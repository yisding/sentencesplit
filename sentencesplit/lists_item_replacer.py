# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import string
from functools import partial

from sentencesplit.utils import Rule, apply_rules, split_mode_rank

# Constant patterns compiled once at import instead of recompiled per call.
# Newline-separated list-marker guards: a list spanning lines is not collapsed.
_MULTILINE_BULLET_GUARD_RE = re.compile(r"♨.+(\n|\r).+♨")
_MULTILINE_PAREN_MARKER_GUARD_RE = re.compile(r"☝.+\n.+☝|☝.+\r.+☝")
# Every numbered-list pattern requires a digit; used to skip the scan on
# digit-free text (matches re's \d Unicode-digit semantics exactly).
_DIGIT_RE = re.compile(r"\d")


class ListItemReplacer:
    ROMAN_NUMERALS = "i ii iii iv v vi vii viii ix x xi xii xiii xiv xv xvi xvii xviii xix xx".split(" ")
    LATIN_NUMERALS = list(string.ascii_lowercase)

    # Rubular: http://rubular.com/r/XcpaJKH0sz
    ALPHABETICAL_LIST_WITH_PERIODS = r"(?<=^)[a-z](?=\.)|(?<=\A)[a-z](?=\.)|(?<=\s)[a-z](?=\.)"

    # Rubular: http://rubular.com/r/Gu5rQapywf
    ALPHABETICAL_LIST_WITH_PARENS = r"(?<=\()[a-z]+(?=\))|(?<=^)[a-z]+(?=\))|(?<=\A)[a-z]+(?=\))|(?<=\s)[a-z]+(?=\))"

    # (pattern, replacement)
    SubstituteListPeriodRule = Rule("♨", "∯")
    ListMarkerRule = Rule("☝", "")

    # Rubular: http://rubular.com/r/Wv4qLdoPx7
    # https://regex101.com/r/62YBlv/1
    SpaceBetweenListItemsFirstRule = Rule(r"(?<=\S\S)\s(?=\S\s*\d+♨)", "\r")

    # Rubular: http://rubular.com/r/AizHXC6HxK
    # https://regex101.com/r/62YBlv/2
    SpaceBetweenListItemsSecondRule = Rule(r"(?<=\S\S)\s(?=\d{1,2}♨)", "\r")

    # Rubular: http://rubular.com/r/GE5q6yID2j
    # https://regex101.com/r/62YBlv/3
    SpaceBetweenListItemsThirdRule = Rule(r"(?<=\S\S)\s(?=\d{1,2}☝)", "\r")

    NUMBERED_LIST_REGEX_1 = r"\s\d{1,2}(?=\.\s)|^\d{1,2}(?=\.\s)|\s\d{1,2}(?=\.\))|^\d{1,2}(?=\.\))|(?<=\s\-)\d{1,2}(?=\.\s)|(?<=^\-)\d{1,2}(?=\.\s)|(?<=\s\⁃)\d{1,2}(?=\.\s)|(?<=^\⁃)\d{1,2}(?=\.\s)|(?<=\s\-)\d{1,2}(?=\.\))|(?<=^\-)\d{1,2}(?=\.\))|(?<=\s\⁃)\d{1,2}(?=\.\))|(?<=^\⁃)\d{1,2}(?=\.\))"
    # 1. abcd
    # 2. xyz
    NUMBERED_LIST_REGEX_2 = r"(?<=\s)\d{1,2}\.(?=\s)|^\d{1,2}\.(?=\s)|(?<=\s)\d{1,2}\.(?=\))|^\d{1,2}\.(?=\))|(?<=\s\-)\d{1,2}\.(?=\s)|(?<=^\-)\d{1,2}\.(?=\s)|(?<=\s\⁃)\d{1,2}\.(?=\s)|(?<=^\⁃)\d{1,2}\.(?=\s)|(?<=\s\-)\d{1,2}\.(?=\))|(?<=^\-)\d{1,2}\.(?=\))|(?<=\s\⁃)\d{1,2}\.(?=\))|(?<=^\⁃)\d{1,2}\.(?=\))"
    # 1) abcd
    # 2) xyz
    NUMBERED_LIST_PARENS_REGEX = r"\d{1,2}(?=\)\s)"

    # Rubular: http://rubular.com/r/NsNFSqrNvJ
    EXTRACT_ALPHABETICAL_LIST_LETTERS_REGEX = r"\([a-z]+(?=\))|(?<=^)[a-z]+(?=\))|(?<=\A)[a-z]+(?=\))|(?<=\s)[a-z]+(?=\))"

    # Rubular: http://rubular.com/r/wMpnVedEIb
    ALPHABETICAL_LIST_LETTERS_AND_PERIODS_REGEX = r"(?<=^)[a-z]\.|(?<=\A)[a-z]\.|(?<=\s)[a-z]\."

    # Rubular: http://rubular.com/r/GcnmQt4a3I
    ROMAN_NUMERALS_IN_PARENTHESES = r"\(((?=[mdclxvi])m*(c[md]|d?c*)(x[cl]|l?x*)(i[xv]|v?i*))\)(?=\s[A-Z])"
    _ROMAN_NUMERALS_IN_PARENTHESES_RE = re.compile(ROMAN_NUMERALS_IN_PARENTHESES)

    # A false-positive guard for numbered lists. Some adjacent ordinals are
    # prose, not list items (e.g. English "for 1. above ... 2. above" or German
    # "des 19. und ... 20. Jahrhunderts"). The connector must bridge two
    # numbered markers so real lists like "1. and gates 2. or gates" still split.
    # Languages may override this (or set it to None to disable the guard).
    NUMBERED_LIST_FALSE_POSITIVE_REGEX = r"\d{1,2}♨\s+(?:above|and|below|or|bis|bzw|sowie|und|oder)\b[^♨\r\n]{0,80}\s\d{1,2}♨"

    def __init__(self, text: str, split_mode: str = "balanced") -> None:
        self.text = text
        self.split_mode = split_mode

    def add_line_break(self):
        self.format_alphabetical_lists()
        self.format_roman_numeral_lists()
        self.format_numbered_list_with_periods()
        self.format_numbered_list_with_parens()
        return self.text

    def replace_parens(self):
        self.text = self._ROMAN_NUMERALS_IN_PARENTHESES_RE.sub(r"&✂&\1&⌬&", self.text)
        return self.text

    def format_numbered_list_with_parens(self):
        self.replace_parens_in_numbered_list()
        self.add_line_breaks_for_numbered_list_with_parens()
        self.text = apply_rules(self.text, self.ListMarkerRule)

    def replace_periods_in_numbered_list(self):
        self.scan_lists(self.NUMBERED_LIST_REGEX_1, self.NUMBERED_LIST_REGEX_2, "♨", strip=True)

    def format_numbered_list_with_periods(self):
        self.replace_periods_in_numbered_list()
        self.add_line_breaks_for_numbered_list_with_periods()
        self.text = apply_rules(self.text, self.SubstituteListPeriodRule)

    def format_alphabetical_lists(self):
        self.add_line_breaks_for_alphabetical_list_with_periods(roman_numeral=False)
        self.add_line_breaks_for_alphabetical_list_with_parens(roman_numeral=False)

    def format_roman_numeral_lists(self):
        self.add_line_breaks_for_alphabetical_list_with_periods(roman_numeral=True)
        self.add_line_breaks_for_alphabetical_list_with_parens(roman_numeral=True)

    def add_line_breaks_for_alphabetical_list_with_periods(self, roman_numeral=False):
        self.iterate_alphabet_array(self.ALPHABETICAL_LIST_WITH_PERIODS, roman_numeral=roman_numeral)

    def add_line_breaks_for_alphabetical_list_with_parens(self, roman_numeral=False):
        self.iterate_alphabet_array(self.ALPHABETICAL_LIST_WITH_PARENS, parens=True, roman_numeral=roman_numeral)

    def scan_lists(self, regex1, regex2, replacement, strip=False):
        # All numbered-list patterns require a digit (and the body does int()),
        # so digit-free text can't match — skip the two finditer scans. The loop
        # below never runs on empty matches, so this is byte-identical.
        if not _DIGIT_RE.search(self.text):
            return
        matches = list(re.finditer(regex1, self.text))
        list_array = [(int(m.group().strip()), m.start()) for m in matches]
        for ind, (item, pos) in enumerate(list_array):
            found_forward = False
            if ind < len(list_array) - 1:
                next_item, next_pos = list_array[ind + 1]
                if item + 1 == next_item and next_pos - pos < 200:
                    self.substitute_found_list_items(regex2, item, strip, replacement)
                    found_forward = True
            if not found_forward and ind > 0:
                prev_item, prev_pos = list_array[ind - 1]
                if pos - prev_pos < 200 and (
                    ((item - 1) == prev_item) or ((item == 0) and (prev_item == 9)) or ((item == 9) and (prev_item == 0))
                ):
                    self.substitute_found_list_items(regex2, item, strip, replacement)

    def substitute_found_list_items(self, regex, each, strip, replacement):

        def replace_item(match, strip=False):
            match = match.group()
            if strip:
                match = match.strip()
            chomped_match = match if len(match) == 1 else match.strip(".])")
            if str(each) == chomped_match:
                return "{}{}".format(each, replacement)
            else:
                return match

        self.text = re.sub(regex, partial(replace_item, strip=strip), self.text)

    @staticmethod
    def _is_embedded_numbered_marker(text: str, marker_start: int) -> bool:
        index = marker_start - 1
        while index >= 0 and text[index].isspace():
            index -= 1
        if index < 0:
            return False
        return text[index] not in ".:;!?([{\r\n"

    def add_line_breaks_for_numbered_list_with_periods(self):
        false_positive = self.NUMBERED_LIST_FALSE_POSITIVE_REGEX
        if split_mode_rank(self.split_mode) >= 2:
            # aggressive: disable the prose-ordinal guard, so a single-line run
            # of ordinals before lowercase words ("des 19. und 20. …") is split
            # as a numbered list rather than kept as prose.
            false_positive = None

        text_for_breaks = self.text
        if false_positive is not None:
            text_for_breaks = re.sub(
                false_positive,
                lambda match: (
                    match.group().replace("♨", "∯")
                    if self._is_embedded_numbered_marker(text_for_breaks, match.start())
                    else match.group()
                ),
                text_for_breaks,
            )

        if (text_for_breaks.count("♨") >= 2) and (not _MULTILINE_BULLET_GUARD_RE.search(text_for_breaks)):
            self.text = apply_rules(
                text_for_breaks,
                self.SpaceBetweenListItemsFirstRule,
                self.SpaceBetweenListItemsSecondRule,
            )
        else:
            self.text = text_for_breaks

    def replace_parens_in_numbered_list(self):
        self.scan_lists(self.NUMBERED_LIST_PARENS_REGEX, self.NUMBERED_LIST_PARENS_REGEX, "☝")

    def add_line_breaks_for_numbered_list_with_parens(self):
        if "☝" in self.text and not _MULTILINE_PAREN_MARKER_GUARD_RE.search(self.text):
            self.text = apply_rules(
                self.text,
                self.SpaceBetweenListItemsThirdRule,
            )

    def replace_alphabet_list(self, a):
        """
        Input: 'a. ffegnog b. fgegkl c.'
        Output: \ra∯ ffegnog \rb∯ fgegkl \rc∯
        """

        def replace_letter_period(match, val=None):
            match = match.group()
            match_wo_period = match.strip(".")
            if match_wo_period == val:
                return "\r{}∯".format(match_wo_period)
            else:
                return match

        self.text = re.sub(
            self.ALPHABETICAL_LIST_LETTERS_AND_PERIODS_REGEX,
            partial(replace_letter_period, val=a),
            self.text,
            flags=re.IGNORECASE,
        )

    def replace_alphabet_list_parens(self, a):
        """
        Input: "a) ffegnog (b) fgegkl c)"
        Output: "\ra) ffegnog \r&✂&b) fgegkl \rc)"
        """

        def replace_alphabet_paren(match, val=None):
            match = match.group()
            if "(" in match:
                match_wo_paren = match.strip("(")
                if match_wo_paren == val:
                    return "\r&✂&{}".format(match_wo_paren)
                else:
                    return match
            else:
                if match == val:
                    return "\r{}".format(match)
                else:
                    return match

        # Make it cases-insensitive
        self.text = re.sub(
            self.EXTRACT_ALPHABETICAL_LIST_LETTERS_REGEX,
            partial(replace_alphabet_paren, val=a),
            self.text,
            flags=re.IGNORECASE,
        )

    def replace_correct_alphabet_list(self, a, parens):
        if parens:
            self.replace_alphabet_list_parens(a)
        else:
            self.replace_alphabet_list(a)

    def last_array_item_replacement(self, a, i, alphabet, alphabet_index, list_array, parens):
        if i == 0:
            return self.text
        if not alphabet and not list_array:
            return
        if list_array[i - 1] not in alphabet:
            return
        if a not in alphabet:
            return
        if alphabet_index[a] - alphabet_index[list_array[i - 1]] != 1:
            return
        self.replace_correct_alphabet_list(a, parens)

    def other_items_replacement(self, a, i, alphabet, alphabet_index, list_array, parens):
        if not alphabet and not list_array:
            return
        if a not in alphabet:
            return
        if list_array[i + 1] not in alphabet:
            return
        forward_match = alphabet_index[list_array[i + 1]] - alphabet_index[a] == 1
        backward_match = i > 0 and list_array[i - 1] in alphabet and alphabet_index[a] - alphabet_index[list_array[i - 1]] == 1
        if not forward_match and not backward_match:
            return
        self.replace_correct_alphabet_list(a, parens)

    def iterate_alphabet_array(self, regex, parens=False, roman_numeral=False):
        list_array = re.findall(regex, self.text, re.IGNORECASE)
        # Common case on list-free text: no markers found. Skip the lowercasing,
        # the per-call alphabet-index dict build, and the filter — with an empty
        # list the replacement loop below never runs, so this is byte-identical.
        if not list_array:
            return
        list_array = [i.lower() for i in list_array]
        alphabet = self.ROMAN_NUMERALS if roman_numeral else self.LATIN_NUMERALS
        alphabet_index = {value: index for index, value in enumerate(alphabet)}
        list_array = [i for i in list_array if i in alphabet]
        for ind, each in enumerate(list_array):
            if ind == len(list_array) - 1:
                self.last_array_item_replacement(each, ind, alphabet, alphabet_index, list_array, parens)
            else:
                self.other_items_replacement(each, ind, alphabet, alphabet_index, list_array, parens)
