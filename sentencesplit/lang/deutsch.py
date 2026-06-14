# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.period_classifier import AbbrPolicy, Candidate, Decision, PeriodClassifier
from sentencesplit.processor import Processor
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule, apply_rules

# Rubular: http://rubular.com/r/TkZomF9tTM
_BETWEEN_DOUBLE_QUOTES_DE_RE = re.compile(r"„(?=(?P<tmp>[^“\\]+|\\{2}|\\.)*)(?P=tmp)“")

# Rubular: http://rubular.com/r/OdcXBsub0w
_BETWEEN_UNCONVENTIONAL_DOUBLE_QUOTE_DE_RE = re.compile(r",,(?=(?P<tmp>[^“\\]+|\\{2}|\\.)*)(?P=tmp)“")


# German (Phase 5): the legacy ``Deutsch.AbbreviationReplacer`` overrode
# ``scan_for_replacements`` to a SINGLE rule, ``re.sub(r"(?<={am})\.(?=\s)", "∯")``,
# bypassing the base prepositive / number / regular trichotomy entirely. The
# effective behavior: PROTECT a known abbreviation's period whenever it is
# followed by whitespace, REGARDLESS of the follower's case — so "Dr. med. Meyer"
# keeps both periods even though "Meyer" is capitalized (German capitalizes all
# nouns, so a capital follower is NOT a sentence-start cue). ``classify_special``
# below replaces every branch; ``realize_suffix`` pins the realization pass to the
# same ``\.(?=\s)`` suffix so global PROTECT matches the decision exactly.
#
# Quirk FIXED (BC not required, plan §3): the legacy interpolated ``{am}``
# (== ``m.group()``, the boundary char + abbreviation) UNescaped into the
# lookbehind. ``_full_pattern`` re.escapes the abbreviation, so the V2 path is
# escape-everything-correct. The legacy "" works only by accident of the German
# abbreviation list containing no regex metacharacters; the V2 path is robust.
_DE_PROTECT_BEFORE_WHITESPACE = re.compile(r"\.(?=\s)")


def _de_classify_special(pc: "PeriodClassifier", line: str, c: Candidate) -> object:
    """German: every candidate period before whitespace PROTECTs; else BOUNDARY.

    Reproduces ``Deutsch.AbbreviationReplacer.scan_for_replacements`` (one rule,
    all branches collapsed). The candidate is already a known ``<abbr>.`` at a
    word boundary (enumeration's reachability gate), so only the suffix
    ``\\.(?=\\s)`` is tested here.
    """
    if _DE_PROTECT_BEFORE_WHITESPACE.match(line, c.period_idx):
        return Decision.PROTECT
    return Decision.BOUNDARY


def _de_realize_suffix(pc: "PeriodClassifier", c: Candidate, line: str, d: "Decision") -> str:
    """German global-realization suffix: ``\\.(?=\\s)`` for every PROTECT."""
    return _DE_PROTECT_BEFORE_WHITESPACE.pattern


DE_POLICY = AbbrPolicy(
    classify_special=_de_classify_special,
    realize_suffix=_de_realize_suffix,
)


class Deutsch(Common, Standard):
    iso_code = "de"

    class Numbers(Common.Numbers):
        # Rubular: http://rubular.com/r/hZxoyQwKT1
        NumberPeriodSpaceRule = Rule(r"(?<=\s\d)\.(?=\s)|(?<=\s\d\d)\.(?=\s)", "∯")

        # Rubular: http://rubular.com/r/ityNMwdghj
        NegativeNumberPeriodSpaceRule = Rule(r"(?<=-\d)\.(?=\s)|(?<=-\d\d)\.(?=\s)", "∯")

        All = Common.Numbers.All + [NumberPeriodSpaceRule, NegativeNumberPeriodSpaceRule]

    class Processor(Processor):
        def replace_numbers(self, text: str) -> str:
            text = apply_rules(text, *self.profile.number_rules)
            return self.replace_period_in_deutsch_dates(text)

        def replace_period_in_deutsch_dates(self, text: str) -> str:
            MONTHS = [
                "Januar",
                "Februar",
                "März",
                "April",
                "Mai",
                "Juni",
                "Juli",
                "August",
                "September",
                "Oktober",
                "November",
                "Dezember",
            ]
            for month in MONTHS:
                # Rubular: http://rubular.com/r/zlqgj7G5dA
                text = re.sub(rf"(?<=\d)\.(?=\s*{month})", "∯", text)
            return text

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = [
            "ä",
            "adj",
            "adm",
            "adv",
            "art",
            "asst",
            "b.a",
            "b.s",
            "bart",
            "bldg",
            "brig",
            "bros",
            "bse",
            "buchst",
            "bzgl",
            "bzw",
            "c.-à-d",
            "ca",
            "capt",
            "chr",
            "cmdr",
            "co",
            "col",
            "comdr",
            "con",
            "corp",
            "cpl",
            "d.h",
            "d.j",
            "dergl",
            "dgl",
            "dkr",
            "dr",
            "ens",
            "etc",
            "ev",
            "evtl",
            "ff",
            "g.g.a",
            "g.u",
            "gen",
            "ggf",
            "gov",
            "hon",
            "hosp",
            "i.f",
            "i.h.v",
            "ii",
            "iii",
            "insp",
            "iv",
            "ix",
            "jun",
            "k.o",
            "kath",
            "lfd",
            "lt",
            "ltd",
            "m.e",
            "maj",
            "med",
            "messrs",
            "mio",
            "mlle",
            "mm",
            "mme",
            "mr",
            "mrd",
            "mrs",
            "ms",
            "msgr",
            "mwst",
            "no",
            "nos",
            "nr",
            "o.ä",
            "op",
            "ord",
            "pfc",
            "ph",
            "pp",
            "prof",
            "pvt",
            "rep",
            "reps",
            "res",
            "rev",
            "rt",
            "s.p.a",
            "sa",
            "sen",
            "sens",
            "sfc",
            "sgt",
            "sog",
            "sogen",
            "spp",
            "sr",
            "st",
            "std",
            "str",
            "supt",
            "surg",
            "u.a",
            "u.e",
            "u.s.w",
            "u.u",
            "u.ä",
            "usf",
            "usw",
            "v",
            "vgl",
            "vi",
            "vii",
            "viii",
            "vs",
            "x",
            "xi",
            "xii",
            "xiii",
            "xiv",
            "xix",
            "xv",
            "xvi",
            "xvii",
            "xviii",
            "xx",
            "z.b",
            "z.t",
            "z.z",
            "z.zt",
            "zt",
            "zzt",
            "univ.-prof",
            "o.univ.-prof",
            "ao.univ.prof",
            "ass.prof",
            "hon.prof",
            "univ.-doz",
            "univ.ass",
            "stud.ass",
            "projektass",
            "ass",
            "di",
            "dipl.-ing",
            "mag",
        ]
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = ["art", "ca", "no", "nos", "nr", "pp"]

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2: route the abbreviation-protection step through the PeriodClassifier.
        # DE_POLICY re-encodes the formerly-overridden ``scan_for_replacements``
        # (one rule, all branches collapsed) as data:
        #   - classify_special: PROTECT a known abbreviation's period whenever it
        #     is followed by whitespace, regardless of follower case (German
        #     capitalizes all nouns, so a capital follower is not a boundary cue);
        #     so "Dr. med. Meyer" keeps both periods.
        #   - realize_suffix: pin the global realization to the same ``\.(?=\s)``.
        # The reordered German ``replace()`` (whole-text protection; no
        # Kommanditgesellschaft / compact-ampm / uppercase-initialism / allcaps
        # imprint / standalone-I passes) is preserved below — only the protection
        # step now delegates to the classifier. The legacy unescaped-``{am}``
        # quirk is FIXED: ``_full_pattern`` re.escapes the abbreviation.
        ABBR_POLICY = DE_POLICY

        def replace(self):
            # Rubular: http://rubular.com/r/B4X33QKIL8
            SingleLowerCaseLetterRule = Rule(r"(?<=\s[a-z])\.(?=\s)", "∯")

            # Rubular: http://rubular.com/r/iUNSkCuso0
            SingleLowerCaseLetterAtStartOfLineRule = Rule(r"(?<=^[a-z])\.(?=\s)", "∯")
            self.text = apply_rules(
                self.text,
                self.lang.PossessiveAbbreviationRule,
                *self.lang.SingleLetterAbbreviationRules.All,
                SingleLowerCaseLetterRule,
                SingleLowerCaseLetterAtStartOfLineRule,
            )

            # Whole-text (not per-line) abbreviation protection; this routes
            # through the V2 classifier's single-pass rewrite (same DE_POLICY
            # decision on every candidate).
            self.text = self.search_for_abbreviations_in_string(self.text)
            self.replace_multi_period_abbreviations()
            # German never restored non-ASCII a.m./p.m. boundaries; keep that
            # while honoring the conservative split-bias dial.
            self.apply_ampm_boundary_rules(restore_non_ascii=False)
            # No standalone-"I" boundary restoration: "I" is not a German
            # pronoun, so RESTORE_STANDALONE_I_BOUNDARIES stays False for German
            # (only english / en_legal / en_es_zh enable it).
            return self.text

    class BetweenPunctuation(BetweenPunctuation):
        def sub_punctuation_between_double_quotes(self, txt):
            if "„" in txt:
                return _BETWEEN_DOUBLE_QUOTES_DE_RE.sub(replace_punctuation, txt)
            elif ",," in txt:
                return _BETWEEN_UNCONVENTIONAL_DOUBLE_QUOTE_DE_RE.sub(replace_punctuation, txt)
            else:
                return txt
