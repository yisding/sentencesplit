# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard
from sentencesplit.period_classifier import NOT_HANDLED, AbbrPolicy, Decision
from sentencesplit.processor import Processor
from sentencesplit.utils import Rule, apply_rules

# Kazakh single-token abbreviations are stored WITHOUT a trailing dot, so the
# automaton keys them as "<abbr>." and the classifier enumerates each one's
# trailing period as a candidate. Previously a subset of them ("обл.", "тех.",
# "м." …) was stored WITH a trailing dot, so the automaton keyed those as
# "<abbr>.." and never enumerated them; a whole-text
# ``replace_single_period_abbreviations`` pass compensated by sentinelizing their
# period before a Kazakh-Cyrillic / Latin lowercase follower (a WIDER class than
# the base REGULAR branch's ASCII ``[a-z]``) BEFORE the classifier ran. The
# always-dotless abbreviations ("см", "млн" …) were NOT in that pass — they rode
# the base ASCII-follower REGULAR branch.
#
# To stay byte-for-byte net-neutral while letting the classifier own the work, the
# WIDE Cyrillic-lowercase follower test must apply ONLY to those formerly-dotted
# stems, not to every Kazakh abbreviation (else "См. рис." — matching the
# always-dotless "см" — would newly protect before lowercase " рис", diverging
# from the retired pass). ``_KK_WIDE_FOLLOWER_STEMS`` is the frozen set of those
# stems (lowercase, dot already removed); a candidate whose abbreviation is in it
# is classified against ``_KK_WIDE_REGULAR_RE`` (the base REGULAR shape with the
# Kazakh-Cyrillic + Latin lowercase follower class), and every other candidate
# falls through to the base ASCII-follower dispatch. ``base`` policy's REGULAR
# arms ``\.|:|-|\?|,`` and ``\s(I\s|I'm|I'll|\d|\()`` already match what the pass
# protected, so only the lowercase-letter slot needs widening for this set.
_KK_WIDE_FOLLOWER_STEMS = frozenset(
    {
        "авг",
        "акцион",
        "м",
        "а",
        "р",
        "ғ",
        "апр",
        "аум",
        "биікт",
        "биол",
        "геогр",
        "геол",
        "қ",
        "дек",
        "ж",
        "жж",
        "лат",
        "май",
        "мыс",
        "нояб",
        "обл",
        "окт",
        "оңт",
        "пед",
        "сент",
        "солт",
        "тереңд",
        "тех",
        "төм",
        "т",
        "и",
        "с",
        "ш",
        "февр",
        "хим",
        "экон",
        "янв",
        "акад",
        "мм",
    }
)

# Base REGULAR suffix (period_classifier.PeriodClassifier.RE_REGULAR) with the
# follower class widened from ASCII ``[a-z]`` to Kazakh-Cyrillic + Latin lowercase,
# matching the retired ``replace_period_of_kazakh_abbr`` lookahead exactly.
_KK_WIDE_FOLLOWER_CLASS = "[a-zа-яёәғқңөұүһі]"
_KK_WIDE_REGULAR_SUFFIX = r"\.(?=((\.|\:|-|\?|,)|(\s(" + _KK_WIDE_FOLLOWER_CLASS + r"|I\s|I'm|I'll|\d|\())))"
_KK_WIDE_REGULAR_RE = re.compile(_KK_WIDE_REGULAR_SUFFIX)


def _kk_classify_special(pc, line, c):
    """Apply the WIDE Cyrillic-lowercase follower test to the formerly-dotted stems
    only; defer every other candidate to the base ASCII-follower dispatch."""
    if pc._elision_strip(c.am_stripped).lower() not in _KK_WIDE_FOLLOWER_STEMS:
        return NOT_HANDLED
    return Decision.PROTECT if _KK_WIDE_REGULAR_RE.match(line, c.period_idx) else Decision.BOUNDARY


def _kk_realize_suffix(pc, c, line, d):
    """Global-realization suffix for the WIDE-follower PROTECT decisions."""
    return _KK_WIDE_REGULAR_SUFFIX


KK_POLICY = AbbrPolicy(classify_special=_kk_classify_special, realize_suffix=_kk_realize_suffix)


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
            "авг",
            "aбб",
            "аек",
            "ак",
            "ақ",
            "акцион",
            "акср",
            "ақш",
            "англ",
            "аөсшк",
            "апр",
            "а",
            "р",
            "ғ",
            "аум",
            "ацат",
            "әч",
            "т. б.",
            "б. з. б.",
            "б. з. д.",
            "биікт",
            "б. т.",
            "биол",
            "биохим",
            "бө",
            "б. э. д.",
            "бта",
            "бұұ",
            "вич",
            "всоонл",
            "геогр",
            "геол",
            "гленкор",
            "гэс",
            "қк",
            "км",
            "г",
            "млн",
            "млрд",
            "т",
            "ғ. с.",
            "қ",
            "дек",
            "днқ",
            "дсұ",
            "еақк",
            "еқыұ",
            "ембімұнайгаз",
            "ео",
            "еуразэқ",
            "еуроодақ",
            "еұу",
            "ж",
            "жж",
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
            "лат",
            "м²",
            "м³",
            "магатэ",
            "май",
            "максам",
            "мб",
            "мвт",
            "мемл",
            "м",
            "мсоп",
            "мтк",
            "мыс",
            "наса",
            "нато",
            "нквд",
            "нояб",
            "обл",
            "огпу",
            "окт",
            "оңт",
            "опек",
            "оеб",
            "өзенмұнайгаз",
            "өф",
            "пәк",
            "пед",
            "ркфср",
            "рнқ",
            "рсфср",
            "рф",
            "свс",
            "сву",
            "сду",
            "сес",
            "сент",
            "см",
            "снпс",
            "солт",
            "сооно",
            "ссро",
            "сср",
            "ссср",
            "ссс",
            "сэс",
            "дк",
            "тв",
            "тереңд",
            "тех",
            "тжқ",
            "тмд",
            "төм",
            "трлн",
            "тр",
            "и",
            "с",
            "ш",
            "т. с. с.",
            "тэц",
            "уаз",
            "уефа",
            "ұқк",
            "ұқшұ",
            "февр",
            "фққ",
            "фсб",
            "хим",
            "хқко",
            "шұар",
            "шыұ",
            "экон",
            "экспо",
            "цтп",
            "цас",
            "янв",
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
            "акад",
            "мм",
        ]
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = []

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2: route the per-line abbreviation-protection step through the
        # PeriodClassifier. Kazakh overrides ZERO scan methods
        # (``scan_for_replacements`` / ``replace_period_of_abbr`` are inherited;
        # ``PREPOSITIVE_ABBREVIATIONS`` and ``NUMBER_ABBREVIATIONS`` are empty;
        # ``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`` stays False), so its per-line
        # step is the BASE REGULAR branch with one widened arm: ``KK_POLICY``
        # swaps the ASCII ``[a-z]`` follower class for the Kazakh-Cyrillic + Latin
        # lowercase class ``[a-zа-яёәғқңөұүһі]`` so "обл. қала" does NOT split.
        #
        # Previously the single-token Kazakh abbreviations ("обл.", "тех.", "м." …)
        # were stored WITH a trailing dot, so the automaton keyed them as
        # "<abbr>.." and never enumerated them; a whole-text
        # ``replace_single_period_abbreviations`` pass compensated by sentinelizing
        # their period before a lowercase follower BEFORE the classifier ran. The
        # data now stores them dotless (keyed "<abbr>."), the classifier enumerates
        # them directly, and ``KK_POLICY``'s follower class reproduces exactly what
        # the retired pass protected — so that whole-text pass (and its
        # ``_LOWERCASE_CONTINUATION_CHARS`` helper) is gone.
        #
        # Two Kazakh-specific whole-text passes remain in ``replace()`` because they
        # cannot collapse into the per-line classifier:
        #   1. (pre) Cyrillic single-uppercase-letter initials -> ``∯`` (run on the
        #      whole text before line-splitting; ``^`` anchors the document start);
        #   2. (post) ``protect_multi_period_abbreviations_before_parenthesis`` —
        #      runs AFTER ``replace_multi_period_abbreviations`` (it matches interior
        #      ``∯`` that pass produced via ``[.∯]``), so it must stay a whole-text
        #      post-pass, not a per-line classifier stage.
        ABBR_POLICY = KK_POLICY

        def replace(self) -> str:
            SingleUpperCaseCyrillicLetterAtStartOfLineRule = Rule(r"(?<=^[А-ЯЁ])\.(?=\s)", "∯")
            SingleUpperCaseCyrillicLetterRule = Rule(r"(?<=\s[А-ЯЁ])\.(?=\s)", "∯")
            self.text = apply_rules(
                self.text,
                SingleUpperCaseCyrillicLetterAtStartOfLineRule,
                SingleUpperCaseCyrillicLetterRule,
            )
            self.text = super().replace()
            self.protect_multi_period_abbreviations_before_parenthesis()
            return self.text

        def protect_multi_period_abbreviations_before_parenthesis(self) -> None:
            for abbreviation in self.lang.Abbreviation.ABBREVIATIONS:
                abbreviation = abbreviation.strip()
                if not (abbreviation.endswith(".") and abbreviation.count(".") > 1):
                    continue
                body = re.escape(abbreviation[:-1]).replace(r"\.", r"[.∯]").replace(r"\ ", r"\s*")
                self.text = re.sub(rf"(?i:({body}))\.(?=\s*[(])", r"\1∯", self.text)
