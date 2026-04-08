# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.utils import Rule


class Standard:
    # This class holds the punctuation marks.
    Punctuations = ["。", "．", ".", "！", "!", "?", "？"]

    # Rubular: http://rubular.com/r/G2opjedIm9
    GeoLocationRule = Rule(r"(?<=[a-zA-z]°)\.(?=\s*\d+)", "∯")

    FileFormatRule = Rule(
        r"(?<=\s)\.(?=(jpe?g|png|gif|tiff?|pdf|ps|docx?|xlsx?|svg|bmp|tga|exif|odt|html?|txt|rtf|bat|sxw|xml|zip|exe|msi|blend|wmv|mp[34]|pptx?|flac|rb|cpp|cs|js)\s)",
        "∯",
    )

    DotNetRule = Rule(r"(?<=\s)\.(?=NET\b)", "∯")

    SingleNewLineRule = Rule(r"\n", "ȹ")

    # Rubular: http://rubular.com/r/aXPUGm6fQh
    QuestionMarkInQuotationRule = Rule(r"\?(?=(\'|\"))", "&ᓷ&")

    ExtraWhiteSpaceRule = Rule(r"\s{3,}", " ")

    SubSingleQuoteRule = Rule(r"&⎋&", "'")

    class Abbreviation:
        """Defines the abbreviations for each language (if available)"""

        ELISION_CHARACTERS = ""
        ABBREVIATIONS = [
            "adj",
            "adm",
            "adv",
            "al",
            "ala",
            "alta",
            "approx",
            "apr",
            "arc",
            "ariz",
            "ark",
            "art",
            "assn",
            "asst",
            "attys",
            "aug",
            "avg",
            "ave",
            "bart",
            "bld",
            "bldg",
            "blvd",
            "brig",
            "bros",
            "btw",
            "cal",
            "calif",
            "capt",
            "cl",
            "cmdr",
            "co",
            "col",
            "colo",
            "comdr",
            "con",
            "conn",
            "corp",
            "cpl",
            "cres",
            "ct",
            "d.phil",
            "dak",
            "dec",
            "del",
            "dept",
            "det",
            "dist",
            "dr",
            "dr.phil",
            "dr.philos",
            "drs",
            "e.g",
            "eq",
            "ens",
            "esp",
            "esq",
            "est",
            "etc",
            "exp",
            "expy",
            "ext",
            "feb",
            "fed",
            "fla",
            "ft",
            "fwy",
            "fy",
            "ga",
            "gen",
            "gov",
            "govt",
            "hon",
            "hosp",
            "hr",
            "hway",
            "hwy",
            "i.e",
            "ia",
            "id",
            "ida",
            "ill",
            "inc",
            "ind",
            "ing",
            "insp",
            "is",
            "jan",
            "jr",
            "jul",
            "jun",
            "kan",
            "kans",
            "ken",
            "ky",
            "la",
            "lt",
            "ltd",
            "maj",
            "mar",
            "max",
            "mass",
            "may",
            "md",
            "me",
            "med",
            "messrs",
            "mex",
            "mfg",
            "mich",
            "misc",
            "min",
            "minn",
            "miss",
            "mlle",
            "mm",
            "mme",
            "mo",
            "mont",
            "mr",
            "mrs",
            "ms",
            "msgr",
            "mssrs",
            "mt",
            "mtn",
            "natl",
            "neb",
            "nebr",
            "nev",
            "no",
            "nos",
            "nov",
            "nr",
            "oct",
            "ok",
            "okla",
            "ont",
            "op",
            "ord",
            "ore",
            "orig",
            "p",
            "pa",
            "pd",
            "pde",
            "penn",
            "penna",
            "pfc",
            "ph",
            "ph.d",
            "pl",
            "plz",
            "pp",
            "prof",
            "pt",
            "pvt",
            "que",
            "rd",
            "rs",
            "ref",
            "rep",
            "reps",
            "res",
            "rev",
            "rt",
            "sask",
            "sec",
            "sen",
            "sens",
            "sep",
            "sept",
            "sfc",
            "sgt",
            "sr",
            "st",
            "supt",
            "surg",
            "tce",
            "tel",
            "tenn",
            "tex",
            "univ",
            "usafa",
            "u.s",
            "ut",
            "va",
            "v",
            "ver",
            "viz",
            "vol",
            "vs",
            "vt",
            "wash",
            "wis",
            "wisc",
            "wy",
            "wyo",
            "yuk",
            "fig",
        ]
        # Prepositive abbreviations always attach to the word that follows them,
        # so a period after them is never a sentence boundary.  These are
        # primarily titles, honorifics, and rank designators (Mr., Dr., Gen.)
        # as well as a handful of connectives (v., vs.) that bind two names.
        PREPOSITIVE_ABBREVIATIONS = [
            "adm",
            "attys",
            "brig",
            "capt",
            "cmdr",
            "col",
            "cpl",
            "det",
            "dr",
            "gen",
            "gov",
            "ing",
            "lt",
            "maj",
            "mr",
            "mrs",
            "ms",
            "mt",
            "messrs",
            "mssrs",
            "prof",
            "rep",
            "reps",
            "rev",
            "sen",
            "sens",
            "sgt",
            "st",
            "supt",
            "v",
            "vs",
        ]
        NUMBER_ABBREVIATIONS = ["approx", "art", "est", "ext", "fig", "no", "nos", "p", "pp", "tel", "vol"]

        # Rubular: http://rubular.com/r/EUbZCNfgei
        # \w in python matches unicode abbreviations also so limit to english alphanumerics
        WithMultiplePeriodsAndEmailRule = Rule(r"([a-zA-Z0-9_])(\.)([a-zA-Z0-9_])", "\\1∮\\3")

    class DoublePunctuationRules:
        FirstRule = Rule(r"\?!", "☉")
        SecondRule = Rule(r"!\?", "☈")
        ThirdRule = Rule(r"\?\?", "☇")
        ForthRule = Rule(r"!!", "☄")
        FullWidthFirstRule = Rule(r"？！", "☋")
        FullWidthSecondRule = Rule(r"！？", "☌")
        FullWidthThirdRule = Rule(r"？？", "☊")
        FullWidthForthRule = Rule(r"！！", "☍")
        DoublePunctuation = re.compile(r"\?!|!\?|\?\?|!!|？！|！？|？？|！！")
        All = [
            FirstRule,
            SecondRule,
            ThirdRule,
            ForthRule,
            FullWidthFirstRule,
            FullWidthSecondRule,
            FullWidthThirdRule,
            FullWidthForthRule,
        ]

    class ExclamationPointRules:
        # Rubular: http://rubular.com/r/XS1XXFRfM2
        InQuotationRule = Rule(r"\!(?=(\'|\"))", "&ᓴ&")

        # Rubular: http://rubular.com/r/sl57YI8LkA
        BeforeCommaMidSentenceRule = Rule(r"\!(?=\,\s[a-z])", "&ᓴ&")

        # Rubular: http://rubular.com/r/f9zTjmkIPb
        MidSentenceRule = Rule(r"\!(?=\s[a-z])", "&ᓴ&")

        All = [InQuotationRule, BeforeCommaMidSentenceRule, MidSentenceRule]

    class SubSymbolsRules:
        """Reverse temporary symbols back to their original punctuation.

        Uses str.replace() via SUBS_TABLE for performance since all
        substitutions are literal strings (no regex needed).
        """

        SUBS_TABLE = [
            ("∯", "."),
            ("♬", "،"),
            ("♭", ":"),
            ("&ᓰ&", "。"),
            ("&ᓱ&", "．"),
            ("&ᓳ&", "！"),
            ("&ᓴ&", "!"),
            ("&ᓷ&", "?"),
            ("&ᓸ&", "？"),
            ("☉", "?!"),
            ("☇", "??"),
            ("☈", "!?"),
            ("☄", "!!"),
            ("☊", "？？"),
            ("☋", "？！"),
            ("☌", "！？"),
            ("☍", "！！"),
            ("&✂&", "("),
            ("&⌬&", ")"),
            ("ȸ", ""),
            ("ȹ", "\n"),
        ]

    class EllipsisRules:
        # below rules aren't similar to original rules of pragmatic segmenter
        # modification: spaces replaced with same number of symbols
        # Rubular: http://rubular.com/r/i60hCK81fz
        ThreeConsecutiveRule = Rule(r"\.\.\.(?=\s+[A-Z])", "☏☏.")

        # Rubular: http://rubular.com/r/Hdqpd90owl
        FourConsecutiveRule = Rule(r"(?<=\S)\.{3}(?=\.\s[A-Z])", "ƪƪƪ")

        # Rubular: http://rubular.com/r/YBG1dIHTRu
        ThreeSpaceRule = Rule(r"(\s\.){3}\s", "♟♟♟♟♟♟♟")

        # Rubular: http://rubular.com/r/2VvZ8wRbd8
        FourSpaceRule = Rule(r"(?<=[a-z])(\.\s){3}\.($|\\n)", "♝♝♝♝♝♝♝")

        OtherThreePeriodRule = Rule(r"\.\.\.", "ƪƪƪ")

        TwoConsecutiveRule = Rule(r"(?<=\w\s)\.\.(?=\s[a-z])", "☏☏")

        All = [
            ThreeSpaceRule,
            FourSpaceRule,
            FourConsecutiveRule,
            ThreeConsecutiveRule,
            OtherThreePeriodRule,
            TwoConsecutiveRule,
        ]

    class ReinsertEllipsisRules:
        # below rules aren't similar to original rules of pragmatic segmenter
        # modification: symbols replaced with same number of ellipses
        SubThreeConsecutivePeriod = Rule(r"ƪƪƪ", "...")
        SubThreeSpacePeriod = Rule(r"♟♟♟♟♟♟♟", " . . . ")
        SubFourSpacePeriod = Rule(r"♝♝♝♝♝♝♝", ". . . .")
        SubTwoConsecutivePeriod = Rule(r"☏☏", "..")
        SubOnePeriod = Rule(r"∮", ".")
        All = [SubThreeConsecutivePeriod, SubThreeSpacePeriod, SubFourSpacePeriod, SubTwoConsecutivePeriod, SubOnePeriod]

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = (
            "A Being Did For He How However I In It Millions More She That The There They We What When Where Who Why".split(
                " "
            )
        )
