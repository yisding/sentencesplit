# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.boundary_resplit import (
    _CJK_BANG_RESPLIT_RE,
    _CJK_QUOTE_RESPLIT_RE,
    _LATIN_RESPLIT_RE,
    _MULTI_TERMINATOR_RESPLIT_RE,
    _split_on_uppercase_boundary,
    merge_quote_continuations,
)
from sentencesplit.lang.common import Common, Standard, canonical_abbreviations
from sentencesplit.lang.common.cjk import (
    _QUOTE_CLOSER_RE,
    CJK_REPORTING_CLAUSE_RE,
    CJKBetweenPunctuationMixin,
    CJKBoundaryProfile,
    make_cjk_abbreviation_rules,
)
from sentencesplit.lang.spanish import Spanish
from sentencesplit.period_classifier import AbbrPolicy
from sentencesplit.processor import Processor
from sentencesplit.utils import _next_nonspace_char_starts_sentence

_CJK_FOLLOWING_CHAR_RE = re.compile(r"[\u3400-\u9FFF]")

# Combined en/es/zh profile (Phase 5): any-Unicode-letter follower class, a CJK
# ideograph follower that protects even without an intervening space, and the
# ASCII-only restriction on the capital-follower-is-boundary heuristic. This
# reproduces the legacy ``EnglishSpanishChinese.AbbreviationReplacer``
# (``replace_period_of_abbr`` + ``scan_for_replacements`` overrides) as data.
EN_ES_ZH_POLICY = AbbrPolicy(
    follower_class=r"[^\W\d_]",
    cjk_follower_class="[\u3400-\u9fff]",  # CJK unified ideographs (Ext-A start .. BMP end)
    ascii_only_upper_heuristic=True,
)

_SENTENCE_START_WRAPPERS = frozenset("\"'“‘«‹([{「『【（《")
_SPANISH_INVERTED_SENTENCE_OPENERS = frozenset("¿¡")
# Closers that mark an embedded CJK quote/title; a lowercase Latin continuation
# after one of these is not a quote continuation (unlike a Latin quote closer).
_CJK_QUOTE_CLOSERS = frozenset("\u300d\u300f\u300b\u3011")


def _next_nonspace_char_starts_combined_sentence(text: str, start: int = 0) -> bool:
    for index in range(start, len(text)):
        char = text[index]
        if char.isspace() or char in _SENTENCE_START_WRAPPERS:
            continue
        return (
            _next_nonspace_char_starts_sentence(text, index)
            or char in _SPANISH_INVERTED_SENTENCE_OPENERS
            or _CJK_FOLLOWING_CHAR_RE.match(char) is not None
        )
    return False


class EnglishSpanishChinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "en_es_zh"

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = canonical_abbreviations(Standard.Abbreviation.ABBREVIATIONS, Spanish.Abbreviation.ABBREVIATIONS)
        PREPOSITIVE_ABBREVIATIONS = sorted(
            set(Standard.Abbreviation.PREPOSITIVE_ABBREVIATIONS + Spanish.Abbreviation.PREPOSITIVE_ABBREVIATIONS)
        )
        NUMBER_ABBREVIATIONS = sorted(
            set(Standard.Abbreviation.NUMBER_ABBREVIATIONS + Spanish.Abbreviation.NUMBER_ABBREVIATIONS)
        )

    class AbbreviationReplacer(AbbreviationReplacer):
        CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE = True
        PROTECT_ALLCAPS_IMPRINT_SUFFIXES = True
        RESTORE_STANDALONE_I_BOUNDARIES = True

        # V2: route the per-line abbreviation-protection step through the
        # PeriodClassifier. EN_ES_ZH_POLICY re-encodes the two formerly-
        # overridden methods (replace_period_of_abbr + scan_for_replacements)
        # as data:
        #   - follower_class [^\W\d_]: any Unicode letter may follow an abbr.
        #   - cjk_follower_class [\u3400-\u9FFF]: a CJK ideograph immediately
        #     after the period protects WITHOUT an intervening space
        #     ("U.S.标准", "etc.标准"); with a space, [^\W\d_] already covers it.
        #   - ascii_only_upper_heuristic: the capital-follower-is-boundary cue
        #     fires only for an ASCII capital. A non-ASCII capital
        #     ("Sr. Élena", "dept. Élena") is NOT a cue, so it falls through to
        #     the regular / prepositive branches whose [^\W\d_] follower class
        #     protects it.
        # The legacy `_HEURISTIC_ABBREVIATIONS` gate was a no-op: that set
        # equals the full abbreviation set and every candidate's abbr is
        # necessarily in it, so the membership test was always True. It is
        # therefore not modeled in the policy.
        ABBR_POLICY = EN_ES_ZH_POLICY

    class CjkAbbreviationRules:
        All = make_cjk_abbreviation_rules(r"\u3400-\u9FFF")

    class BetweenPunctuation(CJKBetweenPunctuationMixin, BetweenPunctuation):
        def replace(self) -> str:
            txt = super().replace()
            return self.apply_cjk_punctuation(txt)

    class Processor(Processor):
        def _resplit_segments(self, postprocessed_sents: list[str]) -> list[str]:
            resplit = []
            for pps in postprocessed_sents:
                latin_parts = _split_on_uppercase_boundary(pps, _LATIN_RESPLIT_RE) or _split_on_uppercase_boundary(
                    pps, _MULTI_TERMINATOR_RESPLIT_RE, starts_sentence=_next_nonspace_char_starts_combined_sentence
                )
                for latin_part in latin_parts or [pps]:
                    if not latin_part:
                        continue
                    for part in _CJK_QUOTE_RESPLIT_RE.split(latin_part):
                        resplit.extend(p for p in _CJK_BANG_RESPLIT_RE.split(part) if p)
            # Unlike the CJK variants (lang/common/cjk.py), the combined profile
            # does not set CJK_REPORTING_CLAUSE_REGEX (its profile value is None),
            # so it passes the module-global CJK_REPORTING_CLAUSE_RE explicitly and
            # enables the extra Latin-closer (latin_lowercase_continuation) and
            # CJK-ideograph-separator handling that the shared merger supports.
            return merge_quote_continuations(
                resplit or postprocessed_sents,
                closer_re=_QUOTE_CLOSER_RE,
                reporting_clause_re=CJK_REPORTING_CLAUSE_RE,
                latin_lowercase_continuation=True,
                cjk_closers=_CJK_QUOTE_CLOSERS,
                cjk_follower_re=_CJK_FOLLOWING_CHAR_RE,
            )

        def _is_orphan_content_char(self, c: str) -> bool:
            # Combined profile also treats CJK ideographs as orphan content so a
            # short CJK fragment ending in "." merges like a Latin abbreviation.
            return c.isalnum() or bool(_CJK_FOLLOWING_CHAR_RE.match(c))
