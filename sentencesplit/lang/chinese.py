# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.punctuation_replacer import replace_punctuation


class Chinese(Common, Standard):
    iso_code = "zh"

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

    class BetweenPunctuation(BetweenPunctuation):
        def __init__(self, text):
            super().__init__(text)

        def replace(self):
            self.sub_punctuation_between_quotes_and_parens()
            return self.text

        def sub_punctuation_between_double_angled_quotation_marks(self):
            BETWEEN_DOUBLE_ANGLE_QUOTATION_MARK_REGEX = r"《(?=(?P<tmp>[^》\\]+|\\{2}|\\.)*)(?P=tmp)》"
            self.text = re.sub(BETWEEN_DOUBLE_ANGLE_QUOTATION_MARK_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_single_angled_quotation_marks(self):
            BETWEEN_SINGLE_ANGLE_QUOTATION_MARK_REGEX = r"〈(?=(?P<tmp>[^〉\\]+|\\{2}|\\.)*)(?P=tmp)〉"
            self.text = re.sub(BETWEEN_SINGLE_ANGLE_QUOTATION_MARK_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_l_bracket(self):
            BETWEEN_L_BRACKET_REGEX = r"「(?=(?P<tmp>[^」\\]+|\\{2}|\\.)*)(?P=tmp)」"
            self.text = re.sub(BETWEEN_L_BRACKET_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_double_quotes_zh(self):
            BETWEEN_DOUBLE_QUOTES_ZH_REGEX = r"(?<=[^\s。．.！!?？])“(?=(?P<tmp>[^”\\]+|\\{2}|\\.)*)(?P=tmp)”"
            self.text = re.sub(BETWEEN_DOUBLE_QUOTES_ZH_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_single_quotes_zh(self):
            BETWEEN_SINGLE_QUOTES_ZH_REGEX = r"(?<=[^\s。．.！!?？])‘(?=(?P<tmp>[^’\\]+|\\{2}|\\.)*)(?P=tmp)’"
            self.text = re.sub(BETWEEN_SINGLE_QUOTES_ZH_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_corner_brackets(self):
            BETWEEN_CORNER_BRACKETS_REGEX = r"(?<=[^\s。．.！!?？])『(?=(?P<tmp>[^』\\]+|\\{2}|\\.)*)(?P=tmp)』"
            self.text = re.sub(BETWEEN_CORNER_BRACKETS_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_parens_zh(self):
            BETWEEN_PARENS_ZH_REGEX = r"（(?=(?P<tmp>[^）\\]+|\\{2}|\\.)*)(?P=tmp)）"
            self.text = re.sub(BETWEEN_PARENS_ZH_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_black_lenticular_brackets(self):
            BETWEEN_BLACK_LENTICULAR_BRACKETS_REGEX = r"【(?=(?P<tmp>[^】\\]+|\\{2}|\\.)*)(?P=tmp)】"
            self.text = re.sub(BETWEEN_BLACK_LENTICULAR_BRACKETS_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_and_parens(self):
            self.sub_punctuation_between_double_angled_quotation_marks()
            self.sub_punctuation_between_single_angled_quotation_marks()
            self.sub_punctuation_between_l_bracket()
            self.sub_punctuation_between_double_quotes_zh()
            self.sub_punctuation_between_single_quotes_zh()
            self.sub_punctuation_between_corner_brackets()
            self.sub_punctuation_between_parens_zh()
            self.sub_punctuation_between_black_lenticular_brackets()
