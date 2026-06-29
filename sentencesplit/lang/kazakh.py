# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import DEFAULT_POST_STAGES, AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard, canonical_abbreviations
from sentencesplit.period_classifier import AbbrPolicy
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
# stems (lowercase, dot already removed). It is wired into KK_POLICY as a
# ``regular_follower_overrides`` FIELD (S10): the base dispatch's REGULAR branch
# uses the widened follower class for these stems and the ASCII ``[a-z]`` class for
# every other stem, so Kazakh rides the base dispatch with NO bespoke
# ``classify_special``/``realize_suffix`` pair. The base policy's REGULAR arms
# ``\.|:|-|\?|,`` and ``\s(I\s|I'm|I'll|\d|\()`` already match what the retired
# pass protected, so only the lowercase-letter slot needs widening for this set.
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

# Follower class for the WIDE stems: the base REGULAR suffix's ASCII ``[a-z]``
# slot widened to Kazakh-Cyrillic + Latin lowercase, matching the retired
# ``replace_period_of_kazakh_abbr`` lookahead exactly. The classifier builds the
# full REGULAR regex (lowercase slot replaced by this class) once from the
# ``regular_follower_overrides`` field below.
_KK_WIDE_FOLLOWER_CLASS = "[a-zа-яёәғқңөұүһі]"


def _kk_protect_before_parenthesis(r) -> None:
    """Kazakh post-stage: protect a multi-period abbreviation's final period when it
    immediately precedes an opening parenthesis. Runs AFTER the default pipeline
    (notably ``replace_multi_period_abbreviations``), matching the interior ``∯`` that
    pass produced via ``[.∯]`` — so it stays a whole-text post-pass, appended to the
    default post-stages rather than a per-line classifier stage (see S10)."""
    r.protect_multi_period_abbreviations_before_parenthesis()


# Kazakh rides the base REGULAR dispatch with NO bespoke classify_special /
# realize_suffix pair (S10): the ``regular_follower_overrides`` field widens the
# REGULAR follower class to Kazakh-Cyrillic + Latin lowercase for the 39
# formerly-dotted stems only ("обл. қала" joins; "См. рис." still splits), and the
# default downstream pipeline gets one extra post-pass (the paren protection
# above), owned by the policy now (S1) so ``replace()`` only customizes the Kazakh
# upstream Cyrillic-initial rules and runs the driver.
KK_POLICY = AbbrPolicy(
    regular_follower_overrides=(_KK_WIDE_FOLLOWER_STEMS, _KK_WIDE_FOLLOWER_CLASS),
    # The widened Kazakh follower decision is context-sensitive even when
    # ``follower_char`` is empty: "обл.x" is a boundary, while "обл.:" protects.
    # Anchor each occurrence so an earlier empty-follower boundary cannot suppress
    # a later protectable occurrence of the same abbreviation on the same line.
    realize_per_occurrence=True,
    post_stages=DEFAULT_POST_STAGES + (_kk_protect_before_parenthesis,),
)


class Kazakh(Common, Standard):
    iso_code = "kk"

    # Handling Cyrillic characters in re module
    # https://stackoverflow.com/a/10982308/5462100
    #
    # Sentinel-aware ``[.\u222f]`` separators/terminator, mirroring the base
    # ``Common.MULTI_PERIOD_ABBREVIATION_REGEX`` and this language's own
    # ``protect_multi_period_abbreviations_before_parenthesis``: when a declared
    # dotless multi-period abbreviation ("\u0442.\u0441.\u0441") is followed by a REGULAR-branch
    # follower, the classifier has already protected its trailing period to "\u222f"
    # ("\u0442.\u0441.\u0441\u222f") before this pass runs, so the token must still be re-found to
    # protect its interior dots. The ASCII-only "." form could only re-find it via a
    # lucky shorter-prefix match; matching "\u222f" makes the whole token match directly.
    MULTI_PERIOD_ABBREVIATION_REGEX = re.compile(
        r"\b[\u0400-\u0500]+(?:[.\u222f]\s?[\u0400-\u0500])+[.\u222f]|\b[a-z](?:[.\u222f][a-z])+[.\u222f]", re.IGNORECASE
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
        # Stored in canonical form (lowercased, de-duplicated, sorted); see
        # ``canonical_abbreviations`` and the
        # ``test_abbreviations_are_canonical_form`` lint.
        ABBREVIATIONS = canonical_abbreviations(
            [
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
        )
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = []

    class AbbreviationReplacer(AbbreviationReplacer):
        # Route the per-line abbreviation-protection step through the
        # PeriodClassifier. Kazakh overrides ZERO scan methods
        # (``scan_for_replacements`` / ``replace_period_of_abbr`` are inherited;
        # ``PREPOSITIVE_ABBREVIATIONS`` and ``NUMBER_ABBREVIATIONS`` are empty;
        # ``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`` stays False), so its per-line
        # step is the BASE REGULAR dispatch with one widened arm: ``KK_POLICY``'s
        # ``regular_follower_overrides`` field widens the ASCII ``[a-z]`` follower
        # class to the Kazakh-Cyrillic + Latin lowercase class
        # ``[a-zа-яёәғқңөұүһі]`` for the 39 ``_KK_WIDE_FOLLOWER_STEMS`` only, so
        # "обл. қала" does NOT split while "См. рис." (always-dotless "см") still
        # does (S10).
        #
        # Previously the single-token Kazakh abbreviations ("обл.", "тех.", "м." …)
        # were stored WITH a trailing dot, so the automaton keyed them as
        # "<abbr>.." and never enumerated them; a whole-text
        # ``replace_single_period_abbreviations`` pass compensated by sentinelizing
        # their period before a lowercase follower BEFORE the classifier ran. The
        # data now stores them dotless (keyed "<abbr>."), the classifier enumerates
        # them directly, and ``KK_POLICY``'s widened follower override reproduces
        # exactly what the retired pass protected — so that whole-text pass (and its
        # ``_LOWERCASE_CONTINUATION_CHARS`` helper) is gone.
        #
        # Two Kazakh-specific whole-text passes remain because they cannot collapse
        # into the per-line classifier:
        #   1. (pre) Cyrillic single-uppercase-letter initials -> ``∯`` (run on the
        #      whole text before line-splitting in ``replace()``; ``^`` anchors the
        #      document start);
        #   2. (post) ``protect_multi_period_abbreviations_before_parenthesis`` —
        #      runs AFTER ``replace_multi_period_abbreviations`` (it matches interior
        #      ``∯`` that pass produced via ``[.∯]``), so it stays a whole-text
        #      post-pass — now expressed (S1) as the final entry of
        #      ``KK_POLICY.post_stages`` (``DEFAULT_POST_STAGES`` + this pass) rather
        #      than a hand-call after ``super().replace()``.
        ABBR_POLICY = KK_POLICY

        def replace(self) -> str:
            SingleUpperCaseCyrillicLetterAtStartOfLineRule = Rule(r"(?<=^[А-ЯЁ])\.(?=\s)", "∯")
            SingleUpperCaseCyrillicLetterRule = Rule(r"(?<=\s[А-ЯЁ])\.(?=\s)", "∯")
            self.text = apply_rules(
                self.text,
                SingleUpperCaseCyrillicLetterAtStartOfLineRule,
                SingleUpperCaseCyrillicLetterRule,
            )
            # KK_POLICY.post_stages == DEFAULT_POST_STAGES + the paren protection,
            # so ``super().replace()`` runs the extra Kazakh post-pass at the end.
            return super().replace()

        def protect_multi_period_abbreviations_before_parenthesis(self) -> None:
            for abbreviation in self.lang.Abbreviation.ABBREVIATIONS:
                abbreviation = abbreviation.strip()
                if not (abbreviation.endswith(".") and abbreviation.count(".") > 1):
                    continue
                body = re.escape(abbreviation[:-1]).replace(r"\.", r"[.∯]").replace(r"\ ", r"\s*")
                self.text = re.sub(rf"(?i:({body}))\.(?=\s*[(])", r"\1∯", self.text)
