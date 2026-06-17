# -*- coding: utf-8 -*-
import re
import unicodedata

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard, canonical_abbreviations
from sentencesplit.period_classifier import AbbrPolicy, Candidate, Decision, PeriodClassifier

# Russian (Phase 5): the legacy ``Russian.AbbreviationReplacer`` overrode ONLY the
# regular branch (``replace_period_of_abbr``); PREPOSITIVE/NUMBER lists are empty,
# so every Russian abbreviation flows through it. The override protects a known
# abbreviation's period UNCONDITIONALLY (no follower-class lookahead — the legacy
# ``re.sub(r"(^|\s)(abbr)\.")`` matches any period, so "5 куб.м." protects ``куб.``
# even though a Cyrillic ``м`` follows immediately with no space), EXCEPT:
#   - a SENTENCE_FINAL language-tag abbreviation (``рус.`` / ``англ.`` / ``др.`` …)
#     directly before a Cyrillic capital stays a BOUNDARY ("…и др. Она" splits),
#     unless the capital is a foreign-language gloss (``англ. Moscow`` → Latin, no
#     split) handled by the Cyrillic-capital gate; and
#   - ``ср.`` ("cf.") carries its own compare-phrase heuristic (russian.py:159-177).
# ``classify_special`` handles EVERY candidate (never NOT_HANDLED), so the base
# trichotomy never runs. ``realize_per_occurrence`` honors the per-match context
# the legacy callback read (``_sr_continues_compare_phrase`` scans downstream), so
# two ``ср.`` on one line may decide differently.
#
# Offset mapping from the legacy regex groups: legacy ``match.end()`` (just after
# the period) == ``period_idx + 1``; legacy ``match.start(2)`` (the abbreviation
# start) == ``period_idx - len(am_stripped)``.
_RU_CONJUNCTION_CONTINUATION_RE = re.compile(r"\sи\s+[А-ЯЁ]")
_RU_SENTENCE_START_OPENERS = frozenset("\"'“”‘’«„([{")


def _ru_content_start(text: str, start: int) -> int:
    index = start
    n = len(text)
    while index < n and (text[index].isspace() or text[index] in _RU_SENTENCE_START_OPENERS):
        index += 1
    return index


def _ru_starts_with_cyrillic_upper(text: str, start: int) -> bool:
    index = _ru_content_start(text, start)
    if index >= len(text):
        return False
    char = text[index]
    return char.isupper() and unicodedata.name(char, "").startswith("CYRILLIC")


def _ru_is_embedded_occurrence(text: str, abbr_start: int) -> bool:
    index = abbr_start - 1
    while index >= 0 and text[index].isspace():
        index -= 1
    if index < 0:
        return False
    return text[index] not in ".!?\r\n"


def _ru_continues_compare_phrase(text: str, start: int) -> bool:
    index = _ru_content_start(text, start)
    sentence_end = len(text)
    for boundary in ".!?":
        found = text.find(boundary, index)
        if found != -1:
            sentence_end = min(sentence_end, found)
    return _RU_CONJUNCTION_CONTINUATION_RE.search(text[index:sentence_end]) is not None


def _ru_classify_special(pc: "PeriodClassifier", line: str, c: Candidate) -> object:
    """Russian regular-branch override (russian.py:154-179), per occurrence.

    Returns PROTECT/BOUNDARY for every candidate (never NOT_HANDLED), reading the
    candidate's own ORIGINAL context. Mirrors the legacy ``replacement`` callback:
    ``match.group()[:-1] + "∯"`` == PROTECT, ``match.group()`` == BOUNDARY.
    """
    abbr_lower = c.am_lower  # elision-stripped lowercase, computed once on the Candidate
    period_idx = c.period_idx
    match_end = period_idx + 1  # legacy match.end()
    abbr_start = c.abbr_start  # legacy match.start(2); computed once on the Candidate
    if abbr_lower == "ср":
        if not _ru_starts_with_cyrillic_upper(line, match_end):
            return Decision.PROTECT
        if _ru_is_embedded_occurrence(line, abbr_start):
            return Decision.PROTECT
        if _ru_continues_compare_phrase(line, match_end):
            return Decision.BOUNDARY if pc._leans_split else Decision.PROTECT
        if pc._leans_join:
            return Decision.PROTECT
        return Decision.BOUNDARY
    sentence_final = getattr(pc.r, "SENTENCE_FINAL_ABBREVIATIONS", frozenset())
    if abbr_lower in sentence_final and _ru_starts_with_cyrillic_upper(line, match_end):
        return Decision.BOUNDARY
    return Decision.PROTECT


RU_POLICY = AbbrPolicy(
    classify_special=_ru_classify_special,
    realize_per_occurrence=True,
)


class Russian(Common, Standard):
    iso_code = "ru"

    class Abbreviation(Standard.Abbreviation):
        # Stored in canonical form (lowercased, de-duplicated, sorted); see
        # ``canonical_abbreviations`` and the
        # ``test_abbreviations_are_canonical_form`` lint.
        ABBREVIATIONS = canonical_abbreviations(
            [
                "y",
                "y.e",
                "а",
                "авт",
                "адм.-терр",
                "акад",
                "англ",
                "в",
                "вв",
                "вкз",
                "вост.-европ",
                "г",
                "гг",
                "гос",
                "гр",
                "греч",
                "д",
                "деп",
                "дисс",
                "дол",
                "долл",
                "др",
                "ежедн",
                "ж",
                "жен",
                "з",
                "зап",
                "зап.-европ",
                "заруб",
                "и",
                "ин",
                "иностр",
                "инст",
                "исп",
                "итал",
                "к",
                "канд",
                "кв",
                "кг",
                "куб",
                "л",
                "л.h",
                "л.н",
                "лат",
                "м",
                "мин",
                "моск",
                "муж",
                "н",
                "нед",
                "нем",
                "о",
                "п",
                "пгт",
                "пер",
                "польск",
                "пп",
                "пр",
                "просп",
                "проф",
                "р",
                "руб",
                "рус",
                "с",
                "сек",
                "см",
                "спб",
                "ср",
                "стр",
                "т",
                "тел",
                "тов",
                "тт",
                "тыс",
                "у",
                "у.е",
                "ул",
                "ф",
                "фр",
                "ч",
                "чуваш",
            ]
        )
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = []

    class AbbreviationReplacer(AbbreviationReplacer):
        # Route abbreviation protection through the PeriodClassifier. The
        # former override touched ONLY the regular branch (PREPOSITIVE/NUMBER lists
        # are empty), so RU_POLICY.classify_special re-encodes it as data:
        #   - protect a known abbreviation's period unconditionally (no follower
        #     lookahead — "5 куб.м." keeps "куб." even with no space before "м");
        #   - keep a BOUNDARY for a SENTENCE_FINAL language-tag abbreviation before
        #     a Cyrillic capital ("…и др. Она" splits; "англ. Moscow" — Latin gloss
        #     — does not), per the data table below; and
        #   - apply the "ср." compare-phrase heuristic.
        # ``realize_per_occurrence`` preserves the legacy per-match callback's
        # downstream-context reads so two "ср." on one line can decide differently.
        # SENTENCE_FINAL_ABBREVIATIONS stays here as the language data table; the
        # policy reads it off the replacer back-reference.
        ABBR_POLICY = RU_POLICY

        SENTENCE_FINAL_ABBREVIATIONS = {
            "англ",
            "греч",
            "др",
            "исп",
            "итал",
            "лат",
            "нем",
            "польск",
            "рус",
            "ср",
            "фр",
            "чуваш",
        }
