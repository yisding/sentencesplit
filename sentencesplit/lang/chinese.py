# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import (
    CJK_REPORTING_CLAUSE_RE,
    CJKBetweenPunctuationMixin,
    CJKBoundaryProfile,
    CJKProcessor,
    make_cjk_abbreviation_rules,
)


class Chinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "zh"
    CJK_REPORTING_CLAUSE_REGEX = CJK_REPORTING_CLAUSE_RE

    class AbbreviationReplacer(AbbreviationReplacer):
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
        All = make_cjk_abbreviation_rules(r"\u4e00-\u9fff")

    class Processor(CJKProcessor):
        pass

    class BetweenPunctuation(CJKBetweenPunctuationMixin, BetweenPunctuation):
        def replace(self) -> str:
            txt = super().replace()
            return self.apply_cjk_punctuation(txt)
