# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.whole_span_abbr import whole_span_policy
from sentencesplit.lists_item_replacer import ListItemReplacer
from sentencesplit.processor import Processor
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import apply_rules

# Constant patterns compiled once at import instead of recompiled per call.
_SLOVAK_DOUBLE_QUOTES_RE = re.compile(r"\„(?=(?P<tmp>[^“\\]+|\\{2}|\\.)*)(?P=tmp)\“")
_SLOVAK_ORDINAL_PERIOD_RE = re.compile(r"(?<=\d)\.(?=\s*[a-z]+)")
_SLOVAK_ROMAN_PERIOD_RE = re.compile(r"((\s+[VXI]+)|(^[VXI]+))(\.)(?=\s+)", re.IGNORECASE)


# Slovak (Phase 5): the legacy ``Slovak.AbbreviationReplacer`` overrode ONLY the
# regular branch (``replace_period_of_abbr``); the PREPOSITIVE
# (``st``/``dr``/``ing``/``mgr``/``prof`` …) and NUMBER (``č``/``no``/``nr``)
# branches inherit the base ``_replace_with_escape`` / ``_replace_number_abbr``
# unchanged. The override replaced the base regular suffix
# ``\.(?=((\.|:|-|?|,)|(\s([a-z]|I…|\d|\())))`` with a literal whole-span
# ``txt.replace(abbr + ".", abbr.replace(".", "∯") + "∯")``. Two effects differ
# from the base regular branch:
#   1) UNCONDITIONAL — no follower-class lookahead. A known abbreviation's period
#      protects regardless of what follows ("napr. XYZCorp" -> "napr∯ XYZCorp",
#      "apod. Niečo" -> "apod∯ Niečo"). Slovak abbreviations frequently precede a
#      capitalized company/proper name, so a capital follower is NOT a boundary cue.
#   2) WHOLE-SPAN — every interior period of a spaced/compact abbreviation becomes
#      a sentinel too ("s. r. o." -> "s∯ r∯ o∯", "ph.d." -> "ph∯d∯",
#      "a.s.a.p." -> "a∯s∯a∯p∯"), keeping multi-word company forms like
#      "Company name s. r. o." as one token. The base regular branch only ever
#      protects the trailing period (relying on the later
#      ``replace_multi_period_abbreviations`` pass for interiors), which is wrong
#      for Slovak's spaced forms.
# This is structurally identical to Bulgarian's regular-branch override, so both
# ride the shared ``whole_span_policy()`` factory in
# ``lang/common/whole_span_abbr.py`` (see that module for the full behavior +
# quirk-fix notes).
SK_POLICY = whole_span_policy()


class Slovak(Common, Standard):
    iso_code = "sk"

    class ListItemReplacer(ListItemReplacer):
        def add_line_break(self):
            # We've found alphabetical lists are causing a lot of problems with abbreviations
            # with multiple periods and spaces, such as 'Company name s. r. o.'. Disabling
            # alphabetical list parsing seems like a reasonable tradeoff.

            # self.format_alphabetical_lists()
            self.format_roman_numeral_lists()
            self.format_numbered_list_with_periods()
            self.format_numbered_list_with_parens()
            return self.text

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2 PeriodClassifier (Phase 5). The legacy ``replace_period_of_abbr``
        # override — a literal whole-span ``txt.replace(abbr + ".", abbr.replace(".",
        # "∯") + "∯")`` that protected EVERY interior period of a spaced/compact
        # abbreviation ("Company name s. r. o." stays one token) UNCONDITIONALLY
        # (no follower-class lookahead, because Slovak abbreviations routinely
        # precede a capitalized company/proper name) — is reimplemented as
        # ``SK_POLICY`` (the shared ``whole_span_policy()`` factory in
        # ``lang/common/whole_span_abbr.py``). It overrides ONLY the regular branch;
        # the PREPOSITIVE / NUMBER branches inherit the base classifier unchanged.
        ABBR_POLICY = SK_POLICY

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = [
            "č",
            "no",
            "nr",
            "s. r. o",
            "ing",
            "p",
            "a. d",
            "o. k",
            "pol. pr",
            "a. s. a. p",
            "p. n. l",
            "red",
            "o.k",
            "a.d",
            "m.o",
            "pol.pr",
            "a.s.a.p",
            "p.n.l",
            "pp",
            "sl",
            "corp",
            "plgr",
            "tz",
            "rtg",
            "o.c.p",
            "o. c. p",
            "c.k",
            "c. k",
            "n.a",
            "n. a",
            "a.m",
            "a. m",
            "vz",
            "i.b",
            "i. b",
            "ú.p.v.o",
            "ú. p. v. o",
            "bros",
            "rsdr",
            "doc",
            "tu",
            "ods",
            "n.w.a",
            "n. w. a",
            "nár",
            "pedg",
            "paeddr",
            "rndr",
            "naprk",
            "a.g.p",
            "a. g. p",
            "prof",
            "pr",
            "a.v",
            "a. v",
            "por",
            "mvdr",
            "nešp",
            "u.s",
            "u. s",
            "kt",
            "vyd",
            "e.t",
            "e. t",
            "al",
            "ll.m",
            "ll. m",
            "o.f.i",
            "o. f. i",
            "mr",
            "apod",
            "súkr",
            "stred",
            "s.e.g",
            "s. e. g",
            "sr",
            "tvz",
            "ind",
            "var",
            "etc",
            "atd",
            "n.o",
            "n. o",
            "s.a",
            "s. a",
            "např",
            "a.i.i",
            "a. i. i",
            "a.k.a",
            "a. k. a",
            "konkr",
            "čsl",
            "odd",
            "ltd",
            "t.z",
            "t. z",
            "o.z",
            "o. z",
            "obv",
            "obr",
            "pok",
            "tel",
            "št",
            "skr",
            "phdr",
            "xx",
            "š.p",
            "š. p",
            "ph.d",
            "ph. d",
            "m.n.m",
            "m. n. m",
            "zz",
            "roz",
            "ev",
            "v.sp",
            "v. sp",
            "drsc",
            "mudr",
            "t.č",
            "t. č",
            "el",
            "os",
            "co",
            "r.o",
            "r. o",
            "str",
            "p.a",
            "p. a",
            "zdravot",
            "prek",
            "gen",
            "viď",
            "dr",
            "cca",
            "p.s",
            "p. s",
            "zák",
            "slov",
            "arm",
            "inc",
            "max",
            "d.c",
            "k.o",
            "a. r. k",
            "d. c",
            "k. o",
            "soc",
            "bc",
            "zs",
            "akad",
            "sz",
            "pozn",
            "tr",
            "nám",
            "kol",
            "csc",
            "ul",
            "sp",
            "o.i",
            "jr",
            "zb",
            "sv",
            "tj",
            "čs",
            "tzn",
            "príp",
            "iv",
            "hl",
            "st",
            "pod",
            "vi",
            "tis",
            "stor",
            "rozh",
            "mld",
            "atď",
            "mgr",
            "a.s",
            "a. s",
            "phd",
            "z.z",
            "z. z",
            "judr",
            "hod",
            "vs",
            "písm",
            "s.r.o",
            "min",
            "ml",
            "iii",
            "t.j",
            "t. j",
            "spol",
            "mil",
            "ii",
            "napr",
            "resp",
            "tzv",
        ]
        PREPOSITIVE_ABBREVIATIONS = ["st", "dr", "mudr", "judr", "ing", "mgr", "bc", "drsc", "doc", "prof"]
        NUMBER_ABBREVIATIONS = ["č", "no", "nr"]

    class BetweenPunctuation(BetweenPunctuation):
        # Rubular: https://rubular.com/r/rImWbaYFtHHtf4
        BETWEEN_SLOVAK_DOUBLE_QUOTES_REGEX = r"„(?>[^“\\]+|\\{2}|\\.)*“"
        BETWEEN_SLOVAK_DOUBLE_QUOTES_REGEX_2 = r"\„(?=(?P<tmp>[^“\\]+|\\{2}|\\.)*)(?P=tmp)\“"

        def sub_punctuation_between_slovak_double_quotes(self, txt):
            return _SLOVAK_DOUBLE_QUOTES_RE.sub(replace_punctuation, txt)

        def sub_punctuation_between_quotes_and_parens(self, txt):
            txt = self.sub_punctuation_between_single_quotes(txt)
            txt = self.sub_punctuation_between_single_quote_slanted(txt)
            txt = self.sub_punctuation_between_double_quotes(txt)
            txt = self.sub_punctuation_between_square_brackets(txt)
            txt = self.sub_punctuation_between_parens(txt)
            txt = self.sub_punctuation_between_quotes_arrow(txt)
            txt = self.sub_punctuation_between_em_dashes(txt)
            txt = self.sub_punctuation_between_quotes_slanted(txt)
            txt = self.sub_punctuation_between_slovak_double_quotes(txt)
            return txt

    class Processor(Processor):
        def replace_numbers(self, text: str) -> str:
            text = apply_rules(text, *self.profile.number_rules)
            text = self.replace_period_in_slovak_dates(text)
            text = self.replace_period_in_ordinal_numerals(text)
            text = self.replace_period_in_roman_numerals(text)
            return text

        def replace_period_in_ordinal_numerals(self, text: str) -> str:
            # Rubular: https://rubular.com/r/0HkmvzMGTqgWs6
            return _SLOVAK_ORDINAL_PERIOD_RE.sub("∯", text)

        def replace_period_in_roman_numerals(self, text: str) -> str:
            # Rubular: https://rubular.com/r/XlzTIi7aBRThSl
            return _SLOVAK_ROMAN_PERIOD_RE.sub(r"\1∯", text)

        def replace_period_in_slovak_dates(self, text: str) -> str:
            MONTHS = [
                "Január",
                "Február",
                "Marec",
                "Apríl",
                "Máj",
                "Jún",
                "Júl",
                "August",
                "September",
                "Október",
                "November",
                "December",
                "Januára",
                "Februára",
                "Marca",
                "Apríla",
                "Mája",
                "Júna",
                "Júla",
                "Augusta",
                "Septembra",
                "Októbra",
                "Novembra",
                "Decembra",
            ]
            for month in MONTHS:
                # Rubular: https://rubular.com/r/dGLZqsbjcdJvCd
                text = re.sub(rf"(?<=\d)\.(?=\s*{month})", "∯", text)
            return text
