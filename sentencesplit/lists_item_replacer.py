# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import string
from functools import partial

from sentencesplit.utils import Rule, apply_rules


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

    NUMBERED_LIST_REGEX_1 = r"\s\d{1,2}(?=\.\s)|^\d{1,2}(?=\.\s)|\s\d{1,2}(?=\.\))|^\d{1,2}(?=\.\))|(?<=\s\-)\d{1,2}(?=\.\s)|(?<=^\-)\d{1,2}(?=\.\s)|(?<=\s\⁃)\d{1,2}(?=\.\s)|(?<=^\⁃)\d{1,2}(?=\.\s)|(?<=s\-)\d{1,2}(?=\.\))|(?<=^\-)\d{1,2}(?=\.\))|(?<=\s\⁃)\d{1,2}(?=\.\))|(?<=^\⁃)\d{1,2}(?=\.\))"
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

    def __init__(self, text: str) -> None:
        self.text = text

    def add_line_break(self):
        self.format_alphabetical_lists()
        self.format_roman_numeral_lists()
        self.format_numbered_list_with_periods()
        self.format_numbered_list_with_parens()
        return self.text

    def replace_parens(self):
        return self._ROMAN_NUMERALS_IN_PARENTHESES_RE.sub(r"&✂&\1&⌬&", self.text)

    @staticmethod
    def replace_parens_text(text: str) -> str:
        """Replace roman numeral parentheses without instantiation."""
        return ListItemReplacer._ROMAN_NUMERALS_IN_PARENTHESES_RE.sub(r"&✂&\1&⌬&", text)

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
        self.text = self.add_line_breaks_for_alphabetical_list_with_periods(roman_numeral=False)
        self.text = self.add_line_breaks_for_alphabetical_list_with_parens(roman_numeral=False)
        return self.text

    def format_roman_numeral_lists(self):
        self.text = self.add_line_breaks_for_alphabetical_list_with_periods(roman_numeral=True)
        self.text = self.add_line_breaks_for_alphabetical_list_with_parens(roman_numeral=True)
        return self.text

    def add_line_breaks_for_alphabetical_list_with_periods(self, roman_numeral=False):
        txt = self.iterate_alphabet_array(self.ALPHABETICAL_LIST_WITH_PERIODS, roman_numeral=roman_numeral)
        return txt

    def add_line_breaks_for_alphabetical_list_with_parens(self, roman_numeral=False):
        txt = self.iterate_alphabet_array(self.ALPHABETICAL_LIST_WITH_PARENS, parens=True, roman_numeral=roman_numeral)
        return txt

    def scan_lists(self, regex1, regex2, replacement, strip=False):
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

        def replace_item(match, val=None, strip=False, repl="♨"):
            match = match.group()
            if strip:
                match = str(match).strip()
            chomped_match = match if len(match) == 1 else match.strip(".])")
            if str(each) == chomped_match:
                return "{}{}".format(each, replacement)
            else:
                return str(match)

        self.text = re.sub(regex, partial(replace_item, val=each, strip=strip, repl=replacement), self.text)

    def add_line_breaks_for_numbered_list_with_periods(self):
        if (
            ("♨" in self.text)
            and (not re.search("♨.+(\n|\r).+♨", self.text))
            and (not re.search(r"for\s\d{1,2}♨\s[a-z]", self.text))
        ):
            self.text = apply_rules(
                self.text,
                self.SpaceBetweenListItemsFirstRule,
                self.SpaceBetweenListItemsSecondRule,
            )

    def replace_parens_in_numbered_list(self):
        self.scan_lists(self.NUMBERED_LIST_PARENS_REGEX, self.NUMBERED_LIST_PARENS_REGEX, "☝")

    def add_line_breaks_for_numbered_list_with_parens(self):
        if "☝" in self.text and not re.search("☝.+\n.+☝|☝.+\r.+☝", self.text):
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

        txt = re.sub(
            self.ALPHABETICAL_LIST_LETTERS_AND_PERIODS_REGEX,
            partial(replace_letter_period, val=a),
            self.text,
            flags=re.IGNORECASE,
        )
        return txt

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
        txt = re.sub(
            self.EXTRACT_ALPHABETICAL_LIST_LETTERS_REGEX,
            partial(replace_alphabet_paren, val=a),
            self.text,
            flags=re.IGNORECASE,
        )
        return txt

    def replace_correct_alphabet_list(self, a, parens):
        if parens:
            a = self.replace_alphabet_list_parens(a)
        else:
            a = self.replace_alphabet_list(a)
        return a

    def last_array_item_replacement(self, a, i, alphabet, alphabet_index, list_array, parens):
        if (len(alphabet) == 0) and (len(list_array) == 0) or (list_array[i - 1] not in alphabet) or (a not in alphabet):
            return self.text
        if abs(alphabet_index[list_array[i - 1]] - alphabet_index[a]) != 1:
            return self.text
        result = self.replace_correct_alphabet_list(a, parens)
        return result

    def other_items_replacement(self, a, i, alphabet, alphabet_index, list_array, parens):
        if (
            (len(alphabet) == 0)
            and (len(list_array) == 0)
            or (list_array[i - 1] not in alphabet)
            or (a not in alphabet)
            or (list_array[i + 1] not in alphabet)
        ):
            return self.text
        if (
            alphabet_index[list_array[i + 1]] - alphabet_index[a] != 1
            and abs(alphabet_index[list_array[i - 1]] - alphabet_index[a]) != 1
        ):
            return self.text
        result = self.replace_correct_alphabet_list(a, parens)
        return result

    def iterate_alphabet_array(self, regex, parens=False, roman_numeral=False):
        list_array = re.findall(regex, self.text, re.IGNORECASE)
        list_array = [i.lower() for i in list_array]
        alphabet = self.ROMAN_NUMERALS if roman_numeral else self.LATIN_NUMERALS
        alphabet_index = {value: index for index, value in enumerate(alphabet)}
        list_array = [i for i in list_array if i in alphabet]
        for ind, each in enumerate(list_array):
            if ind == len(list_array) - 1:
                self.text = self.last_array_item_replacement(each, ind, alphabet, alphabet_index, list_array, parens)
            else:
                self.text = self.other_items_replacement(each, ind, alphabet, alphabet_index, list_array, parens)
        return self.text
