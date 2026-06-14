# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard
from sentencesplit.period_classifier import BASE_POLICY
from sentencesplit.processor import Processor
from sentencesplit.utils import Rule, apply_rules


class Kazakh(Common, Standard):
    iso_code = "kk"

    # Handling Cyrillic characters in re module
    # https://stackoverflow.com/a/10982308/5462100
    MULTI_PERIOD_ABBREVIATION_REGEX = re.compile(
        r"\b[\u0400-\u0500]+(?:\.\s?[\u0400-\u0500])+[.]|\b[a-z](?:\.[a-z])+[.]", re.IGNORECASE
    )

    class Processor(Processor):
        def between_punctuation(self, txt):
            txt = self.between_punctuation_processor(txt).replace()
            # Rubular: http://rubular.com/r/WRWy56Z5zp
            QuestionMarkFollowedByDashLowercaseRule = Rule(r"(?<=)\?(?=\s*[-—]\s*)", "&ᓷ&")
            # Rubular: http://rubular.com/r/lixxP7puSa
            ExclamationMarkFollowedByDashLowercaseRule = Rule(r"(?<=)!(?=\s*[-—]\s*)", "&ᓴ&")

            txt = apply_rules(
                txt,
                QuestionMarkFollowedByDashLowercaseRule,
                ExclamationMarkFollowedByDashLowercaseRule,
            )
            return txt

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = [
            "afp",
            "anp",
            "atp",
            "bae",
            "bg",
            "bp",
            "cam",
            "cctv",
            "cd",
            "cez",
            "cgi",
            "cnpc",
            "farc",
            "fbi",
            "eiti",
            "epo",
            "er",
            "gp",
            "gps",
            "has",
            "hiv",
            "hrh",
            "http",
            "icu",
            "idf",
            "imd",
            "ime",
            "ip",
            "iso",
            "kaz",
            "kpo",
            "kpa",
            "kz",
            "mri",
            "nasa",
            "nba",
            "nbc",
            "nds",
            "ohl",
            "omlt",
            "ppm",
            "pda",
            "pkk",
            "psm",
            "psp",
            "raf",
            "rss",
            "rtl",
            "sas",
            "sme",
            "sms",
            "tnt",
            "udf",
            "uefa",
            "usb",
            "utc",
            "x",
            "zdf",
            "әқбк",
            "аақ",
            "авг.",
            "aбб",
            "аек",
            "ак",
            "ақ",
            "акцион.",
            "акср",
            "ақш",
            "англ",
            "аөсшк",
            "апр",
            "м.",
            "а.",
            "р.",
            "ғ.",
            "апр.",
            "аум.",
            "ацат",
            "әч",
            "т. б.",
            "б. з. б.",
            "б. з. д.",
            "биікт.",
            "б. т.",
            "биол.",
            "биохим",
            "бө",
            "б. э. д.",
            "бта",
            "бұұ",
            "вич",
            "всоонл",
            "геогр.",
            "геол.",
            "гленкор",
            "гэс",
            "қк",
            "км",
            "г",
            "млн",
            "млрд",
            "т",
            "ғ. с.",
            "қ.",
            "дек.",
            "днқ",
            "дсұ",
            "еақк",
            "еқыұ",
            "ембімұнайгаз",
            "ео",
            "еуразэқ",
            "еуроодақ",
            "еұу",
            "ж.",
            "жж.",
            "жоо",
            "жіө",
            "жсдп",
            "жшс",
            "іім",
            "инта",
            "исаф",
            "камаз",
            "кгб",
            "кеу",
            "кг",
            "км²",
            "км³",
            "кимеп",
            "кср",
            "ксро",
            "кокп",
            "кхдр",
            "қазатомпром",
            "қазкср",
            "қазұу",
            "қазмұнайгаз",
            "қазпошта",
            "қазтаг",
            "қкп",
            "қмдб",
            "қр",
            "қхр",
            "лат.",
            "м²",
            "м³",
            "магатэ",
            "май.",
            "максам",
            "мб",
            "мвт",
            "мемл",
            "м",
            "мсоп",
            "мтк",
            "мыс.",
            "наса",
            "нато",
            "нквд",
            "нояб.",
            "обл.",
            "огпу",
            "окт.",
            "оңт.",
            "опек",
            "оеб",
            "өзенмұнайгаз",
            "өф",
            "пәк",
            "пед.",
            "ркфср",
            "рнқ",
            "рсфср",
            "рф",
            "свс",
            "сву",
            "сду",
            "сес",
            "сент.",
            "см",
            "снпс",
            "солт.",
            "сооно",
            "ссро",
            "сср",
            "ссср",
            "ссс",
            "сэс",
            "дк",
            "тв",
            "тереңд.",
            "тех.",
            "тжқ",
            "тмд",
            "төм.",
            "трлн",
            "тр",
            "т.",
            "и.",
            "с.",
            "ш.",
            "т. с. с.",
            "тэц",
            "уаз",
            "уефа",
            "ұқк",
            "ұқшұ",
            "февр.",
            "фққ",
            "фсб",
            "хим.",
            "хқко",
            "шұар",
            "шыұ",
            "экон.",
            "экспо",
            "цтп",
            "цас",
            "янв.",
            "dvd",
            "жкт",
            "ққс",
            "юнеско",
            "ббс",
            "mgm",
            "жск",
            "зоо",
            "бсн",
            "өұқ",
            "оар",
            "боак",
            "эөкк",
            "хтқо",
            "әөк",
            "жэк",
            "хдо",
            "спбму",
            "аф",
            "сбд",
            "амт",
            "гсдп",
            "гсбп",
            "эыдұ",
            "нұсжп",
            "жтсх",
            "хдп",
            "эқк",
            "фкққ",
            "пиқ",
            "өгк",
            "мбф",
            "маж",
            "кота",
            "тж",
            "ук",
            "обб",
            "сбл",
            "жхл",
            "кмс",
            "бмтрк",
            "жққ",
            "бхооо",
            "мқо",
            "ржмб",
            "гулаг",
            "жко",
            "еэы",
            "еаэы",
            "рфкп",
            "рлдп",
            "хвқ",
            "мр",
            "мт",
            "кту",
            "ртж",
            "тим",
            "мемдум",
            "т.с.с",
            "с.ш.",
            "ш.б.",
            "б.б.",
            "руб",
            "мин",
            "акад.",
            "мм",
            "мм.",
        ]
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = []

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2: route the per-line abbreviation-protection step through the
        # PeriodClassifier. Kazakh overrode ZERO scan methods
        # (``scan_for_replacements`` / ``replace_period_of_abbr`` are inherited;
        # ``PREPOSITIVE_ABBREVIATIONS`` and ``NUMBER_ABBREVIATIONS`` are empty;
        # ``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`` stays False), so its per-line
        # step is the BASE REGULAR branch verbatim — ``BASE_POLICY`` reproduces it
        # byte-for-byte (verified by the differential oracle over every Kazakh
        # Golden Rule + regression case).
        #
        # All Kazakh-specific behavior lives in the THREE whole-text passes that
        # wrap the base ``replace()`` and CANNOT collapse into the per-line
        # classifier:
        #   1. (pre) Cyrillic single-uppercase-letter initials -> ``∯`` (run on
        #      the whole text before line-splitting; ``^`` anchors the document
        #      start);
        #   2. (pre) ``replace_single_period_abbreviations`` — the dotted Kazakh
        #      abbreviations ("обл.", "тех.", "м." …) are stored WITH a trailing
        #      dot, so the automaton keys them as "<abbr>.." and the base step
        #      never enumerates "обл." as a candidate. This pass protects their
        #      period before a Kazakh-Cyrillic-lowercase / Latin-lowercase / "I" /
        #      digit / "(" continuation (``_LOWERCASE_CONTINUATION_CHARS``), which
        #      the base ``[a-z]`` follower class would miss; it sentinelizes the
        #      period BEFORE the classifier runs, so those periods are no longer
        #      "." candidates by the time the per-line step sees them;
        #   3. (post) ``protect_multi_period_abbreviations_before_parenthesis`` —
        #      runs AFTER ``replace_multi_period_abbreviations`` (it matches interior
        #      ``∯`` that pass produced via ``[.∯]``), so it must stay a whole-text
        #      post-pass, not a per-line classifier stage.
        # This mirrors the Deutsch V2 conversion: keep the reordered ``replace()``
        # for whole-text staging; only the protection step delegates to the
        # classifier.
        USE_PERIOD_CLASSIFIER = True
        ABBR_POLICY = BASE_POLICY

        _LOWERCASE_CONTINUATION_CHARS = "a-zа-яёәғқңөұүһі"

        def replace(self) -> str:
            SingleUpperCaseCyrillicLetterAtStartOfLineRule = Rule(r"(?<=^[А-ЯЁ])\.(?=\s)", "∯")
            SingleUpperCaseCyrillicLetterRule = Rule(r"(?<=\s[А-ЯЁ])\.(?=\s)", "∯")
            self.text = apply_rules(
                self.text,
                SingleUpperCaseCyrillicLetterAtStartOfLineRule,
                SingleUpperCaseCyrillicLetterRule,
            )
            self.replace_single_period_abbreviations()
            self.text = super().replace()
            self.protect_multi_period_abbreviations_before_parenthesis()
            return self.text

        def replace_single_period_abbreviations(self) -> None:
            for abbreviation in self.lang.Abbreviation.ABBREVIATIONS:
                abbreviation = abbreviation.strip()
                if abbreviation.endswith(".") and abbreviation.count(".") == 1:
                    abbreviation_without_period = abbreviation[:-1]
                    self.text = self.replace_period_of_kazakh_abbr(abbreviation_without_period)

        def replace_period_of_kazakh_abbr(self, abbreviation: str) -> str:
            text = " " + self.text
            escaped = rf"(?i:{re.escape(abbreviation)})"
            boundary = self._data.boundary_class
            lowercase = self._LOWERCASE_CONTINUATION_CHARS
            text = re.sub(
                rf"(?<=[{boundary}]{escaped})\.(?=(?:\.|:|-|\?|,|\s(?:[{lowercase}]|I\s|I'm|I'll|\d|[(])))",
                "∯",
                text,
            )
            return text[1:]

        def protect_multi_period_abbreviations_before_parenthesis(self) -> None:
            for abbreviation in self.lang.Abbreviation.ABBREVIATIONS:
                abbreviation = abbreviation.strip()
                if not (abbreviation.endswith(".") and abbreviation.count(".") > 1):
                    continue
                body = re.escape(abbreviation[:-1]).replace(r"\.", r"[.∯]").replace(r"\ ", r"\s*")
                self.text = re.sub(rf"(?i:({body}))\.(?=\s*[(])", r"\1∯", self.text)
