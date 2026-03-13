# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import List

from sentencesplit.cleaner import Cleaner
from sentencesplit.languages import Language
from sentencesplit.processor import Processor
from sentencesplit.utils import SegmentLookahead, TextSpan

# Simple, common characters per script that won't trigger abbreviation rules.
_DEFAULT_LOOKAHEAD_STEMS = ("a", "A")
_LANGUAGE_LOOKAHEAD_STEMS = {
    "am": ("ሀ",),
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


class Segmenter:
    def __init__(
        self, language: str = "en", clean: bool = False, doc_type: str | None = None, char_span: bool = False
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
            Get start & end character offsets of each sentences
            within original text, by default False
        """
        self.language = language
        self.language_module = Language.get_language_code(language)
        self.clean = clean
        self.doc_type = doc_type
        self.char_span = char_span
        if self.clean and self.char_span:
            raise ValueError("char_span must be False if clean is True. Since `clean=True` will modify original text.")
        # when doctype is pdf then force user to clean the text
        # char_span func wont be provided with pdf doctype also
        elif self.doc_type == "pdf" and not self.clean:
            raise ValueError(
                "`doc_type='pdf'` should have `clean=True` & `char_span` should be False since originaltext will be modified."
            )

    def cleaner(self, text: str):
        if hasattr(self.language_module, "Cleaner"):
            return self.language_module.Cleaner(text, self.language_module, doc_type=self.doc_type)
        else:
            return Cleaner(text, self.language_module, doc_type=self.doc_type)

    def processor(self, text: str):
        if hasattr(self.language_module, "Processor"):
            return self.language_module.Processor(text, self.language_module, char_span=self.char_span)
        else:
            return Processor(text, self.language_module, char_span=self.char_span)

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
            spans = [TextSpan(s, start, end) for s, start, end in matched_spans]
            return analysis_text, spans, comparison_segments
        return analysis_text, comparison_segments, comparison_segments

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

    def _next_sentence_start(self, sentences: List[str], start_at: int, original_text: str, prior_end: int):
        """Find start index for the next matchable sentence after ``start_at``."""
        for next_sent in sentences[start_at:]:
            if not next_sent:
                continue
            next_match = self._find_sentence_start(next_sent, original_text, prior_end)
            if next_match is not None:
                return next_match[0]
        return None

    def _unmatched_span(self, sentences: List[str], idx: int, original_text: str, prior_end: int):
        """Return fallback span when current processed sentence cannot be matched."""
        next_start = self._next_sentence_start(sentences, idx + 1, original_text, prior_end)
        if next_start is None:
            if prior_end < len(original_text):
                return original_text[prior_end:], prior_end, len(original_text)
            return None
        if next_start > prior_end:
            return original_text[prior_end:next_start], prior_end, next_start
        return None

    def _match_spans(self, sentences: List[str], original_text: str):
        """Match processed sentences back to spans in the original text.

        Yields (text_slice, start, end) tuples for each sentence.
        Accounts for trailing whitespace that SENTENCE_BOUNDARY_REGEX
        does not capture, keeping the segmentation non-destructive.
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
            while end_idx < len(original_text) and original_text[end_idx].isspace():
                end_idx += 1
            yield original_text[start_idx:end_idx], start_idx, end_idx
            prior_end = end_idx

    def segment(self, text: str | None) -> List[str] | List[TextSpan]:
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

    def segment_spans(self, text: str | None) -> List[TextSpan]:
        """Return sentence spans regardless of the instance's char_span flag."""
        if self.clean:
            raise ValueError("segment_spans() requires clean=False.")
        seg = Segmenter(language=self.language, clean=False, doc_type=self.doc_type, char_span=True)
        return seg.segment(text)

    def segment_clean(self, text: str | None) -> List[str]:
        """Return cleaned sentences regardless of the instance's clean flag."""
        seg = Segmenter(language=self.language, clean=True, doc_type=self.doc_type, char_span=False)
        return seg.segment(text)
