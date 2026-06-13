# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


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
        ABBREVIATIONS = [
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
        NUMBER_ABBREVIATIONS = []
        PREPOSITIVE_ABBREVIATIONS = []

    class AbbreviationReplacer(AbbreviationReplacer):
        def replace_period_of_abbr(self, txt, abbr, escaped=None):
            abbr = abbr.strip()
            txt = re.sub(r"(?<=\s{abbr})\.|(?<=^{abbr})\.".format(abbr=abbr), "∯", txt)
            # For Cyrillic multi-period abbreviations (e.g. "б.р", "к.с",
            # "бел.пр") the trailing period is protected above, but their
            # INTERIOR periods are never sentinel-protected by the shared
            # logic — the ASCII-only WithMultiplePeriodsAndEmailRule and the
            # MULTI_PERIOD_ABBREVIATION_REGEX (after the trailing period is
            # already consumed) both miss them — so the boundary regex would
            # split mid-token ("б.р." -> "б." + "р."). Protect the abbreviation's
            # own interior periods explicitly.
            if "." in abbr:
                escaped_body = re.escape(abbr).replace(r"\.", "∯")
                txt = re.sub(r"(?<=\s){abbr}(?=∯)|(?<=^){abbr}(?=∯)".format(abbr=re.escape(abbr)), escaped_body, txt)
            return txt
