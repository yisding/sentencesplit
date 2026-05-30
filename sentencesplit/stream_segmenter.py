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

import warnings

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
        # Segmenter also emits the char_span DeprecationWarning, but from inside
        # its own __init__ the warning would point at this wrapper rather than
        # the caller. Suppress that inner emission and re-warn here with a
        # stacklevel that names the user's StreamSegmenter(...) call site, so the
        # forwarded flag still warns exactly once.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self._segmenter = Segmenter(
                language=language,
                clean=clean,
                char_span=char_span,
                split_mode=split_mode,
            )
        if char_span:
            warnings.warn(
                "char_span is deprecated; use segment_spans()",
                DeprecationWarning,
                stacklevel=2,
            )
        self.language = language
        self.clean = clean
        self.char_span = char_span
        self.split_mode = split_mode
        self.buffering_mode = buffering_mode
        self.max_buffer_size = max_buffer_size

        # The full text fed since the last reset/flush. Spans (char_span=True)
        # are reported relative to this buffer, so it is the single source of
        # truth and is only ever extended or drained, never rewritten.
        self._buffer: str = ""
        # Number of characters already emitted as completed sentences. Always a
        # prefix length of ``self._buffer``; the unemitted tail is
        # ``self._buffer[self._emitted_chars:]``.
        self._emitted_chars: int = 0
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
        return not self._segmenter.should_wait_for_more(self._buffer)

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
        self._buffer = ""
        self._emitted_chars = 0
        return out

    def reset(self) -> None:
        """Clear all buffered state, making the instance reusable from scratch."""
        self._buffer = ""
        self._emitted_chars = 0
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

        Usually ``start`` equals the watermark and the whole segment is emitted.
        If an earlier emission of this same (final) segment grew — e.g. it
        absorbed a trailing space that arrived in a later delta — only the new
        delta is emitted, so concatenating all emissions reproduces the source
        exactly with neither duplication nor loss.
        """
        watermark = self._emitted_chars
        if start >= watermark:
            self._completed.append(segment)
        else:
            delta = self._buffer[watermark:end]
            if isinstance(segment, TextSpan):
                self._completed.append(TextSpan(delta, watermark, end))
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
        """
        segments, should_wait = self._segment_buffer()
        if not segments:
            return
        last_index = len(segments) - 1
        for index, (segment, start, end) in enumerate(self._offset_segments(segments)):
            if end <= self._emitted_chars:
                continue  # fully within the already-emitted prefix
            if not self._is_emittable(segment, index == last_index, should_wait):
                break  # this and everything after it is the pending tail
            self._emit(segment, start, end)

    def _enforce_max_buffer_size(self) -> list[str | TextSpan] | None:
        """Force-flush the pending tail if it exceeds ``max_buffer_size``.

        Pathological inputs (a megabyte with no terminal punctuation) would
        otherwise grow ``self._buffer`` without bound. When the unemitted tail
        crosses the limit we emit it verbatim as completed text and reset the
        buffer, trading a possibly mid-sentence cut for bounded memory.
        """
        assert self.max_buffer_size is not None
        if len(self.pending_text()) <= self.max_buffer_size:
            return None
        forced = self.flush()
        # flush() returns previously-completed sentences too; surface them so
        # nothing is dropped, and keep them out of the completed queue (already
        # drained by flush()).
        return forced
