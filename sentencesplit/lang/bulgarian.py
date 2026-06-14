# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard, canonical_abbreviations
from sentencesplit.lang.common.whole_span_abbr import whole_span_policy

# Bulgarian (Phase 5): the legacy ``Bulgarian.AbbreviationReplacer`` overrode ONLY
# the regular branch (``replace_period_of_abbr``); both ``PREPOSITIVE_ABBREVIATIONS``
# and ``NUMBER_ABBREVIATIONS`` are EMPTY, so every Bulgarian abbreviation flows
# through the regular branch. The override did two things (bulgarian.py:99-113):
#   1) UNCONDITIONAL trailing-period protection — ``re.sub(r"(?<=\sabbr)\.", "∯")``
#      protects a known abbreviation's period regardless of what follows. Bulgarian
#      keeps a single protected period here ("150 г. Саргон" stays "150 г∯ Саргон"
#      at this stage) and a LATER pass decides the boundary; a capital follower is
#      NOT a boundary cue at the protection step.
#   2) WHOLE-SPAN — for Cyrillic multi-period abbreviations ("б.р", "бел.пр",
#      "к.с") the INTERIOR periods are sentinelized too ("б.р." -> "б∯р∯"), because
#      the ASCII-only ``WithMultiplePeriodsAndEmailRule`` and the post-trailing-period
#      ``MULTI_PERIOD_ABBREVIATION_REGEX`` both miss them, so the boundary regex would
#      otherwise shatter the token ("б.р." -> "б." + "р.").
# This is structurally IDENTICAL to Slovak's regular-branch override (unconditional
# whole-span PROTECT, regular branch only, empty-or-inert prepositive/number), so
# Bulgarian rides the SAME shared ``whole_span_policy()`` factory
# (``lang/common/whole_span_abbr.py``): its ``classify_special`` returns
# ``NOT_HANDLED`` for prepositive/number — never reached here since both sets are
# empty — and PROTECT otherwise, and its ``protect_edit`` does the whole-span
# splice. ``classify_special`` overrides ONLY the regular branch; the (unused)
# PREPOSITIVE/NUMBER branches inherit the base classifier.
#
# Quirk FIXED (BC not required, plan §3, reviewed Golden-Rule-anchored): the legacy
# trailing-period regex interpolated the abbreviation UNescaped into a lookbehind
# (``r"(?<=\s{abbr})\.".format(abbr=abbr)``), so each interior ``.`` of a multi-period
# abbreviation became a regex WILDCARD. When a genuine ``б.р.`` fired the automaton,
# the global ``re.sub`` then ALSO protected an unrelated decoy on the same line whose
# shape matched the wildcard ("…б.р. … бхр. …" -> the spurious "бхр∯"). The V2 path
# classifies + splices only the candidates the reachability gate (word-boundary,
# re.escape-d ``match_re``) actually enumerates, so only the genuine ``б.р.`` is
# protected and the decoy keeps its boundary period — linguistically correct, and
# exercised by no Golden Rule (every Bulgarian Golden Rule + Cyrillic regression case
# is byte-identical between the two paths).
BG_POLICY = whole_span_policy()


class Bulgarian(Common, Standard):
    iso_code = "bg"

    # The shared MULTI_PERIOD_ABBREVIATION_REGEX only matches ASCII letters, so
    # Cyrillic multi-period abbreviations such as "б.р." or "к.с." never have
    # their interior period sentinel-protected and the boundary regex shatters
    # them ("Това е б.р." -> "Това е б." + "р."). Allow Cyrillic (and Latin)
    # letters via a Unicode letter class, mirroring Greek's override. Bulgarian
    # declares abbreviations whose final segment is multi-letter ("б.ред",
    # "бел.пр", "т.нар"), so — unlike Greek — the final segment also allows
    # 1-3 letters instead of a single letter.
    MULTI_PERIOD_ABBREVIATION_REGEX = re.compile(r"(?<!\w)(?:[^\W\d_]{1,3}\.){2,}", re.IGNORECASE | re.UNICODE)

    class Abbreviation(Standard.Abbreviation):
        # Stored in canonical form (lowercased, de-duplicated, sorted); see
        # ``canonical_abbreviations`` and the
        # ``test_abbreviations_are_canonical_form`` lint.
        ABBREVIATIONS = canonical_abbreviations(
            [
                "p.s",
                "акад",
                "ал",
                "б.р",
                "б.ред",
                "бел.а",
                "бел.пр",
                "бр",
                "бул",
                "в",
                "вж",
                "вкл",
                "вм",
                "вр",
                "г",
                "ген",
                "гр",
                "дж",
                "дм",
                "доц",
                "др",
                "ем",
                "заб",
                "зам",
                "инж",
                "к.с",
                "кв",
                "кв.м",
                "кг",
                "км",
                "кор",
                "куб",
                "куб.м",
                "л",
                "лв",
                "м",
                "м.г",
                "мин",
                "млн",
                "млрд",
                "мм",
                "н.с",
                "напр",
                "пл",
                "полк",
                "проф",
                "р",
                "рис",
                "с",
                "св",
                "сек",
                "см",
                "сп",
                "срв",
                "ст",
                "стр",
                "т",
                "т.г",
                "т.е",
                "т.н",
                "т.нар",
                "табл",
                "тел",
                "у",
                "ул",
                "фиг",
                "ха",
                "хил",
                "ч",
                "чл",
                "щ.д",
            ]
        )
        NUMBER_ABBREVIATIONS = []
        PREPOSITIVE_ABBREVIATIONS = []

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2 PeriodClassifier (Phase 5). The legacy ``replace_period_of_abbr``
        # override — an UNCONDITIONAL trailing-period protect plus a WHOLE-SPAN
        # interior-period protect for Cyrillic multi-period abbreviations ("б.р",
        # "бел.пр", "к.с") so the boundary regex does not shatter the token
        # ("б.р." -> "б." + "р.") — is reimplemented as ``BG_POLICY`` (the shared
        # ``whole_span_policy()`` factory in ``lang/common/whole_span_abbr.py``,
        # shared with Slovak's structurally-identical regular-branch override).
        # It overrides ONLY the regular branch; Bulgarian's PREPOSITIVE and NUMBER
        # abbreviation lists are empty, so every abbreviation is regular. The
        # legacy unescaped-lookbehind wildcard quirk is fixed (see BG_POLICY docs).
        ABBR_POLICY = BG_POLICY
