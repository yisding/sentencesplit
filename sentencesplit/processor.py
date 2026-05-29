# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.exclamation_words import ExclamationWords
from sentencesplit.language_profile import LanguageProfile
from sentencesplit.utils import _next_nonspace_char_starts_sentence, apply_rules

# Pre-compiled patterns used on the hot path
_ALPHA_ONLY_RE = re.compile(r"\A[a-zA-Z]*\Z")
_ELLIPSIS_RE = re.compile(r"\A\.{3,}\Z")
_TRAILING_EXCL_RE = re.compile(r"&ᓴ&$")
_PAREN_SPACE_BEFORE_RE = re.compile(r"\s(?=\()")
_PAREN_SPACE_AFTER_RE = re.compile(r"(?<=\))\s")
_ORPHAN_SINGLE_CHARS = frozenset("'\")\u2019\u201d")
# Zero-width / format characters that str.strip() does not remove. Wikipedia
# reference markers leave a lone U+200B at a sentence boundary, which otherwise
# survives as a phantom empty sentence or is folded into the next sentence.
_ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\ufeff"
_CJK_QUOTE_RESPLIT_RE = re.compile(
    r"(?<=[。．][\]\"')”’」』】）》])(?=[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ffA-Za-z0-9「『【（《])"
)
_LATIN_RESPLIT_RE = re.compile(r"(?<=[a-zA-Z]{2}\.\))\s+")
# A run of 2+ '!'/'?' (restored from the continuous-punctuation placeholders) that
# ends a sentence: the boundary check itself is delegated to
# _next_nonspace_char_starts_sentence so accented Latin capitals (Ä/Ö/Ü, É, …) count.
# The cluster is left intact; only the whitespace after it becomes a split point.
_MULTI_TERMINATOR_RESPLIT_RE = re.compile(r"(?<=[!?]{2})\s+")
# A period immediately followed (after optional spaces) by a *single* comma can
# never be a sentence boundary, since no sentence starts with a comma. This
# protects the final period of unlisted multi-period abbreviations such as the
# botanical author tag "N.E.Br.," from being treated as terminal. The negative
# lookahead excludes a doubled comma (",,"), which in Dutch typography is an
# *opening* quotation mark beginning a new sentence (e.g. "...einde. ,,Nieuwe...").
_PERIOD_BEFORE_COMMA_RE = re.compile(r"\.(?=\s*,(?!,))")

# The between-punctuation pass protects everything from an opening quote to its
# closing quote as one unsplittable region, so a quotation that wraps several
# complete sentences collapses into a single segment when the closing quote is
# far away. _resplit_multi_sentence_quote re-splits such a segment, but only for
# a self-contained, un-nested quotation: a single matched quote pair (one opener
# near the start, the matching closer at the end) whose interior contains NO
# other quote characters at all. That excludes dialogue with embedded attribution
# or nested quotes (e.g. '"X," said Alice; "Y. Z. W."' or '"...\'William...\'"'),
# which the existing gold keeps whole, while still catching a clean run such as
# '“A. B. C.”' (case_0080).
_QUOTE_PAIRS = (("“", "”"), ('"', '"'), ("«", "»"))
_QUOTE_PAIR_BY_OPENER = {opener: closer for opener, closer in _QUOTE_PAIRS}
_LEADING_QUOTE_RE = re.compile(r"\A[\s_]*([“\"«])")
# Any quotation character — used to reject quotes with nested quotes/attribution.
_ANY_QUOTE_CHARS = frozenset("“”\"«»‘’'")
# Interior boundary inside a restored (already de-protected) quoted segment: a
# single PERIOD, optional whitespace, then a Latin capital. Only periods count —
# runs of '!'/'?' inside a quote are usually one emphatic speech act
# ("Oh dear! Oh dear!" / "As if I would! ... again!"), not separate sentences.
_QUOTE_INTERIOR_BOUNDARY_RE = re.compile(r"(?<=[.])\s+(?=[A-Z])")
# A multi-sentence quotation must contain at least this many interior pieces
# (i.e. at least two interior boundaries / three sentences) before the resplit
# fires, and every piece must be at least _QUOTE_MIN_WORDS words long. Requiring
# three keeps single-boundary quotes intact, where it is genuinely ambiguous
# whether the second clause is a new sentence or a continuation of the same
# speech act (e.g. the gold-kept "...at tea-time. Dinah, my dear, I wish...").
_QUOTE_MIN_INTERIOR_SENTENCES = 3
_QUOTE_MIN_WORDS = 5


def _resplit_multi_sentence_quote(text: str) -> list[str] | None:
    """Re-split a self-contained quotation at its interior period boundaries.

    Returns the split pieces, or ``None`` when *text* should be left intact.
    """
    match = _LEADING_QUOTE_RE.match(text)
    if match is None:
        return None
    closer = _QUOTE_PAIR_BY_OPENER[match.group(1)]
    body = text.rstrip()
    if not body.endswith(closer):
        return None
    # The interior must be a single, un-nested quotation: no embedded quote
    # characters (attribution, nested quotes) that signal the multi-sentence run
    # is not one clean quoted utterance.
    inner = body[match.end() : -1]
    if any(char in _ANY_QUOTE_CHARS for char in inner):
        return None

    spans = []
    last = 0
    for boundary in _QUOTE_INTERIOR_BOUNDARY_RE.finditer(text):
        spans.append(text[last : boundary.start()])
        last = boundary.end()
    if len(spans) + 1 < _QUOTE_MIN_INTERIOR_SENTENCES:
        return None
    spans.append(text[last:])

    if any(len(span.split()) < _QUOTE_MIN_WORDS for span in spans):
        # Short interior pieces are dialogue beats, not standalone sentences —
        # keep the quotation whole.
        return None

    return spans


def _split_on_uppercase_boundary(text: str, whitespace_re: re.Pattern[str]) -> list[str] | None:
    parts = []
    last = 0
    for match in whitespace_re.finditer(text):
        if not _next_nonspace_char_starts_sentence(text, match.end()):
            continue
        parts.append(text[last : match.start()])
        last = match.end()
    if not parts:
        return None
    parts.append(text[last:])
    return [part for part in parts if part]


def _sub_symbols_fast(text: str, lang) -> str:
    """Replace temporary symbols using str.replace() instead of regex."""
    for old, new in lang.SubSymbolsRules.SUBS_TABLE:
        text = text.replace(old, new)
    return text


class Processor:
    def __init__(self, text: str | None, lang, split_mode: str = "conservative") -> None:
        self.text = text
        self.lang = lang
        self.split_mode = split_mode
        self.profile = LanguageProfile.from_language(lang)

    def process(self) -> list[str]:
        if not self.text:
            return []
        text = self.text
        for phase in self._text_processing_phases():
            text = phase(text)
        return self.split_into_segments(text)

    def _text_processing_phases(self):
        phases = [
            self._normalize_newlines,
            self._mark_list_item_boundaries,
            self.replace_abbreviations,
        ]
        if self.profile.cjk_abbreviation_rules:
            phases.append(self._apply_cjk_abbreviation_rules)
        phases.extend(
            [
                self.replace_numbers,
                self.replace_continuous_punctuation,
                self.replace_periods_before_numeric_references,
                self._protect_special_tokens,
            ]
        )
        return tuple(phases)

    def _boundary_processing_phases(self):
        return (
            self._ensure_terminal_marker,
            self._apply_exclamation_word_rules,
            self.between_punctuation,
            self._apply_double_punctuation_rules,
            self._apply_quotation_punctuation_rules,
            self._replace_list_parens,
        )

    def _normalize_newlines(self, text: str) -> str:
        return text.replace("\n", "\r")

    def _mark_list_item_boundaries(self, text: str) -> str:
        return self.profile.list_item_replacer_cls(text).add_line_break()

    def _apply_cjk_abbreviation_rules(self, text: str) -> str:
        return apply_rules(text, *self.profile.cjk_abbreviation_rules)

    def _protect_special_tokens(self, text: str) -> str:
        return apply_rules(
            text,
            self.lang.Abbreviation.WithMultiplePeriodsAndEmailRule,
            self.lang.GeoLocationRule,
            self.lang.FileFormatRule,
            self.lang.DotNetRule,
        )

    def rm_none_flatten(self, sents: list[str | list[str] | None]) -> list[str]:
        new_sents = []
        for s in sents:
            if not s:
                continue
            if isinstance(s, list):
                new_sents.extend(s)
            else:
                new_sents.append(s)
        return new_sents

    def split_into_segments(self, text: str | None = None) -> list[str]:
        working_text = text if text is not None else self.text
        if not working_text:
            return []

        working_text = self.check_for_parens_between_quotes(working_text)
        sents = working_text.split("\r")
        # remove empty and none values
        sents = self.rm_none_flatten(sents)
        sents = [self._apply_single_newline_and_ellipsis_rules(s) for s in sents]
        sents = [self.check_for_punctuation(s) for s in sents]
        # flatten list of list of sentences
        sents = self.rm_none_flatten(sents)
        postprocessed_sents = self._restore_and_postprocess_segments(sents)
        postprocessed_sents = [apply_rules(ns, self.lang.SubSingleQuoteRule) for ns in postprocessed_sents]
        postprocessed_sents = self._resplit_segments(postprocessed_sents)
        postprocessed_sents = self._merge_orphan_fragments(postprocessed_sents)
        return self._strip_zero_width_chars(postprocessed_sents)

    def _strip_zero_width_chars(self, postprocessed_sents: list[str]) -> list[str]:
        # str.strip() does not remove zero-width / format characters, so a lone
        # U+200B (e.g. a Wikipedia reference marker) survives as a phantom empty
        # sentence and a leading one is folded into the next sentence. Strip them
        # from the segment edges and drop segments that become empty.
        cleaned = []
        for sent in postprocessed_sents:
            stripped = sent.strip(_ZERO_WIDTH_CHARS).strip()
            if stripped:
                cleaned.append(stripped)
        return cleaned

    def _apply_single_newline_and_ellipsis_rules(self, text: str) -> str:
        return apply_rules(text, self.lang.SingleNewLineRule, *self.lang.EllipsisRules.All)

    def _restore_and_postprocess_segments(self, sentences: list[str]) -> list[str]:
        postprocessed_sents = []
        for sent in sentences:
            restored = _sub_symbols_fast(sent, self.lang)
            for pps in self.post_process_segments(restored):
                if pps:
                    postprocessed_sents.append(pps)
        return postprocessed_sents

    def _resplit_segments(self, postprocessed_sents: list[str]) -> list[str]:
        if self.profile.latin_uppercase_resplit:
            # Re-split at ".) Capital" boundaries (period inside closing paren before new sentence)
            # and at multi-character terminators ("Top!!! Der") whose cluster the
            # continuous-punctuation protection prevented from splitting earlier.
            resplit = []
            for pps in postprocessed_sents:
                parts = (
                    _split_on_uppercase_boundary(pps, _LATIN_RESPLIT_RE)
                    or _split_on_uppercase_boundary(pps, _MULTI_TERMINATOR_RESPLIT_RE)
                    or _resplit_multi_sentence_quote(pps)
                )
                if parts is None:
                    resplit.append(pps)
                else:
                    resplit.extend(parts)
            return resplit

        # CJK: Re-split at closing-quote boundaries
        resplit = []
        for pps in postprocessed_sents:
            parts = _CJK_QUOTE_RESPLIT_RE.split(pps)
            resplit.extend(p for p in parts if p)
        return resplit

    def _merge_orphan_fragments(self, postprocessed_sents: list[str]) -> list[str]:
        # Merge orphan fragments into the preceding sentence.
        # An orphan is either an ellipsis (3+ periods) or a very short
        # lowercase abbreviation fragment ending with a period (e.g. "pp.").
        merged = []
        for sent in postprocessed_sents:
            stripped = sent.strip()
            is_orphan = False
            if stripped and merged:
                if _ELLIPSIS_RE.match(stripped):
                    is_orphan = True
                elif len(stripped) == 1 and stripped in _ORPHAN_SINGLE_CHARS:
                    is_orphan = True
                elif (
                    len(stripped) <= 10
                    and stripped.endswith(".")
                    and not stripped[0].isupper()
                    and any(c.isalnum() for c in stripped)
                ):
                    is_orphan = True
            if is_orphan:
                # Keep punctuation or quote closers attached to the previous
                # sentence without introducing an artificial space. Adding a
                # space here can make the processed sentence impossible to map
                # back to the original text span (e.g. `away.)` -> `away. )`).
                if len(stripped) == 1 and stripped in _ORPHAN_SINGLE_CHARS:
                    merged[-1] = merged[-1] + sent
                else:
                    merged[-1] = merged[-1] + " " + sent
            else:
                merged.append(sent)
        return merged

    def post_process_segments(self, txt: str) -> list[str]:
        if len(txt) > 2 and _ALPHA_ONLY_RE.search(txt):
            return [txt]

        txt = apply_rules(txt, *self.lang.ReinsertEllipsisRules.All)
        if self.profile.latin_uppercase_resplit:
            quoted_parts = _split_on_uppercase_boundary(txt, self.profile.split_quotation_re)
            if quoted_parts is not None:
                return quoted_parts
        else:
            if self.profile.quotation_end_re.search(txt):
                parts = self.profile.split_quotation_re.split(txt)
                return [t for t in parts if t]

        txt = txt.replace("\n", "")
        txt = txt.strip()
        return [txt] if txt else []

    def check_for_parens_between_quotes(self, text: str) -> str:
        def paren_replace(match):
            match = match.group()
            sub1 = _PAREN_SPACE_BEFORE_RE.sub("\r", match)
            sub2 = _PAREN_SPACE_AFTER_RE.sub("\r", sub1)
            return sub2

        return self.profile.parens_dq_re.sub(paren_replace, text)

    def replace_continuous_punctuation(self, text: str) -> str:
        def continuous_puncs_replace(match):
            match = match.group()
            match = match.replace("!", "&ᓴ&")
            match = match.replace("?", "&ᓷ&")
            return match

        return self.profile.continuous_punct_re.sub(continuous_puncs_replace, text)

    def replace_periods_before_numeric_references(self, text: str) -> str:
        """Protect the period in numeric/bracket citations and insert a sentence boundary after them.

        For matches like "see [12]. Next" or "page 1.2 3 next.", rewrites the
        period to a protected placeholder (∯) and inserts a boundary marker (\\r)
        immediately after the numeric reference, so the citation does not trigger
        a mid-sentence split but the next sentence is still recognized.

        \\2 is the numeric reference itself; \\7 is the trailing whitespace.
        Group structure is defined in lang/common/common.py NUMBERED_REFERENCE_REGEX.
        """
        # https://github.com/diasks2/pragmatic_segmenter/commit/d9ec1a352aff92b91e2e572c30bb9561eb42c703
        return self.profile.numbered_ref_re.sub(r"∯\2\r\7", text)

    def check_for_punctuation(self, txt: str) -> list[str]:
        if any(p in txt for p in self.lang.Punctuations):
            sents = self.process_text(txt)
            return sents
        else:
            # NOTE: next steps of check_for_punctuation will unpack this list
            return [txt]

    def process_text(self, txt: str) -> list[str]:
        for phase in self._boundary_processing_phases():
            txt = phase(txt)
        return self.sentence_boundary_punctuation(txt)

    def _ensure_terminal_marker(self, text: str) -> str:
        if text[-1] not in self.lang.Punctuations:
            return text + "ȸ"
        return text

    def _apply_exclamation_word_rules(self, text: str) -> str:
        return ExclamationWords.apply_rules(text)

    def _apply_double_punctuation_rules(self, text: str) -> str:
        # handle text having only doublepunctuations
        if not self.profile.double_punct_re.match(text):
            return apply_rules(text, *self.lang.DoublePunctuationRules.All)
        return text

    def _apply_quotation_punctuation_rules(self, text: str) -> str:
        return apply_rules(text, self.lang.QuestionMarkInQuotationRule, *self.lang.ExclamationPointRules.All)

    def _replace_list_parens(self, text: str) -> str:
        return self.profile.list_item_replacer_cls(text).replace_parens()

    def replace_numbers(self, text: str) -> str:
        return apply_rules(text, *self.lang.Numbers.All)

    def abbreviations_replacer(self, text: str):
        return self.profile.abbreviation_replacer_cls(text, self.lang, split_mode=self.split_mode)

    def replace_abbreviations(self, text: str) -> str:
        return self.abbreviations_replacer(text).replace()

    def between_punctuation_processor(self, txt: str):
        return self.profile.between_punctuation_cls(txt)

    def between_punctuation(self, txt: str) -> str:
        txt = self.between_punctuation_processor(txt).replace()
        return txt

    def sentence_boundary_punctuation(self, txt: str) -> list[str]:
        # A period followed by a comma is never a sentence boundary.
        txt = _PERIOD_BEFORE_COMMA_RE.sub("∯", txt)
        if self.profile.colon_rule is not None:
            txt = apply_rules(txt, self.profile.colon_rule)
        if self.profile.comma_rule is not None:
            txt = apply_rules(txt, self.profile.comma_rule)
        # retain exclamation mark if it is an ending character of a given text
        txt = _TRAILING_EXCL_RE.sub("!", txt)
        txt = [m.group() for m in self.profile.sentence_boundary_re.finditer(txt)]
        return txt
