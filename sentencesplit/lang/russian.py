# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class Russian(Common, Standard):
    iso_code = "ru"

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = [
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
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = []

    class AbbreviationReplacer(AbbreviationReplacer):
        def replace_period_of_abbr(self, txt, abbr, escaped=None):
            txt = re.sub(r"(?<=\s{abbr})\.".format(abbr=abbr.strip()), "∯", txt)
            txt = re.sub(r"(?<=\A{abbr})\.".format(abbr=abbr.strip()), "∯", txt)
            txt = re.sub(r"(?<=^{abbr})\.".format(abbr=abbr.strip()), "∯", txt)
            return txt
