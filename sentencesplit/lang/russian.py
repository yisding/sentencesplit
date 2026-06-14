# -*- coding: utf-8 -*-
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard
from sentencesplit.period_classifier import RU_POLICY


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
        # V2: route abbreviation protection through the PeriodClassifier. The
        # legacy override touched ONLY the regular branch (PREPOSITIVE/NUMBER lists
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
        USE_PERIOD_CLASSIFIER = True
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
