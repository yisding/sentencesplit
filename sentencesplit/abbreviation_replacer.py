# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from collections import deque
from typing import List

from sentencesplit.utils import apply_rules

# Pre-compiled pattern for multi-period abbreviation boundary restoration
_MULTI_PERIOD_BOUNDARY_RE = re.compile(r"(?<=[a-zA-Z]∯[a-zA-Z]∯[a-zA-Z])∯(?=\s[A-Z])")


class AhoCorasickAutomaton:
    """Pure-Python Aho-Corasick automaton for multi-pattern substring search."""

    __slots__ = ("goto", "fail", "output", "_built")

    def __init__(self):
        # State 0 is the root. Each state maps char -> next_state.
        self.goto: list[dict[str, int]] = [{}]
        self.output: list[list[int]] = [[]]  # pattern IDs at each state
        self.fail: list[int] = [0]
        self._built = False

    def add_pattern(self, pattern: str, pattern_id: int) -> None:
        state = 0
        for ch in pattern:
            nxt = self.goto[state].get(ch)
            if nxt is None:
                nxt = len(self.goto)
                self.goto.append({})
                self.output.append([])
                self.fail.append(0)
                self.goto[state][ch] = nxt
            state = nxt
        self.output[state].append(pattern_id)

    def build(self) -> None:
        queue: deque[int] = deque()
        # Initialize depth-1 states
        for ch, s in self.goto[0].items():
            self.fail[s] = 0
            queue.append(s)
        # BFS to build failure links
        while queue:
            r = queue.popleft()
            for ch, s in self.goto[r].items():
                queue.append(s)
                state = self.fail[r]
                while state != 0 and ch not in self.goto[state]:
                    state = self.fail[state]
                self.fail[s] = self.goto[state].get(ch, 0)
                if self.fail[s] == s:
                    self.fail[s] = 0
                if self.output[self.fail[s]]:
                    self.output[s] = self.output[s] + self.output[self.fail[s]]
        self._built = True

    def search(self, text: str) -> set[int]:
        """Scan text in one pass, return set of matched pattern IDs."""
        state = 0
        found: set[int] = set()
        goto = self.goto
        fail = self.fail
        output = self.output
        for ch in text:
            while state != 0 and ch not in goto[state]:
                state = fail[state]
            state = goto[state].get(ch, 0)
            if output[state]:
                found.update(output[state])
        return found


def _replace_with_escape(txt: str, escaped: str, suffix_pattern: str, replacement: str) -> str:
    """Replace period after abbreviation match using pre-escaped abbreviation."""
    txt = " " + txt
    txt = re.sub(rf"(?<=\s{escaped}){suffix_pattern}", replacement, txt)
    return txt[1:]


class _AbbreviationData:
    """Pre-computed abbreviation data for a language, cached per Abbreviation class."""

    __slots__ = ("abbreviations", "prepositive_set", "number_abbr_set", "automaton")

    def __init__(self, lang_abbreviation_class):
        raw = lang_abbreviation_class.ABBREVIATIONS
        sorted_abbrs = sorted(raw, key=len, reverse=True)
        self.prepositive_set = frozenset(a.lower() for a in lang_abbreviation_class.PREPOSITIVE_ABBREVIATIONS)
        self.number_abbr_set = frozenset(a.lower() for a in lang_abbreviation_class.NUMBER_ABBREVIATIONS)
        self.abbreviations = []
        self.automaton = AhoCorasickAutomaton()
        for idx, abbr in enumerate(sorted_abbrs):
            stripped = abbr.strip()
            stripped_lower = stripped.lower()
            escaped = re.escape(stripped)
            # Pre-compile the two findall patterns for this abbreviation
            match_re = re.compile(r"(?:^|\s|\r|\n){}".format(escaped), re.IGNORECASE)
            next_word_re = re.compile(r"(?<={{{escaped}}} ).{{1}}".format(escaped=escaped))
            self.abbreviations.append(
                (
                    stripped,
                    stripped_lower,
                    escaped,
                    match_re,
                    next_word_re,
                )
            )
            self.automaton.add_pattern(stripped_lower, idx)
        self.automaton.build()


class AbbreviationReplacer:
    _data_cache: dict[int, _AbbreviationData] = {}
    _sent_starters_cache: dict[int, re.Pattern] = {}

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
            *self.lang.SingleLetterAbbreviationRules.All,
        )
        lines: List[str] = []
        for line in self.text.splitlines(True):
            lines.append(self.search_for_abbreviations_in_string(line))
        self.text = "".join(lines)
        self.replace_multi_period_abbreviations()
        # Restore sentence-boundary period when a multi-period abbreviation
        # with 3+ parts (e.g. "e∯s∯t∯") is followed by a space and
        # uppercase letter.  Two-part abbreviations like U∯S∯ are handled
        # separately by replace_abbreviation_as_sentence_boundary.
        # Note: no IGNORECASE — [A-Z] in lookahead must only match uppercase
        # so that "C.E.O. of" is not mistakenly split.
        self.text = _MULTI_PERIOD_BOUNDARY_RE.sub(".", self.text)
        self.text = apply_rules(self.text, *self.lang.AmPmRules.All)
        self.text = self.replace_abbreviation_as_sentence_boundary()
        return self.text

    def _get_sent_starters_re(self) -> re.Pattern:
        """Get or build the cached sentence-starters regex for this class."""
        cls = type(self)
        cls_id = id(cls)
        if cls_id not in AbbreviationReplacer._sent_starters_cache:
            sent_starters = "|".join(r"(?=\s{}\s)".format(word) for word in self.SENTENCE_STARTERS)
            regex = r"(U∯S|U\.S|U∯K|E∯U|E\.U|U∯S∯A|U\.S\.A|I|i.v|I.V)∯({})".format(sent_starters)
            AbbreviationReplacer._sent_starters_cache[cls_id] = re.compile(regex)
        return AbbreviationReplacer._sent_starters_cache[cls_id]

    def replace_abbreviation_as_sentence_boundary(self) -> str:
        self.text = self._get_sent_starters_re().sub("\\1.", self.text)
        return self.text

    def replace_multi_period_abbreviations(self) -> None:
        def mpa_replace(match):
            match = match.group()
            match = match.replace(".", "∯")
            return match

        self.text = self.lang.MULTI_PERIOD_ABBREVIATION_REGEX.sub(mpa_replace, self.text)

    def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
        txt = " " + txt
        if escaped is None:
            escaped = re.escape(abbr.strip())
        txt = re.sub(
            r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())))".format(abbr=escaped),
            "∯",
            txt,
        )
        return txt[1:]

    def search_for_abbreviations_in_string(self, text: str) -> str:
        lowered = text.lower()
        data = self._data
        found_indices = data.automaton.search(lowered)
        abbreviations = data.abbreviations
        for idx in sorted(found_indices):
            stripped, stripped_lower, escaped, match_re, next_word_re = abbreviations[idx]
            abbrev_match = match_re.findall(text)
            if not abbrev_match:
                continue
            char_array = next_word_re.findall(text)
            for ind, match in enumerate(abbrev_match):
                text = self.scan_for_replacements(text, match, ind, char_array, stripped, escaped)
        return text

    def scan_for_replacements(
        self, txt: str, am: str, ind: int, char_array, stripped: str = "", escaped: str | None = None,
    ) -> str:
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
                txt = _replace_with_escape(txt, am_escaped, r"\.(?=(\s|:\d+))", "∯")
            elif am_lower in self._data.number_abbr_set:
                txt = _replace_with_escape(txt, am_escaped, r"\.(?=(\s\d|\s+\())", "∯")
            else:
                txt = self.replace_period_of_abbr(txt, am, am_escaped)
        return txt
