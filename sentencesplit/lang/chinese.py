# -*- coding: utf-8 -*-
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
from sentencesplit.period_classifier import _cjk_regular_only_policy

# Standalone Chinese (Phase 5): regular-branch-only CJK follower (see
# ``_cjk_regular_only_policy``). Range ``[一-鿿]`` (U+4E00..U+9FFF, BMP only,
# no Ext-A) matches the legacy ``Chinese.AbbreviationReplacer`` override literally;
# this is narrower than ``EN_ES_ZH_POLICY``'s ``[㐀-鿿]`` (which includes Ext-A to
# match its own resplit regexes) and keeps the base ``[a-z]`` follower class
# (en_es_zh widened it to ``[^\W\d_]`` to also segment accented Spanish/English).
ZH_POLICY = _cjk_regular_only_policy("[一-鿿]")  # CJK Unified Ideographs (U+4E00..U+9FFF, BMP only)


class Chinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "zh"
    CJK_REPORTING_CLAUSE_REGEX = CJK_REPORTING_CLAUSE_RE

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2: route the per-line abbreviation-protection step through the
        # PeriodClassifier. ZH_POLICY re-encodes the formerly-overridden
        # ``replace_period_of_abbr`` (the regular branch) as data — the base
        # ``[a-z]`` follower class plus a CJK-ideograph follower
        # ``[一-鿿]`` that protects "U.S.标准" / "etc.标准" without an
        # intervening space — woven into the REGULAR branch only
        # (``cjk_follower_regular_only``), exactly where the legacy override placed
        # it. The PREPOSITIVE / NUMBER branches inherit the base (no-CJK) suffixes,
        # and ``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`` stays False, matching legacy.
        ABBR_POLICY = ZH_POLICY

    class CjkAbbreviationRules:
        All = make_cjk_abbreviation_rules(r"\u4e00-\u9fff")

    class Processor(CJKProcessor):
        pass

    class BetweenPunctuation(CJKBetweenPunctuationMixin, BetweenPunctuation):
        def replace(self) -> str:
            txt = super().replace()
            return self.apply_cjk_punctuation(txt)
