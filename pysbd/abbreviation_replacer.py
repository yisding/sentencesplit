# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import List

from pysbd.utils import apply_rules


def _replace_with_escape(txt: str, escaped: str, suffix_pattern: str, replacement: str) -> str:
    """Replace period after abbreviation match using pre-escaped abbreviation."""
    txt = " " + txt
    txt = re.sub(rf"(?<=\s{escaped}){suffix_pattern}", replacement, txt)
    return txt[1:]


class _AbbreviationData:
    """Pre-computed abbreviation data for a language, cached per Abbreviation class."""
    __slots__ = ('abbreviations', 'prepositive_set', 'number_abbr_set')

    def __init__(self, lang_abbreviation_class):
        raw = lang_abbreviation_class.ABBREVIATIONS
        sorted_abbrs = sorted(raw, key=len, reverse=True)
        self.abbreviations = []
        for abbr in sorted_abbrs:
            stripped = abbr.strip()
            stripped_lower = stripped.lower()
            escaped = re.escape(stripped)
            # Pre-compile the two findall patterns for this abbreviation
            match_re = re.compile(
                r"(?:^|\s|\r|\n){}".format(escaped), re.IGNORECASE
            )
            next_word_re = re.compile(
                r"(?<={{{escaped}}} ).{{1}}".format(escaped=escaped)
            )
            self.abbreviations.append((
                stripped,
                stripped_lower,
                escaped,
                match_re,
                next_word_re,
            ))
        self.prepositive_set = frozenset(
            a.lower() for a in lang_abbreviation_class.PREPOSITIVE_ABBREVIATIONS
        )
        self.number_abbr_set = frozenset(
            a.lower() for a in lang_abbreviation_class.NUMBER_ABBREVIATIONS
        )


class AbbreviationReplacer:
    _data_cache: dict[int, _AbbreviationData] = {}

    def __init__(self, text: str, lang) -> None:
        self.text = text
        self.lang = lang
        abbr_class_id = id(lang.Abbreviation)
        if abbr_class_id not in AbbreviationReplacer._data_cache:
            AbbreviationReplacer._data_cache[abbr_class_id] = _AbbreviationData(lang.Abbreviation)
        self._data = AbbreviationReplacer._data_cache[abbr_class_id]

    def replace(self) -> str:
        self.text = apply_rules(
            self.text,
            self.lang.PossessiveAbbreviationRule,
            self.lang.KommanditgesellschaftRule,
            *self.lang.SingleLetterAbbreviationRules.All
        )
        lines: List[str] = []
        for line in self.text.splitlines(True):
            lines.append(self.search_for_abbreviations_in_string(line))
        self.text = "".join(lines)
        self.replace_multi_period_abbreviations()
        self.text = apply_rules(self.text, *self.lang.AmPmRules.All)
        self.text = self.replace_abbreviation_as_sentence_boundary()
        return self.text

    def replace_abbreviation_as_sentence_boundary(self) -> str:
        sent_starters = "|".join((r"(?=\s{}\s)".format(word) for word in self.SENTENCE_STARTERS))
        regex = r"(U∯S|U\.S|U∯K|E∯U|E\.U|U∯S∯A|U\.S\.A|I|i.v|I.V)∯({})".format(sent_starters)
        self.text = re.sub(regex, '\\1.', self.text)
        return self.text

    def replace_multi_period_abbreviations(self) -> None:
        def mpa_replace(match):
            match = match.group()
            match = match.replace(".", "∯")
            return match

        self.text = re.sub(
            self.lang.MULTI_PERIOD_ABBREVIATION_REGEX,
            mpa_replace,
            self.text,
            flags=re.IGNORECASE
        )

    def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
        txt = " " + txt
        if escaped is None:
            escaped = re.escape(abbr.strip())
        txt = re.sub(
            r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())))".format(
                abbr=escaped
            ),
            "∯",
            txt,
        )
        return txt[1:]

    def search_for_abbreviations_in_string(self, text: str) -> str:
        lowered = text.lower()
        data = self._data
        for stripped, stripped_lower, escaped, match_re, next_word_re in data.abbreviations:
            if stripped_lower not in lowered:
                continue
            abbrev_match = match_re.findall(text)
            if not abbrev_match:
                continue
            char_array = next_word_re.findall(text)
            for ind, match in enumerate(abbrev_match):
                text = self.scan_for_replacements(
                    text, match, ind, char_array, stripped, escaped
                )
        return text

    def scan_for_replacements(self, txt: str, am: str, ind: int, char_array,
                              stripped: str = "", escaped: str | None = None) -> str:
        try:
            char = char_array[ind]
        except IndexError:
            char = ""
        upper = char.isupper() if char else False
        am_lower = am.strip().lower()
        if not upper or am_lower in self._data.prepositive_set:
            # Use match-derived escape to preserve original case
            am_escaped = re.escape(am.strip())
            if am_lower in self._data.prepositive_set:
                txt = _replace_with_escape(txt, am_escaped, r'\.(?=(\s|:\d+))', '∯')
            elif am_lower in self._data.number_abbr_set:
                txt = _replace_with_escape(txt, am_escaped, r'\.(?=(\s\d|\s+\())', '∯')
            else:
                txt = self.replace_period_of_abbr(txt, am, am_escaped)
        return txt
