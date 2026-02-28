# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule


class Chinese(Common, Standard):
    iso_code = "zh"

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []
        SENTENCE_BOUNDARY_ABBREVIATIONS = []

        def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
            txt = " " + txt
            if escaped is None:
                escaped = re.escape(abbr.strip())
            txt = re.sub(
                r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())|[\u4e00-\u9fff]))".format(
                    abbr=escaped
                ),
                "∯",
                txt,
            )
            return txt[1:]


    class CjkAbbreviationRules:
        IntraAbbreviationPeriodRule = Rule(r"(?<=[A-Za-z])\.(?=[A-Za-z]\.)", "∯")
        EndAbbreviationBeforeCjkRule = Rule(r"(?<=[A-Za-z]∯[A-Za-z])\.(?=[\u4e00-\u9fff])", "∯")

        All = [IntraAbbreviationPeriodRule, EndAbbreviationBeforeCjkRule]

    class BetweenPunctuation(BetweenPunctuation):
        def __init__(self, text):
            super().__init__(text)

        def replace(self):
            self.sub_punctuation_between_quotes_and_parens()
            return self.text

        def sub_punctuation_between_double_angled_quotation_marks(self):
            regex = r"《(?=(?P<tmp>[^》\\]+|\\{2}|\\.)*)(?P=tmp)》"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_l_bracket(self):
            regex = r"「(?=(?P<tmp>[^」\\]+|\\{2}|\\.)*)(?P=tmp)」"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_cn_corner_quotes(self):
            regex = r"『(?=(?P<tmp>[^』\\]+|\\{2}|\\.)*)(?P=tmp)』"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_cn_parens(self):
            regex = r"（(?=(?P<tmp>[^）\\]+|\\{2}|\\.)*)(?P=tmp)）"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_and_parens(self):
            self.sub_punctuation_between_double_angled_quotation_marks()
            self.sub_punctuation_between_l_bracket()
            self.sub_punctuation_between_cn_corner_quotes()
            self.sub_punctuation_between_cn_parens()
