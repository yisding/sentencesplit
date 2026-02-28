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
            rule = Rule(r"(?<=[ぁ-ゖァ-ヺー一-龯々〆〤])\n(?=[ぁ-ゖァ-ヺー一-龯々〆〤])", "")
            self.text = apply_rules(self.text, rule)

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []
        SENTENCE_BOUNDARY_ABBREVIATIONS = []

        def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
            txt = " " + txt
            if escaped is None:
                escaped = re.escape(abbr.strip())
            txt = re.sub(
                r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())|[\u3040-\u30ff\u4e00-\u9fff]))".format(
                    abbr=escaped
                ),
                "∯",
                txt,
            )
            return txt[1:]


    class CjkAbbreviationRules:
        IntraAbbreviationPeriodRule = Rule(r"(?<=[A-Za-z])\.(?=[A-Za-z]\.)", "∯")
        EndAbbreviationBeforeCjkRule = Rule(r"(?<=[A-Za-z]∯[A-Za-z])\.(?=[\u3040-\u30ff\u4e00-\u9fff])", "∯")

        All = [IntraAbbreviationPeriodRule, EndAbbreviationBeforeCjkRule]

    class BetweenPunctuation(BetweenPunctuation):
        def __init__(self, text):
            super().__init__(text)

        def replace(self):
            self.sub_punctuation_between_quotes_and_parens()
            return self.text

        def sub_punctuation_between_parens_ja(self):
            regex = r"（(?=(?P<tmp>[^（）]+|\\{2}|\\.)*)(?P=tmp)）"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_ja(self):
            regex = r"「(?=(?P<tmp>[^「」]+|\\{2}|\\.)*)(?P=tmp)」"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_corner_quotes_ja(self):
            regex = r"『(?=(?P<tmp>[^『』]+|\\{2}|\\.)*)(?P=tmp)』"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_and_parens(self):
            self.sub_punctuation_between_parens_ja()
            self.sub_punctuation_between_quotes_ja()
            self.sub_punctuation_between_corner_quotes_ja()
