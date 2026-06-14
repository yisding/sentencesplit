# -*- coding: utf-8 -*-
"""First-class streaming sentence segmentation.

``StreamSegmenter`` is a thin, stateful wrapper around :class:`Segmenter`. It
accepts text deltas (LLM tokens, ASR partials, chat chunks), emits completed
sentences as soon as their boundary is *stable*, and buffers the unstable tail so
a downstream consumer (e.g. a TTS engine) never speaks a half-formed sentence.

It is purely additive: it never changes :meth:`Segmenter.segment` output. The
cornerstone contract is *streaming == non-streaming* when the whole text is fed at
once::

    stream = StreamSegmenter(language="en")
    stream.feed(full_text)
    assert stream.get_completed_sentences() + stream.flush() \\
        == Segmenter(language="en").segment(full_text)

Design — only the unemitted tail is ever re-segmented
-----------------------------------------------------
The invariant that keeps this simple and correct: **once bytes are emitted they
are dropped from the buffer and never looked at again.** Each :meth:`feed`
re-segments only the still-unemitted tail (``self._buffer``) with the byte-exact
:meth:`Segmenter.segment_spans`, projecting to plain strings only at the output
boundary (see :meth:`_to_output`). Because emitted text is
immutable:

- a segment can never "grow" after emission (no delta reconciliation);
- inter-sentence whitespace naturally rides the *next* sentence, since the next
  round segments a tail that *starts* with that whitespace (no carry buffer);
- offsets are simply ``base_offset + tail_offset`` and stay byte-faithful, with no
  length-derived drift on dirty input (zero-width / NBSP / BOM / combining / RTL).

Cost is bounded by the length of a single sentence (the held tail), so a long
stream stays linear, not quadratic.

``clean=True`` is unsupported: text cleaning (HTML/PDF repair) is a whole-document
operation that does not compose with incremental streaming. Clean upstream, then
stream the cleaned text.

Emission is full-sentence granularity only. Sub-sentence (clause/phrase) flows
should drive an external tokenizer; this class never emits a partial sentence
except via :meth:`flush`.

Buffering modes
---------------
``conservative`` (default)
    Emit the trailing sentence only once lookahead confirms its boundary is
    stable (``should_wait_for_more`` is ``False``). Safest for TTS: an ambiguous
    abbreviation (``Dr.``) or a possible decimal continuation (``GPT 3.`` ->
    ``GPT 3.1``) is held until the next delta resolves it.
``balanced``
    Same emission policy as ``conservative`` for the trailing sentence. The name
    mirrors ``Segmenter.split_mode`` and is accepted for symmetry; it does not
    change emission timing.
``aggressive``
    Trust terminal punctuation immediately: emit the trailing sentence as soon as
    it ends in a sentence-terminal mark, without waiting for lookahead to confirm.
    Lower latency, at the risk of speaking an abbreviation tail or a pre-decimal
    number prematurely.

All modes emit confirmed (non-trailing) boundaries identically and always agree
once :meth:`flush` is called, so the streaming-equals-non-streaming contract holds
regardless of mode.
"""

from __future__ import annotations

from sentencesplit.exceptions import InvalidConfigurationError
from sentencesplit.segmenter import Segmenter
from sentencesplit.utils import BufferingMode, SplitMode, TextSpan

BUFFERING_MODES = ("conservative", "balanced", "aggressive")

# Terminal marks that can cluster into a single multi-character terminator
# ("...", "!!!", "??"). A boundary that segment_spans() places *between* two of
# these (because the cluster is not yet complete) is volatile: appending more of
# the cluster re-merges it. _detect holds such a span instead of emitting a
# fragment. ASCII-only because the resplit rules that recombine clusters
# (_MULTI_TERMINATOR_RESPLIT_RE, the "..." ellipsis rules) are ASCII-only.
_CLUSTER_TERMINALS = frozenset(".!?")


class StreamSegmenter:
    """Stateful streaming wrapper over :class:`Segmenter`.

    Parameters mirror :class:`Segmenter` (``language``, ``split_mode``) plus a
    ``char_span`` flag that selects :class:`TextSpan` vs plain-string output (see
    :meth:`_to_output`), a streaming-specific ``buffering_mode``, and an optional
    ``max_buffer_size`` guard against pathological unbounded tails. ``clean=True``
    is not supported (see the module docstring).
    """

    def __init__(
        self,
        language: str = "en",
        clean: bool = False,
        char_span: bool = False,
        split_mode: SplitMode = "balanced",
        buffering_mode: BufferingMode = "conservative",
        max_buffer_size: int | None = None,
    ) -> None:
        if clean:
            raise InvalidConfigurationError(
                "StreamSegmenter does not support clean=True: text cleaning is a whole-document "
                "operation that does not compose with incremental streaming. Clean the text "
                "upstream, then stream the cleaned text."
            )
        if buffering_mode not in BUFFERING_MODES:
            raise InvalidConfigurationError(
                "buffering_mode must be one of {}.".format(", ".join(repr(m) for m in BUFFERING_MODES))
            )
        if max_buffer_size is not None and max_buffer_size <= 0:
            raise InvalidConfigurationError("max_buffer_size must be a positive integer or None.")
        # The wrapped Segmenter validates language/split_mode (clean is fixed to
        # False). It always works in spans internally; this class's own
        # ``char_span`` flag only governs the user-facing output shape (see
        # ``_to_output``).
        self._segmenter = Segmenter(language=language, clean=False, split_mode=split_mode)
        self.language = language
        self.clean = False
        self.char_span = char_span
        self.split_mode = split_mode
        self.buffering_mode = buffering_mode
        self.max_buffer_size = max_buffer_size

        # The unemitted tail: text that still needs (re-)segmenting. Emitted bytes
        # are dropped from the front, so this only ever holds the volatile tail.
        self._buffer: str = ""
        # Stream-absolute position of ``self._buffer[0]`` — the count of characters
        # already emitted and dropped. Added to each span's buffer-relative offset
        # to produce monotonic, byte-faithful stream offsets.
        self._base_offset: int = 0
        # Stability verdict of the last segmentation's trailing tail, cached so
        # is_complete() need not re-segment.
        self._last_should_wait: bool = False
        # Completed sentences (always TextSpans internally) awaiting collection.
        self._completed: list[TextSpan] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def feed(self, delta: str | None) -> list[str | TextSpan] | None:
        """Append a text delta and detect any newly-stable sentences.

        ``None`` and empty deltas are no-ops. Returns ``None`` normally; if
        ``max_buffer_size`` is set and the unemitted tail exceeds it, the
        overflowing tail is force-emitted and returned (so the caller can react to
        the overflow rather than silently growing memory).

        Overflow force-emission is a hard boundary: it may cut mid-sentence.
        ``max_buffer_size`` trades boundary precision for bounded memory; leave it
        ``None`` (the default) for fully boundary-faithful streaming.
        """
        if delta:
            self._buffer += delta
            self._detect()
        if self.max_buffer_size is not None:
            return self._enforce_max_buffer_size()
        return None

    def get_completed_sentences(self) -> list[str | TextSpan]:
        """Return and drain the sentences whose boundary is now stable.

        Ordered, never duplicated. Calling it again returns ``[]`` until more text
        completes another sentence.
        """
        drained = self._completed
        self._completed = []
        return self._to_output(drained)

    def pending_text(self) -> str:
        """Return the buffered tail that has not yet been emitted."""
        return self._buffer

    def is_complete(self) -> bool:
        """Return whether the pending tail is a stable boundary (or empty).

        ``True`` means the stream could stop here without holding back a partial
        sentence: an empty/whitespace tail, or a tail whose boundary lookahead
        considers stable.
        """
        if not self._buffer.strip():
            return True
        # Reuse the verdict cached by the last _detect; feed() always runs _detect
        # before any poll, so it reflects the current tail.
        return not self._last_should_wait

    def flush(self) -> list[str | TextSpan]:
        """Emit every remaining sentence — stable and unstable tail — and drain.

        After ``flush()`` the buffer is reset to empty, so the next ``feed()``
        starts a fresh logical stream. Use this at end-of-stream (LLM done, ASR
        final) as an explicit synchronization point.
        """
        for span in self._tail_spans():
            self._completed.append(self._stream_span(span))
        out = self._completed
        self._completed = []
        # flush() is an explicit end-of-stream synchronization point: the next
        # feed() begins a fresh logical stream, so the stream-relative base offset
        # resets to 0 along with the buffer.
        self._buffer = ""
        self._base_offset = 0
        self._last_should_wait = False
        return self._to_output(out)

    def reset(self) -> None:
        """Clear all buffered state, making the instance reusable from scratch."""
        self._buffer = ""
        self._base_offset = 0
        self._last_should_wait = False
        self._completed = []

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _tail_spans(self) -> list[TextSpan]:
        """Byte-exact spans tiling the current unemitted tail (buffer-relative)."""
        if not self._buffer:
            return []
        return self._segmenter.segment_spans(self._buffer)

    def _stream_span(self, span: TextSpan) -> TextSpan:
        """Rebase a buffer-relative span to monotonic, byte-faithful stream offsets."""
        return TextSpan(span.sent, self._base_offset + span.start, self._base_offset + span.end)

    def _to_output(self, items: list[TextSpan]) -> list:
        """Project internal TextSpans to the caller-facing form.

        ``char_span=True`` returns the byte-exact :class:`TextSpan` items unchanged.
        Plain mode normalizes each span's text exactly as :meth:`Segmenter.segment`
        does — stripping boundary zero-width/format characters and dropping any
        segment that is whitespace-only — so streaming plain output matches
        non-streaming ``segment()`` even on dirty input.
        """
        if self.char_span:
            return items
        out: list[str] = []
        for span in items:
            text = self._segmenter._strip_zero_width(span.sent)
            if text.strip():
                out.append(text)
        return out

    def _emittable(self, span: TextSpan, is_final: bool, should_wait: bool) -> bool:
        """Whether *span* may be emitted now (vs. held in the pending tail).

        A non-final span's boundary lies in the interior of the buffer and is
        stable *unless* it abuts a still-growing multi-character terminator —
        that case is screened out by the cluster check in :meth:`_detect` before
        this is reached, so here a non-final span is always emittable. The final
        span is the volatile tail; emitting it is gated by buffering mode and by
        whether it ends in terminal punctuation.
        """
        if not is_final:
            return True
        if self._segmenter._terminal_punctuation(span.sent.rstrip()) is None:
            return False
        if self.buffering_mode == "aggressive":
            # Trust terminal punctuation immediately, before lookahead confirms.
            return True
        # conservative / balanced: hold the final sentence until its boundary is
        # stable under lookahead.
        return not should_wait

    def _detect(self) -> None:
        """Emit any newly-stable leading sentences and drop them from the buffer.

        Segments the unemitted tail, emits the confirmed leading spans (every
        non-final span, plus the final one if the buffering mode allows), then
        drops the emitted prefix from the front of the buffer and advances the
        stream base offset. Emitted text is never revisited, so nothing it emits
        can later grow or be re-sliced.
        """
        # One segmentation pass yields both the tail spans and the trailing-
        # boundary lookahead verdict; computing them separately would segment the
        # buffer twice on every delta.
        if self._buffer:
            lookahead = self._segmenter.segment_spans_with_lookahead(self._buffer)
            spans, self._last_should_wait = lookahead.segments, lookahead.should_wait_for_more
        else:
            spans, self._last_should_wait = [], False
        if not spans:
            return
        last_index = len(spans) - 1
        cut = 0
        for index, span in enumerate(spans):
            is_final = index == last_index
            # A non-final span whose boundary falls between terminal punctuation
            # characters may sit inside an as-yet-incomplete cluster (e.g.
            # "Wait." inside a "Wait..." still arriving). segment_spans() will
            # re-merge it once the rest of the cluster lands, so the boundary is
            # not stable yet — hold it rather than emit a fragment. A terminal
            # punctuation mark starting the next span ("One. !Two.") is not part
            # of the previous boundary and must not prevent buffer compaction.
            if (
                not is_final
                and 0 < span.end < len(self._buffer)
                and self._buffer[span.end - 1] in _CLUSTER_TERMINALS
                and self._buffer[span.end] in _CLUSTER_TERMINALS
            ):
                break
            if not self._emittable(span, is_final, self._last_should_wait):
                break  # this span (the volatile final) and nothing after it yet
            self._completed.append(self._stream_span(span))
            cut = span.end
        if cut:
            self._buffer = self._buffer[cut:]
            self._base_offset += cut

    def _enforce_max_buffer_size(self) -> list[str | TextSpan] | None:
        """Force-flush the unemitted tail if it exceeds ``max_buffer_size``.

        Pathological inputs (a megabyte with no terminal punctuation) would
        otherwise grow the buffer without bound. When the tail crosses the limit we
        emit all of it and drop it, *preserving* ``self._base_offset`` (unlike
        :meth:`flush`) so subsequent spans stay monotonic and byte-faithful.
        """
        assert self.max_buffer_size is not None
        if len(self._buffer) <= self.max_buffer_size:
            return None
        for span in self._tail_spans():
            self._completed.append(self._stream_span(span))
        out = self._completed
        self._completed = []
        self._base_offset += len(self._buffer)
        self._buffer = ""
        self._last_should_wait = False
        return self._to_output(out)
