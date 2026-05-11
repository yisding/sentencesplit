# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import (
    _CJK_REPORTING_CLAUSE_BOUNDARY,
    CJKBetweenPunctuationMixin,
    CJKBoundaryProfile,
    CJKProcessor,
)
from sentencesplit.utils import Rule


class Chinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "zh"
    CJK_REPORTING_CLAUSE_REGEX = re.compile(
        rf"^(?:他|她|他们|她们|我|我们|记者|警方|老师|母亲|父亲|主持人|发言人).{{0,6}}(?:说|问|答|表示|回应|补充|解释){_CJK_REPORTING_CLAUSE_BOUNDARY}"
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

    class BetweenPunctuation(CJKBetweenPunctuationMixin, BetweenPunctuation):
        def replace(self) -> str:
            txt = super().replace()
            return self.apply_cjk_punctuation(txt)
