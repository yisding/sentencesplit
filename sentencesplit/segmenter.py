# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import warnings

from sentencesplit.cleaner import Cleaner
from sentencesplit.exceptions import InvalidConfigurationError
from sentencesplit.languages import Language
from sentencesplit.processor import Processor
from sentencesplit.utils import (
    SPLIT_MODES,
    ZERO_WIDTH_CHARS,
    DocType,
    SegmentLookahead,
    SplitMode,
    TextSpan,
)

# Simple, common characters per script that won't trigger abbreviation rules.
_DEFAULT_LOOKAHEAD_STEMS = ("a", "A")
_LANGUAGE_LOOKAHEAD_STEMS = {
    "am": ("ሀ",),
    "en_es_zh": ("a", "A", "甲"),
    "ar": ("ا",),
    "bg": ("А",),
    "el": ("Α",),
    "fa": ("ا",),
    "hi": ("अ",),
    "hy": ("Ա",),
    "ja": ("あ",),
    "kk": ("А",),
    "mr": ("अ",),
    "my": ("က",),
    "ru": ("А",),
    "ur": ("ا",),
    "zh": ("甲",),
}
_DIGIT_LOOKAHEAD_STEM = "1"
_PERIOD_END_PUNCTUATION = frozenset({".", "．"})
_TRAILING_SENTENCE_CLOSERS = frozenset("\"')]}»”’）】》」』")
# Zero-width / format characters that str.isspace() does not flag. A lone one
# (e.g. a Wikipedia U+200B reference marker) at a boundary survives str.strip()
# and is otherwise emitted as a phantom sentence or folded into the next one.
_ZERO_WIDTH_CHARS = frozenset(ZERO_WIDTH_CHARS)
_ZERO_WIDTH_TRANSLATION = {ord(c): None for c in _ZERO_WIDTH_CHARS}


def _strip_zero_width(text: str) -> str:
    """Drop boundary zero-width/format characters from a (plain, non-span) segment.

    Only the leading/trailing run of whitespace-or-zero-width is cleaned, and
    even there whitespace is kept — just the stray zero-width artifact (e.g. a
    lone U+200B Wikipedia reference marker) is removed. Interior zero-width
    joiners are preserved, so emoji sequences (👩‍💻) and scripts that use
    U+200C/U+200D within a word (e.g. Hindi, Persian) are not corrupted.
    """

    def _is_boundary_trim(ch: str) -> bool:
        return ch.isspace() or ch in _ZERO_WIDTH_CHARS

    start, end = 0, len(text)
    while start < end and _is_boundary_trim(text[start]):
        start += 1
    while end > start and _is_boundary_trim(text[end - 1]):
        end -= 1
    lead = text[:start].translate(_ZERO_WIDTH_TRANSLATION)
    trail = text[end:].translate(_ZERO_WIDTH_TRANSLATION)
    return lead + text[start:end] + trail


# ``char_span`` is soft-deprecated in favour of ``segment_spans()`` but retained
# indefinitely as a convenience alias (no removal planned). The DeprecationWarning
# fires only once per process — a gentle nudge, not per-construction noise.
_CHAR_SPAN_DEPRECATION_WARNED = False


def _warn_char_span_deprecated(stacklevel: int = 2) -> None:
    global _CHAR_SPAN_DEPRECATION_WARNED
    if _CHAR_SPAN_DEPRECATION_WARNED:
        return
    _CHAR_SPAN_DEPRECATION_WARNED = True
    warnings.warn(
        "char_span is deprecated; use segment_spans()",
        DeprecationWarning,
        stacklevel=stacklevel,
    )


class Segmenter:
    def __init__(
        self,
        language: str = "en",
        clean: bool = False,
        doc_type: DocType = None,
        char_span: bool = False,
        split_mode: SplitMode = "balanced",
    ) -> None:
        """Segments a text into a list of sentences
        with or without character offsets from original text

        Parameters
        ----------
        language : str, required
            specify a language use its two character ISO 639-1 code,
            by default "en"
        clean : bool, optional
            cleans original text, by default False
        doc_type : [type], optional
            Normal text or OCRed text, by default None
            set to `pdf` for OCRed text
        char_span : bool, optional
            Get start & end character offsets of each sentence within
            the original text, by default False.

            .. deprecated:: 0.0.5
               Prefer :meth:`segment_spans`, the canonical spans API, which
               always returns ``list[TextSpan]`` regardless of this flag and
               guarantees a byte-for-byte round-trip with the source.
               ``char_span`` is retained indefinitely as a convenience alias
               (no removal is planned) and emits a one-time
               :class:`DeprecationWarning` on first use.
        split_mode : str, optional
            Global split-bias for ambiguous boundaries, by default
            "balanced". One of:
              - "conservative": lean every tunable ambiguity toward
                keeping text joined (fewer false splits, more missed
                boundaries / under-split).
              - "balanced" (default): the library's historically tuned
                behavior; output is unchanged from previous releases.
              - "aggressive": lean tunable ambiguities toward splitting
                (catches more real boundaries at the cost of some false
                splits / over-split), e.g. allowing "st." or an
                initialism before a capital to end a sentence.
            Only genuinely ambiguous decisions move with this knob;
            structural rules (decimals, period-before-comma, known
            abbreviations) are unaffected.
        """
        self.language = language
        self.language_module = Language.get_language_code(language)
        self.clean = clean
        self.doc_type = doc_type
        self.char_span = char_span
        if char_span:
            _warn_char_span_deprecated(stacklevel=3)
        if split_mode not in SPLIT_MODES:
            raise InvalidConfigurationError("split_mode must be one of {}.".format(", ".join(repr(m) for m in SPLIT_MODES)))
        self.split_mode = split_mode
        if doc_type not in (None, "pdf"):
            raise InvalidConfigurationError("doc_type must be None or 'pdf'.")
        if self.clean and self.char_span:
            raise InvalidConfigurationError(
                "char_span must be False if clean is True. Since `clean=True` will modify original text."
            )
        # when doctype is pdf then force user to clean the text
        # char_span func wont be provided with pdf doctype also
        elif self.doc_type == "pdf" and not self.clean:
            raise InvalidConfigurationError(
                "`doc_type='pdf'` should have `clean=True` & `char_span` should be False since original text will be modified."
            )
        self._cleaner_cls = getattr(self.language_module, "Cleaner", Cleaner)
        self._processor_cls = getattr(self.language_module, "Processor", Processor)

    @staticmethod
    def list_languages() -> list[str]:
        """Return the supported ISO 639-1 language codes, sorted.

        Includes the built-in languages plus the ``en_es_zh`` and ``en_legal``
        profiles, and reflects any languages registered at runtime. Cheap to
        call: no language module is imported just to enumerate the codes. See
        :func:`sentencesplit.languages.list_languages`.
        """
        from sentencesplit.languages import list_languages

        return list_languages()

    def cleaner(self, text: str):
        return self._cleaner_cls(text, self.language_module, doc_type=self.doc_type)

    def processor(self, text: str):
        return self._processor_cls(text, self.language_module, split_mode=self.split_mode)

    def _analysis_text(self, text: str) -> str:
        if self.clean or self.doc_type == "pdf":
            return self.cleaner(text).clean()
        return text

    def _terminal_punctuation(self, text: str) -> tuple[int, str] | None:
        idx = len(text) - 1
        while idx >= 0 and text[idx] in _TRAILING_SENTENCE_CLOSERS:
            idx -= 1
        if idx < 0:
            return None
        punct = text[idx]
        if punct not in self.language_module.Punctuations:
            return None
        return idx, punct

    def _lookahead_probe_stems(self) -> tuple[str, ...]:
        stems = _LANGUAGE_LOOKAHEAD_STEMS.get(self.language, _DEFAULT_LOOKAHEAD_STEMS)
        return (*stems, _DIGIT_LOOKAHEAD_STEM)

    def _lookahead_probes_for_text(
        self, text: str, punct_index: int, punct: str, has_trailing_whitespace: bool
    ) -> tuple[str, ...]:
        separator = "" if has_trailing_whitespace else " "
        probes = [f"{separator}{stem}" for stem in self._lookahead_probe_stems()]

        # When a digit precedes the period (e.g. "GPT 3."), also probe without
        # a leading space ("1") to catch decimal continuations like "3.1".
        if (
            not has_trailing_whitespace
            and punct in _PERIOD_END_PUNCTUATION
            and punct_index > 0
            and text[punct_index - 1].isdigit()
        ):
            probes.append(_DIGIT_LOOKAHEAD_STEM)

        return tuple(dict.fromkeys(probes))

    def _comparison_segments_from_analysis_text(self, analysis_text: str) -> list[str]:
        processed_sents = self.processor(analysis_text).process()
        if self.clean:
            return processed_sents
        return [s for s, _, _ in self._match_spans(processed_sents, analysis_text)]

    def _expected_last_segment_for_probe(self, last_segment: str, suffix: str) -> str:
        if self.clean:
            return last_segment
        leading_whitespace = suffix[: len(suffix) - len(suffix.lstrip())]
        return last_segment + leading_whitespace

    def _wait_with_tail_probe(self, base_tail: str, last_segment: str, probe_suffixes: tuple[str, ...]) -> bool:
        # base_tail starts exactly at the last segment, so probe_segments[0]
        # corresponds to that segment. If appending a suffix changes it, the
        # boundary is unstable and we should wait for more input.
        for suffix in probe_suffixes:
            probe_segments = self._comparison_segments_from_analysis_text(base_tail + suffix)
            if not probe_segments:
                return True

            expected_last_segment = self._expected_last_segment_for_probe(last_segment, suffix)
            if probe_segments[0] != expected_last_segment:
                return True
        return False

    def _wait_with_full_probe(
        self,
        analysis_text: str,
        comparison_segments: list[str],
        last_segment: str,
        probe_suffixes: tuple[str, ...],
    ) -> bool:
        expected_prefix = comparison_segments[:-1]
        for suffix in probe_suffixes:
            probe_segments = self._comparison_segments_from_analysis_text(analysis_text + suffix)
            expected_last_segment = self._expected_last_segment_for_probe(last_segment, suffix)
            probe_prefix = probe_segments[: len(comparison_segments)]
            if probe_prefix != [*expected_prefix, expected_last_segment]:
                return True
        return False

    def _segment_result(self, text: str | None) -> tuple[str, list[str] | list[TextSpan], list[str]]:
        if not text:
            return "", [], []

        original_text = text
        analysis_text = self._analysis_text(text)
        processed_sents = self.processor(analysis_text).process()

        if self.clean:
            return analysis_text, processed_sents, processed_sents

        matched_spans = list(self._match_spans(processed_sents, original_text))
        comparison_segments = [s for s, _, _ in matched_spans]
        if self.char_span:
            # Spans stay exact slices of the original text (non-destructive); a
            # trailing zero-width char is absorbed into its preceding span by
            # _match_spans so it is not folded into the next sentence.
            spans = [TextSpan(s, start, end) for s, start, end in matched_spans]
            return analysis_text, spans, comparison_segments
        # Plain segments drop zero-width/format chars that str.strip() leaves
        # behind, so a lone U+200B reference marker is not emitted as text.
        plain_segments = [seg for seg in (_strip_zero_width(s) for s in comparison_segments) if seg.strip()]
        return analysis_text, plain_segments, comparison_segments

    def _wait_for_last_segment(self, analysis_text: str, comparison_segments: list[str]) -> bool:
        if not comparison_segments:
            return False

        last_segment = comparison_segments[-1]
        terminal_text = last_segment.rstrip()
        if not terminal_text:
            return False

        has_trailing_whitespace = terminal_text != last_segment
        punct_info = self._terminal_punctuation(terminal_text)
        if punct_info is None:
            return True

        punct_index, punct = punct_info
        if punct not in _PERIOD_END_PUNCTUATION:
            return False

        probe_suffixes = self._lookahead_probes_for_text(
            terminal_text,
            punct_index,
            punct,
            has_trailing_whitespace=has_trailing_whitespace,
        )

        # rfind is safe here: comparison_segments are slices of analysis_text
        # (via _match_spans), so the last segment is always at the tail end and
        # rfind returns the correct (rightmost) occurrence.
        start_index = analysis_text.rfind(last_segment)
        if start_index != -1:
            return self._wait_with_tail_probe(analysis_text[start_index:], last_segment, probe_suffixes)

        return self._wait_with_full_probe(analysis_text, comparison_segments, last_segment, probe_suffixes)

    def _find_sentence_start(self, sent: str, original_text: str, prior_end: int):
        """Return start/end indices for ``sent`` from ``prior_end`` if found."""
        start_idx = original_text.find(sent, prior_end)
        if start_idx != -1:
            return start_idx, start_idx + len(sent)

        # Some post-processing rules may normalize spaces around punctuation,
        # so allow flexible whitespace when mapping back to original text.
        whitespace_flexible = re.escape(sent).replace(r"\ ", r"\s*")
        match = re.search(whitespace_flexible, original_text[prior_end:])
        if match is None:
            return None

        start_idx = prior_end + match.start()
        end_idx = prior_end + match.end()
        return start_idx, end_idx

    def _next_sentence_start(self, sentences: list[str], start_at: int, original_text: str, prior_end: int):
        """Find start index for the next matchable sentence after ``start_at``."""
        for next_sent in sentences[start_at:]:
            if not next_sent:
                continue
            next_match = self._find_sentence_start(next_sent, original_text, prior_end)
            if next_match is not None:
                return next_match[0]
        return None

    def _unmatched_span(self, sentences: list[str], idx: int, original_text: str, prior_end: int):
        """Return fallback span when current processed sentence cannot be matched."""
        next_start = self._next_sentence_start(sentences, idx + 1, original_text, prior_end)
        if next_start is None:
            if prior_end < len(original_text):
                return original_text[prior_end:], prior_end, len(original_text)
            return None
        if next_start > prior_end:
            return original_text[prior_end:next_start], prior_end, next_start
        return None

    def _match_spans(self, sentences: list[str], original_text: str):
        """Match processed sentences back to spans in the original text.

        Yields (text_slice, start, end) tuples for each sentence.
        Accounts for trailing whitespace that SENTENCE_BOUNDARY_REGEX
        does not capture, keeping the segmentation non-destructive.

        Spans contiguously tile the whole source: the final yield covers any
        unmatched trailing remainder so that ``"".join(s for s, _, _ in ...)``
        reproduces ``original_text`` byte-for-byte even when the processor
        emits no sentence content (e.g. whitespace- or zero-width-only input).
        """
        prior_end = 0
        for idx, sent in enumerate(sentences):
            if not sent:
                continue
            match_span = self._find_sentence_start(sent, original_text, prior_end)
            if match_span is None:
                fallback_span = self._unmatched_span(sentences, idx, original_text, prior_end)
                if fallback_span is not None:
                    txt, start, end = fallback_span
                    yield txt, start, end
                    prior_end = end
                continue

            start_idx, end_idx = match_span
            if start_idx > prior_end:
                start_idx = prior_end
            while end_idx < len(original_text) and (
                original_text[end_idx].isspace() or original_text[end_idx] in _ZERO_WIDTH_CHARS
            ):
                end_idx += 1
            yield original_text[start_idx:end_idx], start_idx, end_idx
            prior_end = end_idx

        # Trailing remainder the matching loop did not cover (e.g. whitespace-
        # or zero-width-only input the processor drops, leaving no sentence to
        # anchor to). Emit it as a final span so spans contiguously tile the
        # whole source and the round-trip reproduces it byte-for-byte. In normal
        # text the per-sentence trailing-whitespace sweep already advances
        # prior_end to len(original_text), so this never fires.
        if prior_end < len(original_text):
            yield original_text[prior_end:], prior_end, len(original_text)

    def segment(self, text: str | None) -> list[str] | list[TextSpan]:
        """Segment ``text`` into sentences.

        Returns a ``list[str]`` by default, or a ``list[TextSpan]`` (with
        ``.sent``/``.start``/``.end``) when the Segmenter was constructed with
        ``char_span=True``. Use :meth:`segment_spans` to always get spans
        regardless of the ``char_span`` flag.
        """
        _, segments, _ = self._segment_result(text)
        return segments

    def should_wait_for_more(self, text: str | None) -> bool:
        """Return whether the last emitted segment should wait for more input.

        This is continuation-sensitive by design: we probe with tiny suffixes to
        detect whether the last boundary remains stable if more text arrives.
        """
        analysis_text, _, comparison_segments = self._segment_result(text)
        return self._wait_for_last_segment(analysis_text, comparison_segments)

    def segment_with_lookahead(self, text: str | None) -> SegmentLookahead:
        """Segment text and report whether the last segment should wait."""
        analysis_text, segments, comparison_segments = self._segment_result(text)
        return SegmentLookahead(
            segments=segments,
            should_wait_for_more=self._wait_for_last_segment(analysis_text, comparison_segments),
        )

    def segment_spans(self, text: str | None) -> list[TextSpan]:
        """Return sentence spans regardless of the instance's ``char_span`` flag.

        This is the canonical spans API and is byte-for-byte faithful: each
        returned :class:`~sentencesplit.utils.TextSpan` is an exact slice of the
        source (``text[span.start:span.end] == span.sent``), the spans
        contiguously tile the source with no gaps or overlaps
        (``0 <= start < end <= len(text)``, first ``start`` is 0, last ``end`` is
        ``len(text)``), and reassembling them reproduces the source verbatim
        (``"".join(s.sent for s in segment_spans(text)) == text``). It is
        therefore non-destructive even on dirty input (ZWSP/NBSP/BOM/combining
        marks/RTL markers). Requires ``clean=False``.
        """
        if self.clean:
            raise InvalidConfigurationError("segment_spans() requires clean=False.")
        if not text:
            return []
        processed_sents = self.processor(text).process()
        return [TextSpan(s, start, end) for s, start, end in self._match_spans(processed_sents, text)]

    def segment_clean(self, text: str | None) -> list[str]:
        """Return cleaned sentences regardless of the instance's clean flag."""
        if not text:
            return []
        analysis_text = self.cleaner(text).clean()
        return self.processor(analysis_text).process()
