# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.cleaner import Cleaner
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import CJKBoundaryProfile
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule, apply_rules


class Japanese(CJKBoundaryProfile, Common, Standard):
    SENTENCE_BOUNDARY_REGEX = CJKBoundaryProfile.SENTENCE_BOUNDARY_REGEX
    QUOTATION_AT_END_OF_SENTENCE_REGEX = CJKBoundaryProfile.QUOTATION_AT_END_OF_SENTENCE_REGEX
    SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX = CJKBoundaryProfile.SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX
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

        def sub_punctuation_between_quotes_and_parens(self):
            self.sub_punctuation_between_parens_ja()
            self.sub_punctuation_between_quotes_ja()
