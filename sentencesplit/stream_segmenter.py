# -*- coding: utf-8 -*-
"""First-class streaming sentence segmentation.

``StreamSegmenter`` is a thin, stateful wrapper around the already-tested
:meth:`Segmenter.segment_with_lookahead` / :meth:`Segmenter.should_wait_for_more`
primitives. It accepts text deltas (LLM tokens, ASR partials, chat chunks),
emits completed sentences as soon as their boundary is *stable*, and buffers the
unstable tail so a downstream consumer (e.g. a TTS engine) never speaks a
half-formed sentence.

It is purely additive: it never changes :meth:`Segmenter.segment` output. The
cornerstone contract is *streaming == non-streaming*::

    stream = StreamSegmenter(language="en")
    stream.feed(full_text)
    assert stream.get_completed_sentences() + stream.flush() \
        == Segmenter(language="en").segment(full_text)

Emission is full-sentence granularity only. Sub-sentence (clause/phrase) flows
should drive an external tokenizer; this class never emits a partial sentence
except via :meth:`flush`.

Buffering modes
---------------
``conservative`` (default)
    Emit the trailing sentence only once lookahead confirms its boundary is
    stable (``should_wait_for_more`` is ``False``). Safest for TTS: an
    ambiguous abbreviation (``Dr.``) or a possible decimal continuation
    (``GPT 3.`` -> ``GPT 3.1``) is held until the next delta resolves it.
``balanced``
    Same emission policy as ``conservative`` for the trailing sentence. The
    name mirrors ``Segmenter.split_mode`` and is accepted for symmetry; it does
    not change emission timing.
``aggressive``
    Trust terminal punctuation immediately: emit the trailing sentence as soon
    as it ends in a sentence-terminal mark, without waiting for lookahead to
    confirm. Lower latency, at the risk of speaking an abbreviation tail or a
    pre-decimal number prematurely.

All modes emit confirmed (non-trailing) boundaries identically and always agree
once :meth:`flush` is called, so the streaming-equals-non-streaming contract
holds regardless of mode.
"""

from __future__ import annotations

from sentencesplit.segmenter import Segmenter
from sentencesplit.utils import TextSpan

BUFFERING_MODES = ("conservative", "balanced", "aggressive")


class StreamSegmenter:
    """Stateful streaming wrapper over :class:`Segmenter`.

    Parameters mirror :class:`Segmenter` (``language``, ``clean``,
    ``char_span``, ``split_mode``) plus a streaming-specific ``buffering_mode``
    and an optional ``max_buffer_size`` guard against pathological unbounded
    tails.
    """

    def __init__(
        self,
        language: str = "en",
        clean: bool = False,
        char_span: bool = False,
        split_mode: str = "balanced",
        buffering_mode: str = "conservative",
        max_buffer_size: int | None = None,
    ) -> None:
        if buffering_mode not in BUFFERING_MODES:
            raise ValueError("buffering_mode must be one of {}.".format(", ".join(repr(m) for m in BUFFERING_MODES)))
        if max_buffer_size is not None and max_buffer_size <= 0:
            raise ValueError("max_buffer_size must be a positive integer or None.")
        # Segmenter validates language/split_mode/clean+char_span constraints,
        # so StreamSegmenter inherits exactly the same guardrails (e.g.
        # clean=True forbids char_span).
        #
        # The wrapped Segmenter emits the one-time char_span DeprecationWarning
        # itself (once per process), so the wrapper does not re-warn.
        self._segmenter = Segmenter(
            language=language,
            clean=clean,
            char_span=char_span,
            split_mode=split_mode,
        )
        self.language = language
        self.clean = clean
        self.char_span = char_span
        self.split_mode = split_mode
        self.buffering_mode = buffering_mode
        self.max_buffer_size = max_buffer_size

        # The *unstable tail* of the stream: confirmed interior sentences are
        # dropped from the front once emitted (buffer compaction), so this holds
        # only the bytes that still need re-segmenting. It is extended by feed()
        # and shortened from the front by compaction; never rewritten.
        self._buffer: str = ""
        # Number of characters of ``self._buffer`` already emitted as completed
        # sentences. Always a prefix length of ``self._buffer``; the unemitted
        # tail is ``self._buffer[self._emitted_chars:]``. Compaction rebases this
        # alongside the buffer so it stays buffer-relative.
        self._emitted_chars: int = 0
        # Count of characters dropped from the front of ``self._buffer`` by
        # compaction. Emitted span offsets are stream-relative, so this is added
        # to every TextSpan start/end; it is preserved (never reset) across
        # compaction and max_buffer_size overflow so offsets stay monotonic and
        # byte-faithful (full[start:end] == sent over the whole stream).
        self._base_offset: int = 0
        # Whether the last segmentation's trailing tail wanted more input.
        # Cached from _detect_completed so is_complete() can reuse it instead of
        # triggering a second full re-segmentation per poll.
        self._last_should_wait: bool = False
        # Completed sentences awaiting collection via get_completed_sentences().
        self._completed: list[str | TextSpan] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def feed(self, delta: str | None) -> list[str | TextSpan] | None:
        """Append a text delta and detect any newly-stable sentences.

        ``None`` and empty deltas are no-ops. Returns ``None`` normally; if
        ``max_buffer_size`` is set and the pending tail exceeds it, the
        overflowing tail is force-emitted and the force-flushed sentences are
        returned (so the caller can react to the overflow rather than silently
        growing memory).

        Overflow force-emission is a hard boundary: it may cut mid-sentence and
        the spans/text after it continue a fresh logical run. ``max_buffer_size``
        trades boundary precision for bounded memory; leave it ``None`` (the
        default) for fully boundary-faithful streaming.
        """
        if delta:
            self._buffer += delta
            self._detect_completed()
        if self.max_buffer_size is not None:
            return self._enforce_max_buffer_size()
        return None

    def get_completed_sentences(self) -> list[str | TextSpan]:
        """Return and drain the sentences whose boundary is now stable.

        Ordered, never duplicated. Calling it again returns ``[]`` until more
        text completes another sentence.
        """
        drained = self._completed
        self._completed = []
        return drained

    def pending_text(self) -> str:
        """Return the buffered tail that has not yet been emitted."""
        return self._buffer[self._emitted_chars :]

    def is_complete(self) -> bool:
        """Return whether the pending tail is a stable boundary (or empty).

        ``True`` means the stream could stop here without holding back a
        partial sentence: an empty tail, or a tail whose boundary lookahead
        considers stable.
        """
        pending = self.pending_text()
        if not pending.strip():
            return True
        # Reuse the stability verdict cached by the last _detect_completed
        # segmentation instead of re-segmenting the whole buffer again. feed()
        # always runs _detect_completed before any poll, so the cache reflects
        # the current buffer's trailing tail.
        return not self._last_should_wait

    def flush(self) -> list[str | TextSpan]:
        """Emit every remaining sentence — stable and unstable tail — and drain.

        After ``flush()`` the buffer is reset to empty, so the next ``feed()``
        starts a fresh logical stream. Use this at end-of-stream (LLM done, ASR
        final) as an explicit synchronization point.
        """
        segments, _ = self._segment_buffer()
        # Emit every segment past the watermark, reconciling a partially-emitted
        # final segment via _emit (so a grown prior emission is not duplicated).
        for segment, start, end in self._offset_segments(segments):
            if end <= self._emitted_chars:
                continue
            self._emit(segment, start, end)
        out = self._completed
        self._completed = []
        # flush() is an explicit end-of-stream synchronization point: the next
        # feed() begins a fresh logical stream, so the stream-relative base
        # offset resets to 0 along with the buffer and watermark.
        self._buffer = ""
        self._emitted_chars = 0
        self._base_offset = 0
        self._last_should_wait = False
        return out

    def reset(self) -> None:
        """Clear all buffered state, making the instance reusable from scratch."""
        self._buffer = ""
        self._emitted_chars = 0
        self._base_offset = 0
        self._last_should_wait = False
        self._completed = []

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _segment_buffer(self):
        """Segment the full buffer with lookahead.

        Returns ``(segments, should_wait_for_more)``. Segments are exact slices
        of the buffer (str, or TextSpan with buffer-relative offsets), so they
        always tile the buffer contiguously and the last one is the tail whose
        stability ``should_wait_for_more`` describes.
        """
        result = self._segmenter.segment_with_lookahead(self._buffer)
        return result.segments, result.should_wait_for_more

    def _segment_text(self, segment: str | TextSpan) -> str:
        return segment.sent if isinstance(segment, TextSpan) else segment

    def _offset_segments(self, segments):
        """Yield ``(segment, start, end)`` buffer offsets for each segment.

        Segments tile the buffer contiguously (they are exact slices via
        ``_match_spans``), so offsets accumulate from the running length.
        """
        consumed = 0
        for segment in segments:
            length = len(self._segment_text(segment))
            yield segment, consumed, consumed + length
            consumed += length

    def _is_emittable(self, segment, is_final: bool, should_wait: bool) -> bool:
        """Whether *segment* may be emitted now (vs. held in the pending tail).

        A non-final segment's boundary already lies in the interior of the
        buffer and can never change, so it is always emittable. The final
        segment is the volatile tail; emitting it is gated by buffering mode and
        by whether its text could still grow (e.g. absorb trailing whitespace),
        which would otherwise duplicate already-emitted text.
        """
        if not is_final:
            return True
        text = self._segment_text(segment)
        ends_in_terminal = self._segmenter._terminal_punctuation(text.rstrip()) is not None
        if not ends_in_terminal:
            return False
        if self.buffering_mode == "aggressive":
            # Trust terminal punctuation immediately, even before lookahead
            # confirms stability. The final segment may still grow by trailing
            # whitespace on the next feed; _detect_completed reconciles that.
            return True
        # conservative / balanced: hold the final sentence until lookahead
        # confirms its boundary is stable.
        return not should_wait

    def _emit(self, segment, start: int, end: int) -> None:
        """Append the not-yet-emitted slice ``[max(start, watermark), end)``.

        ``start``/``end`` are buffer-relative offsets into the (possibly
        compacted) tail. Emitted ``TextSpan`` offsets, by contrast, are
        stream-relative, so ``self._base_offset`` — the count of characters
        already dropped from the front of the buffer — is added to them.

        Usually ``start`` equals the watermark and the whole segment is emitted.
        If an earlier emission of this same (final) segment grew — e.g. it
        absorbed a trailing space that arrived in a later delta — only the new
        delta is emitted, so concatenating all emissions reproduces the source
        exactly with neither duplication nor loss.
        """
        watermark = self._emitted_chars
        if start >= watermark:
            # Whole segment is new. Rebase a TextSpan's offsets to stream-
            # relative; a plain string segment is emitted verbatim (it may have
            # had zero-width chars stripped, so it is not a raw buffer slice).
            if isinstance(segment, TextSpan):
                self._completed.append(TextSpan(segment.sent, self._base_offset + start, self._base_offset + end))
            else:
                self._completed.append(segment)
        else:
            # A prior emission of this (final) segment grew; emit only the new
            # tail bytes so nothing is duplicated.
            delta = self._buffer[watermark:end]
            if isinstance(segment, TextSpan):
                self._completed.append(TextSpan(delta, self._base_offset + watermark, self._base_offset + end))
            else:
                self._completed.append(delta)
        self._emitted_chars = end

    def _detect_completed(self) -> None:
        """Move any newly-stable leading sentences into the completed queue.

        Uses ``_emitted_chars`` as a watermark into the buffer. Segments before
        the volatile tail have permanent (interior) boundaries and are always
        emitted; the tail is emitted per the buffering mode (see
        :meth:`_is_emittable`). Reconciliation of a grown prior emission is
        handled by :meth:`_emit`.

        After emitting, the confirmed-interior prefix is compacted out of the
        buffer (see :meth:`_compact`) so the next feed only re-segments the
        volatile tail rather than the whole growing stream.
        """
        segments, should_wait = self._segment_buffer()
        self._last_should_wait = should_wait
        if not segments:
            return
        last_index = len(segments) - 1
        final_start = None
        for index, (segment, start, end) in enumerate(self._offset_segments(segments)):
            if index == last_index:
                final_start = start
            if end <= self._emitted_chars:
                continue  # fully within the already-emitted prefix
            if not self._is_emittable(segment, index == last_index, should_wait):
                break  # this and everything after it is the pending tail
            self._emit(segment, start, end)
        self._compact(final_start)

    def _compact(self, final_start: int | None) -> None:
        """Drop the confirmed-interior prefix from the front of the buffer.

        Everything before the final (volatile) segment has a permanent boundary,
        so those bytes never need re-segmenting again. We slice them off the
        front of ``self._buffer``, advance ``self._base_offset`` by the dropped
        length (keeping emitted span offsets monotonic and stream-relative), and
        rebase ``self._emitted_chars`` to the new tail.

        The cut never crosses ``self._emitted_chars``: the final segment may
        have been force-emitted (aggressive mode) yet still grow on a later feed,
        and :meth:`_emit` re-slices it relative to the watermark, so its start
        must remain in the buffer.
        """
        if final_start is None:
            return
        drop = min(final_start, self._emitted_chars)
        if drop <= 0:
            return
        self._buffer = self._buffer[drop:]
        self._base_offset += drop
        self._emitted_chars -= drop

    def _enforce_max_buffer_size(self) -> list[str | TextSpan] | None:
        """Force-flush the pending tail if it exceeds ``max_buffer_size``.

        Pathological inputs (a megabyte with no terminal punctuation) would
        otherwise grow ``self._buffer`` without bound. When the unemitted tail
        crosses the limit we emit it verbatim as completed text, then compact it
        out of the buffer while *preserving* ``self._base_offset`` — so the
        forced cut bounds memory without resetting stream-relative span offsets
        (which would corrupt the byte-faithful span contract).
        """
        assert self.max_buffer_size is not None
        if len(self.pending_text()) <= self.max_buffer_size:
            return None
        # Emit every remaining segment past the watermark (same machinery as
        # flush, including plain-mode zero-width stripping and grown-emission
        # reconciliation via _emit), then compact the now fully-emitted buffer.
        segments, _ = self._segment_buffer()
        for segment, start, end in self._offset_segments(segments):
            if end <= self._emitted_chars:
                continue
            self._emit(segment, start, end)
        forced = self._completed
        self._completed = []
        # Unlike flush(), preserve _base_offset so subsequent spans stay
        # monotonic and stream-relative: the dropped tail advances the base
        # rather than resetting it to 0.
        self._base_offset += len(self._buffer)
        self._buffer = ""
        self._emitted_chars = 0
        self._last_should_wait = False
        return forced
