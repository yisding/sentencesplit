# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import CJKBoundaryProfile
from sentencesplit.lang.english import English
from sentencesplit.lang.spanish import Spanish
from sentencesplit.processor import (
    _CJK_QUOTE_RESPLIT_RE,
    _ELLIPSIS_RE,
    _ORPHAN_SINGLE_CHARS,
    Processor,
    _split_on_uppercase_boundary,
    _sub_symbols_fast,
)
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule, apply_rules

_LATIN_PAREN_RESPLIT_RE = re.compile(r"(?<=[a-zA-Z]{2}\.\))\s+")
_CJK_FOLLOWING_CHAR_RE = re.compile(r"[\u3400-\u9FFF]")
_ENGLISH_HEURISTIC_ABBREVIATIONS = frozenset(a.lower() for a in Standard.Abbreviation.ABBREVIATIONS)
_QUOTE_CLOSER_RE = re.compile(r"""["'”’」』》】]+$""")
_CJK_SLANTED_QUOTE_END_RE = re.compile(r"(&ᓰ&|&ᓱ&|&ᓳ&|&ᓴ&|&ᓷ&|&ᓸ&)(?=[”’][^\s])")
_CJK_REPORTING_CLAUSE_BOUNDARY = r"(?=$|[，,：:。．.!！?？…])"
_CJK_REPORTING_CLAUSE_RE = re.compile(
    rf"^(?:他|她|他们|她们|我|我们|记者|警方|老师|母亲|父亲|主持人|发言人).{{0,6}}(?:说|问|答|表示|回应|补充|解释){_CJK_REPORTING_CLAUSE_BOUNDARY}"
)
_RESTORE_CJK_TERMINAL_PUNCT = {
    "&ᓰ&": "。",
    "&ᓱ&": "．",
    "&ᓳ&": "！",
    "&ᓴ&": "!",
    "&ᓷ&": "?",
    "&ᓸ&": "？",
}


class EnglishSpanishChinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "en_es_zh"

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = sorted(set(Standard.Abbreviation.ABBREVIATIONS + Spanish.Abbreviation.ABBREVIATIONS))
        PREPOSITIVE_ABBREVIATIONS = sorted(
            set(Standard.Abbreviation.PREPOSITIVE_ABBREVIATIONS + Spanish.Abbreviation.PREPOSITIVE_ABBREVIATIONS)
        )
        NUMBER_ABBREVIATIONS = sorted(
            set(Standard.Abbreviation.NUMBER_ABBREVIATIONS + Spanish.Abbreviation.NUMBER_ABBREVIATIONS)
        )

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = English.AbbreviationReplacer.SENTENCE_STARTERS

        def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
            txt = " " + txt
            if escaped is None:
                escaped = re.escape(abbr.strip())
            txt = re.sub(
                rf"(?<=\s{escaped})\.(?=(?:[.:\-?,]|\s(?:[^\W\d_]|I\s|I'm|I'll|\d|\()|[\u3400-\u9FFF]))",
                "∯",
                txt,
            )
            return txt[1:]

        def scan_for_replacements(
            self, txt: str, am: str, ind: int, char_array, stripped: str = "", escaped: str | None = None
        ) -> str:
            try:
                char = char_array[ind]
            except IndexError:
                char = ""
            am_lower = am.strip().lower()
            ascii_upper = bool(char) and char.isascii() and char.isupper()
            use_uppercase_heuristic = ascii_upper and am_lower in _ENGLISH_HEURISTIC_ABBREVIATIONS
            if not use_uppercase_heuristic or am_lower in self._data.prepositive_set:
                am_escaped = re.escape(am.strip())
                txt = " " + txt
                if am_lower in self._data.prepositive_set:
                    should_protect_prepositive = not (
                        self.split_mode == "aggressive" and am_lower in self.AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST
                    )
                    if should_protect_prepositive:
                        txt = re.sub(rf"(?<=\s{am_escaped})\.(?=(?:\s|:\d+|[\u3400-\u9FFF]))", "∯", txt)
                elif am_lower in self._data.number_abbr_set:
                    txt = re.sub(rf"(?<=\s{am_escaped})\.(?=(?:\s\d|\s+\(|\s[IVXLCDM]+\b|[\u3400-\u9FFF]))", "∯", txt)
                else:
                    txt = self.replace_period_of_abbr(txt[1:], am, am_escaped)
                    return txt
                txt = txt[1:]
            elif am_lower in self._data.number_abbr_set:
                # Next word starts ASCII uppercase — protect only before Roman numerals.
                # Exclude lone "I" to avoid false joins with the pronoun "I".
                am_escaped = re.escape(am.strip())
                txt = " " + txt
                txt = re.sub(rf"(?<=\s{am_escaped})\.(?=\s(?:[IVXLCDM]{{2,}}|[VXLCDM])\b)", "∯", txt)
                txt = txt[1:]
            return txt

    class CjkAbbreviationRules:
        IntraAbbreviationPeriodRule = Rule(r"(?<=[A-Za-z])\.(?=[A-Za-z]\.)", "∯")
        EndAbbreviationBeforeCjkRule = Rule(r"(?<=[A-Za-z]∯[A-Za-z])\.(?=[\u3400-\u9FFF])", "∯")

        All = [IntraAbbreviationPeriodRule, EndAbbreviationBeforeCjkRule]

    class BetweenPunctuation(BetweenPunctuation):
        def replace(self) -> str:
            txt = super().replace()
            txt = self.sub_punctuation_between_double_angled_quotation_marks(txt)
            txt = self.sub_punctuation_between_cn_brackets(txt)
            txt = self.sub_punctuation_between_cn_corner_quotes(txt)
            txt = self.sub_punctuation_between_cn_parens(txt)
            txt = _CJK_SLANTED_QUOTE_END_RE.sub(lambda match: _RESTORE_CJK_TERMINAL_PUNCT[match.group(1)], txt)
            return txt

        def sub_punctuation_between_double_angled_quotation_marks(self, txt: str) -> str:
            return re.sub(r"《(?=(?P<tmp>[^》\\]+|\\{2}|\\.)*)(?P=tmp)》", replace_punctuation, txt)

        def sub_punctuation_between_cn_brackets(self, txt: str) -> str:
            return re.sub(r"「(?=(?P<tmp>[^」\\]+|\\{2}|\\.)*)(?P=tmp)」", replace_punctuation, txt)

        def sub_punctuation_between_cn_corner_quotes(self, txt: str) -> str:
            return re.sub(r"『(?=(?P<tmp>[^』\\]+|\\{2}|\\.)*)(?P=tmp)』", replace_punctuation, txt)

        def sub_punctuation_between_cn_parens(self, txt: str) -> str:
            return re.sub(r"（(?=(?P<tmp>[^）\\]+|\\{2}|\\.)*)(?P=tmp)）", replace_punctuation, txt)

    class Processor(Processor):
        def split_into_segments(self) -> list[str]:
            self.check_for_parens_between_quotes()
            sents = self.text.split("\r")
            sents = self.rm_none_flatten(sents)
            sents = [apply_rules(s, self.lang.SingleNewLineRule, *self.lang.EllipsisRules.All) for s in sents]
            sents = [self.check_for_punctuation(s) for s in sents]
            sents = self.rm_none_flatten(sents)

            postprocessed_sents = []
            for sent in sents:
                sent = _sub_symbols_fast(sent, self.lang)
                for pps in self.post_process_segments(sent):
                    if pps:
                        postprocessed_sents.append(pps)

            postprocessed_sents = [apply_rules(ns, self.lang.SubSingleQuoteRule) for ns in postprocessed_sents]
            resplit = []
            for pps in postprocessed_sents:
                latin_parts = _split_on_uppercase_boundary(pps, _LATIN_PAREN_RESPLIT_RE)
                for latin_part in latin_parts or [pps]:
                    if not latin_part:
                        continue
                    parts = _CJK_QUOTE_RESPLIT_RE.split(latin_part)
                    resplit.extend(part for part in parts if part)
            resplit = self._merge_quote_continuations(resplit or postprocessed_sents)
            return self._merge_orphans(resplit)

        def _merge_quote_continuations(self, sentences: list[str]) -> list[str]:
            merged: list[str] = []
            idx = 0
            while idx < len(sentences):
                current = sentences[idx]
                if merged and self._should_merge_quote_continuation(merged[-1], current):
                    separator = "" if _CJK_FOLLOWING_CHAR_RE.match(current.lstrip()) else " "
                    merged[-1] = merged[-1] + separator + current.lstrip()
                else:
                    merged.append(current)
                idx += 1
            return merged

        def _should_merge_quote_continuation(self, previous: str, current: str) -> bool:
            previous = previous.rstrip()
            current = current.lstrip()
            if not previous or not current:
                return False
            if not _QUOTE_CLOSER_RE.search(previous):
                return False
            first_char = current[0]
            if first_char.islower():
                return True
            if _CJK_REPORTING_CLAUSE_RE.match(current):
                return True
            return False

        def _merge_orphans(self, sentences: list[str]) -> list[str]:
            merged = []
            for sent in sentences:
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
                        and any(c.isalnum() or _CJK_FOLLOWING_CHAR_RE.match(c) for c in stripped)
                    ):
                        is_orphan = True
                if is_orphan:
                    if len(stripped) == 1 and stripped in _ORPHAN_SINGLE_CHARS:
                        merged[-1] = merged[-1] + sent
                    else:
                        merged[-1] = merged[-1] + " " + sent
                else:
                    merged.append(sent)
            return merged
