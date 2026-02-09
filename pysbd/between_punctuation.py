# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from functools import partial

from pysbd.punctuation_replacer import replace_punctuation


class BetweenPunctuation:
    """Replace punctuation inside quotes/brackets so it won't split sentences.

    Note: *_REGEX_2 patterns are kept as atomic-grouping workarounds for Python
    (Ruby's atomic groups are not available in the stdlib regex engine).
    """
    # Rubular: http://rubular.com/r/2YFrKWQUYi
    BETWEEN_SINGLE_QUOTES_REGEX = re.compile(r"(?<=\s)'(?:[^']|'[a-zA-Z])*'")

    BETWEEN_SINGLE_QUOTE_SLANTED_REGEX = re.compile(r"(?<=\s)\u2018(?:[^\u2019]|\u2019[a-zA-Z])*\u2019")

    BETWEEN_DOUBLE_QUOTES_REGEX_2 = re.compile(r'"(?=(?P<tmp>[^\"\\]+|\\{2}|\\.)*)(?P=tmp)"')

    BETWEEN_QUOTE_ARROW_REGEX_2 = re.compile(r"\u00ab(?=(?P<tmp>[^\u00bb\\]+|\\{2}|\\.)*)(?P=tmp)\u00bb")

    BETWEEN_QUOTE_SLANTED_REGEX_2 = re.compile(r"\u201c(?=(?P<tmp>[^\u201d\\]+|\\{2}|\\.)*)(?P=tmp)\u201d")

    # Rubular: http://rubular.com/r/WX4AvnZvlX
    BETWEEN_SQUARE_BRACKETS_REGEX_2 = re.compile(r'\[(?=(?P<tmp>[^\]\\]+|\\{2}|\\.)*)(?P=tmp)\]')

    BETWEEN_PARENS_REGEX_2 = re.compile(r"\((?=(?P<tmp>[^\(\)\\]+|\\{2}|\\.)*)(?P=tmp)\)")

    # Rubular: http://rubular.com/r/mXf8cW025o
    WORD_WITH_LEADING_APOSTROPHE = re.compile(r"(?<=\s)'(?:[^']|'[a-zA-Z])*'\S")

    BETWEEN_EM_DASHES_REGEX_2 = re.compile(r"--(?=(?P<tmp>[^--]*))(?P=tmp)--")

    _QUOTE_SPACE_RE = re.compile(r"'\s")

    def __init__(self, text: str) -> None:
        self.text = text

    def replace(self) -> str:
        return self.sub_punctuation_between_quotes_and_parens(self.text)

    def sub_punctuation_between_quotes_and_parens(self, txt: str) -> str:
        txt = self.sub_punctuation_between_single_quotes(txt)
        txt = self.sub_punctuation_between_single_quote_slanted(txt)
        txt = self.sub_punctuation_between_double_quotes(txt)
        txt = self.sub_punctuation_between_square_brackets(txt)
        txt = self.sub_punctuation_between_parens(txt)
        txt = self.sub_punctuation_between_quotes_arrow(txt)
        txt = self.sub_punctuation_between_em_dashes(txt)
        txt = self.sub_punctuation_between_quotes_slanted(txt)
        return txt

    def sub_punctuation_between_parens(self, txt: str) -> str:
        return self.BETWEEN_PARENS_REGEX_2.sub(replace_punctuation, txt)

    def sub_punctuation_between_square_brackets(self, txt: str) -> str:
        return self.BETWEEN_SQUARE_BRACKETS_REGEX_2.sub(replace_punctuation, txt)

    def sub_punctuation_between_single_quotes(self, txt: str) -> str:
        if self.WORD_WITH_LEADING_APOSTROPHE.search(txt) and \
                (not self._QUOTE_SPACE_RE.search(txt)):
            return txt
        return self.BETWEEN_SINGLE_QUOTES_REGEX.sub(
                      partial(replace_punctuation, match_type='single'), txt)

    def sub_punctuation_between_single_quote_slanted(self, txt: str) -> str:
        return self.BETWEEN_SINGLE_QUOTE_SLANTED_REGEX.sub(
                      replace_punctuation, txt)

    def sub_punctuation_between_double_quotes(self, txt: str) -> str:
        return self.BETWEEN_DOUBLE_QUOTES_REGEX_2.sub(replace_punctuation, txt)

    def sub_punctuation_between_quotes_arrow(self, txt: str) -> str:
        return self.BETWEEN_QUOTE_ARROW_REGEX_2.sub(replace_punctuation, txt)

    def sub_punctuation_between_em_dashes(self, txt: str) -> str:
        return self.BETWEEN_EM_DASHES_REGEX_2.sub(replace_punctuation, txt)

    def sub_punctuation_between_quotes_slanted(self, txt: str) -> str:
        return self.BETWEEN_QUOTE_SLANTED_REGEX_2.sub(replace_punctuation, txt)
