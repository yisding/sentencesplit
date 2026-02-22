# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import List

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.exclamation_words import ExclamationWords
from sentencesplit.lists_item_replacer import ListItemReplacer
from sentencesplit.utils import apply_rules

# Pre-compiled patterns used on the hot path
_ALPHA_ONLY_RE = re.compile(r"\A[a-zA-Z]*\Z")
_ELLIPSIS_RE = re.compile(r"\A\.{3,}\Z")
_TRAILING_EXCL_RE = re.compile(r"&ᓴ&$")
_PAREN_SPACE_BEFORE_RE = re.compile(r"\s(?=\()")
_PAREN_SPACE_AFTER_RE = re.compile(r"(?<=\))\s")
_ORPHAN_SINGLE_CHARS = frozenset("'\")\u2019\u201d")


def _sub_symbols_fast(text, lang):
    """Replace temporary symbols using str.replace() instead of regex."""
    for old, new in lang.SubSymbolsRules.SUBS_TABLE:
        text = text.replace(old, new)
    return text


class Processor:
    def __init__(self, text: str | None, lang, char_span: bool = False) -> None:
        self.text = text
        self.lang = lang
        self.char_span = char_span
        # Cache hasattr lookups
        self._has_abbr_replacer = hasattr(lang, "AbbreviationReplacer")
        self._has_between_punct = hasattr(lang, "BetweenPunctuation")
        self._has_colon_rule = hasattr(lang, "ReplaceColonBetweenNumbersRule")
        self._has_comma_rule = hasattr(lang, "ReplaceNonSentenceBoundaryCommaRule")

    def process(self) -> List[str]:
        if not self.text:
            return []
        self.text = self.text.replace("\n", "\r")
        li = ListItemReplacer(self.text)
        self.text = li.add_line_break()
        self.replace_abbreviations()
        self.replace_numbers()
        self.replace_continuous_punctuation()
        self.replace_periods_before_numeric_references()
        self.text = apply_rules(
            self.text,
            self.lang.Abbreviation.WithMultiplePeriodsAndEmailRule,
            self.lang.GeoLocationRule,
            self.lang.FileFormatRule,
            self.lang.DotNetRule,
        )
        postprocessed_sents = self.split_into_segments()
        return postprocessed_sents

    def rm_none_flatten(self, sents: List[str | List[str] | None]) -> List[str]:
        new_sents = []
        for s in sents:
            if not s:
                continue
            if isinstance(s, list):
                new_sents.extend(s)
            else:
                new_sents.append(s)
        return new_sents

    def split_into_segments(self) -> List[str]:
        self.check_for_parens_between_quotes()
        sents = self.text.split("\r")
        # remove empty and none values
        sents = self.rm_none_flatten(sents)
        sents = [apply_rules(s, self.lang.SingleNewLineRule, *self.lang.EllipsisRules.All) for s in sents]
        sents = [self.check_for_punctuation(s) for s in sents]
        # flatten list of list of sentences
        sents = self.rm_none_flatten(sents)
        postprocessed_sents = []
        for sent in sents:
            sent = _sub_symbols_fast(sent, self.lang)
            for pps in self.post_process_segments(sent):
                if pps:
                    postprocessed_sents.append(pps)
        postprocessed_sents = [apply_rules(ns, self.lang.SubSingleQuoteRule) for ns in postprocessed_sents]
        # Re-split at ".) Capital" boundaries (period inside closing paren before new sentence)
        resplit = []
        for pps in postprocessed_sents:
            parts = re.split(r"(?<=[a-zA-Z]{2}\.\))\s+(?=[A-Z])", pps)
            resplit.extend(p for p in parts if p)
        postprocessed_sents = resplit
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
                merged[-1] = merged[-1] + " " + sent
            else:
                merged.append(sent)
        return merged

    def post_process_segments(self, txt: str) -> List[str]:
        if len(txt) > 2 and _ALPHA_ONLY_RE.search(txt):
            return [txt]

        txt = apply_rules(txt, *self.lang.ReinsertEllipsisRules.All)
        if re.search(self.lang.QUOTATION_AT_END_OF_SENTENCE_REGEX, txt):
            txt = re.split(self.lang.SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX, txt)
            return [t for t in txt if t]
        else:
            txt = txt.replace("\n", "")
            txt = txt.strip()
            return [txt] if txt else []

    def check_for_parens_between_quotes(self) -> None:
        def paren_replace(match):
            match = match.group()
            sub1 = _PAREN_SPACE_BEFORE_RE.sub("\r", match)
            sub2 = _PAREN_SPACE_AFTER_RE.sub("\r", sub1)
            return sub2

        self.text = re.sub(self.lang.PARENS_BETWEEN_DOUBLE_QUOTES_REGEX, paren_replace, self.text)

    def replace_continuous_punctuation(self) -> None:
        def continuous_puncs_replace(match):
            match = match.group()
            match = match.replace("!", "&ᓴ&")
            match = match.replace("?", "&ᓷ&")
            return match

        self.text = re.sub(self.lang.CONTINUOUS_PUNCTUATION_REGEX, continuous_puncs_replace, self.text)

    def replace_periods_before_numeric_references(self) -> None:
        # https://github.com/diasks2/pragmatic_segmenter/commit/d9ec1a352aff92b91e2e572c30bb9561eb42c703
        self.text = re.sub(self.lang.NUMBERED_REFERENCE_REGEX, r"∯\2\r\7", self.text)

    def check_for_punctuation(self, txt: str) -> List[str]:
        if any(p in txt for p in self.lang.Punctuations):
            sents = self.process_text(txt)
            return sents
        else:
            # NOTE: next steps of check_for_punctuation will unpack this list
            return [txt]

    def process_text(self, txt: str) -> List[str]:
        if txt[-1] not in self.lang.Punctuations:
            txt += "ȸ"
        txt = ExclamationWords.apply_rules(txt)
        txt = self.between_punctuation(txt)
        # handle text having only doublepunctuations
        if not re.match(self.lang.DoublePunctuationRules.DoublePunctuation, txt):
            txt = apply_rules(txt, *self.lang.DoublePunctuationRules.All)
        txt = apply_rules(txt, self.lang.QuestionMarkInQuotationRule, *self.lang.ExclamationPointRules.All)
        txt = ListItemReplacer(txt).replace_parens()
        txt = self.sentence_boundary_punctuation(txt)
        return txt

    def replace_numbers(self) -> None:
        self.text = apply_rules(self.text, *self.lang.Numbers.All)

    def abbreviations_replacer(self):
        if self._has_abbr_replacer:
            return self.lang.AbbreviationReplacer(self.text, self.lang)
        else:
            return AbbreviationReplacer(self.text, self.lang)

    def replace_abbreviations(self) -> None:
        self.text = self.abbreviations_replacer().replace()

    def between_punctuation_processor(self, txt: str):
        if self._has_between_punct:
            return self.lang.BetweenPunctuation(txt)
        else:
            return BetweenPunctuation(txt)

    def between_punctuation(self, txt: str) -> str:
        txt = self.between_punctuation_processor(txt).replace()
        return txt

    def sentence_boundary_punctuation(self, txt: str) -> List[str]:
        if self._has_colon_rule:
            txt = apply_rules(txt, self.lang.ReplaceColonBetweenNumbersRule)
        if self._has_comma_rule:
            txt = apply_rules(txt, self.lang.ReplaceNonSentenceBoundaryCommaRule)
        # retain exclamation mark if it is an ending character of a given text
        txt = _TRAILING_EXCL_RE.sub("!", txt)
        txt = [m.group() for m in re.finditer(self.lang.SENTENCE_BOUNDARY_REGEX, txt)]
        return txt
