# -*- coding: utf-8 -*-
import re
import unicodedata

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
        _SR_STANDALONE_FOLLOWERS = {"он", "она", "оно", "они", "это", "эта", "этот", "эти"}
        _SENTENCE_START_OPENERS = frozenset("\"'“”‘’«„([{")

        @classmethod
        def _content_start(cls, text, start=0):
            index = start
            while index < len(text) and (text[index].isspace() or text[index] in cls._SENTENCE_START_OPENERS):
                index += 1
            return index

        @classmethod
        def _starts_with_cyrillic_upper(cls, text, start=0):
            index = cls._content_start(text, start)
            if index >= len(text):
                return False
            char = text[index]
            return char.isupper() and unicodedata.name(char, "").startswith("CYRILLIC")

        @classmethod
        def _next_word_lower(cls, text, start=0):
            index = cls._content_start(text, start)
            word_start = index
            while index < len(text) and text[index].isalpha():
                index += 1
            return text[word_start:index].lower()

        @staticmethod
        def _is_embedded_occurrence(text, abbr_start):
            index = abbr_start - 1
            while index >= 0 and text[index].isspace():
                index -= 1
            if index < 0:
                return False
            return text[index] not in ".!?\r\n"

        @classmethod
        def _sr_continues_compare_phrase(cls, text, start=0):
            index = cls._content_start(text, start)
            sentence_end = len(text)
            for boundary in ".!?":
                found = text.find(boundary, index)
                if found != -1:
                    sentence_end = min(sentence_end, found)
            return re.search(r"\sи\s+[А-ЯЁ]", text[index:sentence_end]) is not None

        def replace_period_of_abbr(self, txt, abbr, escaped=None):
            abbr = abbr.strip()
            escaped = escaped or re.escape(abbr)
            abbr_lower = abbr.lower()

            def replacement(match):
                match_end = match.end()
                if abbr_lower == "ср":
                    if not self._starts_with_cyrillic_upper(txt, match_end):
                        return match.group()[:-1] + "∯"
                    if self._is_embedded_occurrence(txt, match.start(2)):
                        return match.group()[:-1] + "∯"
                    if self._next_word_lower(txt, match_end) in self._SR_STANDALONE_FOLLOWERS:
                        return match.group()
                    if self._sr_continues_compare_phrase(txt, match_end):
                        return match.group()[:-1] + "∯"
                    return match.group()
                if (
                    abbr_lower != "ср"
                    and abbr_lower in self.SENTENCE_FINAL_ABBREVIATIONS
                    and self._starts_with_cyrillic_upper(txt, match_end)
                ):
                    return match.group()
                return match.group()[:-1] + "∯"

            return re.sub(r"(^|\s)({abbr})\.".format(abbr=escaped), replacement, txt, flags=re.IGNORECASE)
