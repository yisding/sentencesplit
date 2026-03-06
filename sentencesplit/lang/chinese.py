# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import CJKBoundaryProfile, CJKProcessor
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule

_CJK_SLANTED_QUOTE_END_RE = re.compile(r"(&ᓰ&|&ᓱ&|&ᓳ&|&ᓴ&|&ᓷ&|&ᓸ&)(?=[”’][^\s])")
_RESTORE_CJK_TERMINAL_PUNCT = {
    "&ᓰ&": "。",
    "&ᓱ&": "．",
    "&ᓳ&": "！",
    "&ᓴ&": "!",
    "&ᓷ&": "?",
    "&ᓸ&": "？",
}


class Chinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "zh"
    CJK_REPORTING_CLAUSE_REGEX = re.compile(
        r"^(?:他|她|他们|她们|我|我们|记者|警方|老师|母亲|父亲|主持人|发言人).{0,6}(?:说|问|答|表示|回应|补充|解释)"
    )

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

        def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
            txt = " " + txt
            if escaped is None:
                escaped = re.escape(abbr.strip())
            txt = re.sub(
                r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())|[\u4e00-\u9fff]))".format(abbr=escaped),
                "∯",
                txt,
            )
            return txt[1:]

    class CjkAbbreviationRules:
        IntraAbbreviationPeriodRule = Rule(r"(?<=[A-Za-z])\.(?=[A-Za-z]\.)", "∯")
        EndAbbreviationBeforeCjkRule = Rule(r"(?<=[A-Za-z]∯[A-Za-z])\.(?=[\u4e00-\u9fff])", "∯")

        All = [IntraAbbreviationPeriodRule, EndAbbreviationBeforeCjkRule]

    class Processor(CJKProcessor):
        pass

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

        def sub_punctuation_between_slanted_quotes(self):
            regex = r"“(?=(?P<tmp>[^”\\]+|\\{2}|\\.)*)(?P=tmp)”"
            self.text = re.sub(regex, replace_punctuation, self.text)
            self.text = _CJK_SLANTED_QUOTE_END_RE.sub(
                lambda match: _RESTORE_CJK_TERMINAL_PUNCT[match.group(1)], self.text
            )

        def sub_punctuation_between_cn_parens(self):
            regex = r"（(?=(?P<tmp>[^）\\]+|\\{2}|\\.)*)(?P=tmp)）"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_and_parens(self):
            self.sub_punctuation_between_double_angled_quotation_marks()
            self.sub_punctuation_between_slanted_quotes()
            self.sub_punctuation_between_l_bracket()
            self.sub_punctuation_between_cn_corner_quotes()
            self.sub_punctuation_between_cn_parens()
