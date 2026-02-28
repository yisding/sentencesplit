# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.cleaner import Cleaner
from sentencesplit.lang.common import Common, Standard
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule, apply_rules


class Japanese(Common, Standard):
    iso_code = "ja"

    class Cleaner(Cleaner):
        def __init__(self, text, lang, doc_type=None):
            super().__init__(text, lang)

        def clean(self):
            self.remove_newline_in_middle_of_word()
            return self.text

        def remove_newline_in_middle_of_word(self):
            NewLineInMiddleOfWordRule = Rule(r"(?<=の)\n(?=\S)", "")
            self.text = apply_rules(self.text, NewLineInMiddleOfWordRule)

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

    class BetweenPunctuation(BetweenPunctuation):
        def __init__(self, text):
            super().__init__(text)

        def replace(self):
            self.sub_punctuation_between_quotes_and_parens()
            return self.text

        def sub_punctuation_between_parens_ja(self):
            BETWEEN_PARENS_JA_REGEX = r"（(?=(?P<tmp>[^（）]+|\\{2}|\\.)*)(?P=tmp)）"
            self.text = re.sub(BETWEEN_PARENS_JA_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_ja(self):
            BETWEEN_QUOTE_JA_REGEX = r"「(?=(?P<tmp>[^「」]+|\\{2}|\\.)*)(?P=tmp)」"
            self.text = re.sub(BETWEEN_QUOTE_JA_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_corner_brackets(self):
            BETWEEN_CORNER_BRACKETS_REGEX = r"(?<=[^\s。．.！!?？])『(?=(?P<tmp>[^』\\]+|\\{2}|\\.)*)(?P=tmp)』"
            self.text = re.sub(BETWEEN_CORNER_BRACKETS_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_black_lenticular_brackets(self):
            BETWEEN_BLACK_LENTICULAR_BRACKETS_REGEX = r"【(?=(?P<tmp>[^】\\]+|\\{2}|\\.)*)(?P=tmp)】"
            self.text = re.sub(BETWEEN_BLACK_LENTICULAR_BRACKETS_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_double_angled_quotation_marks(self):
            BETWEEN_DOUBLE_ANGLE_QUOTATION_MARK_REGEX = r"《(?=(?P<tmp>[^》\\]+|\\{2}|\\.)*)(?P=tmp)》"
            self.text = re.sub(BETWEEN_DOUBLE_ANGLE_QUOTATION_MARK_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_single_angled_quotation_marks(self):
            BETWEEN_SINGLE_ANGLE_QUOTATION_MARK_REGEX = r"〈(?=(?P<tmp>[^〉\\]+|\\{2}|\\.)*)(?P=tmp)〉"
            self.text = re.sub(BETWEEN_SINGLE_ANGLE_QUOTATION_MARK_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_tortoise_shell_brackets(self):
            BETWEEN_TORTOISE_SHELL_BRACKETS_REGEX = r"〔(?=(?P<tmp>[^〕\\]+|\\{2}|\\.)*)(?P=tmp)〕"
            self.text = re.sub(BETWEEN_TORTOISE_SHELL_BRACKETS_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_double_quotes(self):
            BETWEEN_DOUBLE_QUOTES_REGEX = r"(?<=[^\s。．.！!?？])“(?=(?P<tmp>[^”\\]+|\\{2}|\\.)*)(?P=tmp)”"
            self.text = re.sub(BETWEEN_DOUBLE_QUOTES_REGEX, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_and_parens(self):
            self.sub_punctuation_between_parens_ja()
            self.sub_punctuation_between_quotes_ja()
            self.sub_punctuation_between_corner_brackets()
            self.sub_punctuation_between_black_lenticular_brackets()
            self.sub_punctuation_between_double_angled_quotation_marks()
            self.sub_punctuation_between_single_angled_quotation_marks()
            self.sub_punctuation_between_tortoise_shell_brackets()
            self.sub_punctuation_between_double_quotes()
