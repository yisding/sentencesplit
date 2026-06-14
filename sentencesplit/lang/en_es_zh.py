# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import (
    _QUOTE_CLOSER_RE,
    CJK_REPORTING_CLAUSE_RE,
    CJKBetweenPunctuationMixin,
    CJKBoundaryProfile,
    make_cjk_abbreviation_rules,
)
from sentencesplit.lang.spanish import Spanish
from sentencesplit.period_classifier import EN_ES_ZH_POLICY
from sentencesplit.processor import (
    _CJK_BANG_RESPLIT_RE,
    _CJK_QUOTE_RESPLIT_RE,
    _LATIN_RESPLIT_RE,
    _MULTI_TERMINATOR_RESPLIT_RE,
    Processor,
    _split_on_uppercase_boundary,
)
from sentencesplit.utils import _next_nonspace_char_starts_sentence

_CJK_FOLLOWING_CHAR_RE = re.compile(r"[\u3400-\u9FFF]")
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


def _split_on_combined_sentence_boundary(text: str, whitespace_re: re.Pattern[str]) -> list[str] | None:
    parts = []
    last = 0
    for match in whitespace_re.finditer(text):
        if not _next_nonspace_char_starts_combined_sentence(text, match.end()):
            continue
        parts.append(text[last : match.start()])
        last = match.end()
    if not parts:
        return None
    parts.append(text[last:])
    return [part for part in parts if part]


class EnglishSpanishChinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "en_es_zh"

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = sorted(set(Standard.Abbreviation.ABBREVIATIONS + Spanish.Abbreviation.ABBREVIATIONS))
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
                latin_parts = _split_on_uppercase_boundary(pps, _LATIN_RESPLIT_RE) or _split_on_combined_sentence_boundary(
                    pps, _MULTI_TERMINATOR_RESPLIT_RE
                )
                for latin_part in latin_parts or [pps]:
                    if not latin_part:
                        continue
                    for part in _CJK_QUOTE_RESPLIT_RE.split(latin_part):
                        resplit.extend(p for p in _CJK_BANG_RESPLIT_RE.split(part) if p)
            return self._merge_combined_quote_continuations(resplit or postprocessed_sents)

        # NOTE: distinct from CJKProcessor._merge_quote_continuations /
        # _should_merge_quote_continuation (lang/common/cjk.py). The combined
        # profile does not set CJK_REPORTING_CLAUSE_REGEX (its profile value is
        # None), so it cannot take the regex from self.profile like the CJK
        # variants do; it hardcodes the module-global CJK_REPORTING_CLAUSE_RE and
        # adds extra Latin-closer / separator handling. The differently-named
        # methods make that divergence explicit rather than a silent overload.
        def _merge_combined_quote_continuations(self, sentences: list[str]) -> list[str]:
            merged: list[str] = []
            idx = 0
            while idx < len(sentences):
                current = sentences[idx]
                if merged and self._should_merge_combined_quote_continuation(merged[-1], current):
                    separator = "" if _CJK_FOLLOWING_CHAR_RE.match(current.lstrip()) else " "
                    merged[-1] = merged[-1] + separator + current.lstrip()
                else:
                    merged.append(current)
                idx += 1
            return merged

        def _should_merge_combined_quote_continuation(self, previous: str, current: str) -> bool:
            previous = previous.rstrip()
            current = current.lstrip()
            if not previous or not current:
                return False
            closer = _QUOTE_CLOSER_RE.search(previous)
            if not closer:
                return False
            # A lowercase Latin continuation is only a quote continuation after a
            # Latin quote closer ("…" then he said). After a CJK closer (」』》】)
            # a lowercase word is a separate sentence (matching standalone zh);
            # only the CJK reporting clause re-merges those.
            is_cjk_closer = any(c in _CJK_QUOTE_CLOSERS for c in closer.group())
            if current[0].islower() and not is_cjk_closer:
                return True
            if CJK_REPORTING_CLAUSE_RE.match(current):
                return True
            return False

        def _is_orphan_content_char(self, c: str) -> bool:
            # Combined profile also treats CJK ideographs as orphan content so a
            # short CJK fragment ending in "." merges like a Latin abbreviation.
            return c.isalnum() or bool(_CJK_FOLLOWING_CHAR_RE.match(c))
