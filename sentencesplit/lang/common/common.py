# -*- coding: utf-8 -*-
import re

from sentencesplit.utils import Rule

# A "letter" eligible to be a single token in a dotted initialism (``A.I.``,
# ``d.å.``, ``μ.χ.``) — any Unicode cased/letter codepoint EXCEPT the ideographic
# / syllabic scripts that ``re``'s ``\w`` also counts as word characters but which
# never spell a Latin/Cyrillic/Greek abbreviation. Excluding them is load-bearing:
# a naive Unicode letter class (or the ``(?<!\w)`` lookbehind the bg/el overrides
# use) treats CJK as ``\w`` and mis-anchors ``项目代号是A.I.-7。`` — greedily eating
# ``号是`` into the match — so the base MUST anchor on this non-CJK-aware class
# (see ``test_chinese.py::test_zh_challenging``). The excluded
# ranges are Hiragana/Katakana, CJK Unified + Ext A, CJK Compatibility Ideographs,
# Hangul syllables, Bopomofo, and Halfwidth/Fullwidth forms.
_NON_CJK_LETTER = r"[^\W\d_぀-ヿ㐀-䶿一-鿿豈-﫿가-힯㄀-ㄯ＀-￯]"


class Common:
    # added special case: r"[。．.！!? ]{2,}" to handle intermittent dots, exclamation, etc.
    # r"[。．.！!?] at end to handle single instances of these symbol inputs
    _SENTENCE_END_PUNCT = r"[。．.！!?？ȸȹ☉☈☇☄☊☋☌☍]"
    _SENTENCE_BOUNDARY_PARTS = [
        r"（(?:[^）])*）(?=\s?[A-Z])",
        r"「(?:[^」])*」(?=\s[A-Z])",
        r"\((?:[^\)]){2,}\)(?=\s[A-Z])",
        r"\'(?:[^\'])*[^,]\'(?=\s[A-Z])",
        r"\"(?:[^\"])*[^,]\"(?=\s[A-Z])",
        r"\“(?:[^\”])*[^,]\”(?=\s[A-Z])",
        r"[。．.！!?？ ]{2,}",
        r"\S[^\n。．.！!?？ȸȹ☉☈☇☄☊☋☌☍]*" + _SENTENCE_END_PUNCT,
        _SENTENCE_END_PUNCT,
    ]
    SENTENCE_BOUNDARY_REGEX = re.compile("|".join(_SENTENCE_BOUNDARY_PARTS))

    LATIN_UPPERCASE_RESPLIT = True

    # Broadened to match any non-space continuation (not just ASCII uppercase).
    # For Latin languages (LATIN_UPPERCASE_RESPLIT=True), the actual uppercase/CJK
    # check is performed by _split_on_uppercase_boundary in processor.py.
    # CJK languages override this regex entirely in CJKBoundaryProfile.
    # # Rubular: http://rubular.com/r/NqCqv372Ix
    QUOTATION_AT_END_OF_SENTENCE_REGEX = re.compile(r"[!?\.-][\"\'“”]\s+\S")

    # # Rubular: http://rubular.com/r/6flGnUMEVl
    PARENS_BETWEEN_DOUBLE_QUOTES_REGEX = re.compile(r'["\”]\s\(.*\)\s["\“]')

    # Broadened to split on any whitespace (not just before ASCII uppercase).
    # The uppercase/CJK guard is applied by _split_on_uppercase_boundary when
    # LATIN_UPPERCASE_RESPLIT is True; CJK languages override in CJKBoundaryProfile.
    # # Rubular: http://rubular.com/r/JMjlZHAT4g
    SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX = re.compile(r"(?<=[!?\.-][\"\'“”])\s+")

    # # Rubular: http://rubular.com/r/mQ8Es9bxtk
    CONTINUOUS_PUNCTUATION_REGEX = re.compile(r"(?<=\S)(!|\?){3,}(?=(\s|\Z|$))")

    # https://rubular.com/r/UkumQaILKbkeyc
    # https://github.com/diasks2/pragmatic_segmenter/commit/d9ec1a352aff92b91e2e572c30bb9561eb42c703
    NUMBERED_REFERENCE_REGEX = re.compile(
        r"(?<=[^\d\s])(\.|∯)((\[(\d{1,3},?\s?-?\s?)?\b\d{1,3}\])+|((\d{1,3}\s?){0,3}\d{1,3}))(\s)(?=[A-Z])"
    )

    # # Rubular: http://rubular.com/r/yqa4Rit8EY
    PossessiveAbbreviationRule = Rule(r"\.(?='s\s)|\.(?='s$)|\.(?='s\Z)", "∯")

    # # Rubular: http://rubular.com/r/NEv265G2X2
    KommanditgesellschaftRule = Rule(r"(?<=Co)\.(?=\sKG)", "∯")

    # Match dotted abbreviations without relying on \b, which treats CJK letters
    # as word characters and misses cases like "中文A.I.-7". The letter class is
    # Unicode (minus CJK — see ``_NON_CJK_LETTER``) so non-ASCII multi-period
    # initialisms — Danish "d.å.", German "o.ä.", Greek "μ.χ." — are recognised
    # too, not just ASCII ones (roadmap S6). The separators/terminator accept the
    # protected sentinel "∯" as well as a literal ".", because when the whole
    # token is a *declared* abbreviation the classifier has already converted its
    # final period to "∯" before this pass runs ("μ.χ∯"); without the "∯" arm the
    # regex could not re-find such tokens to protect their *interior* dots, and
    # the entry would split mid-token. The final segment is limited to a single
    # letter so domains such as "example.co.uk." are not mistaken for
    # abbreviations.
    MULTI_PERIOD_ABBREVIATION_REGEX = re.compile(
        rf"(?<![A-Za-z0-9_])(?:{_NON_CJK_LETTER}{{1,3}}[.∯])+{_NON_CJK_LETTER}[.∯]",
        re.IGNORECASE | re.UNICODE,
    )

    class SingleLetterAbbreviationRules:
        """Searches for periods within an abbreviation and
        replaces the periods.
        """

        # Rubular: http://rubular.com/r/e3H6kwnr6H
        SingleUpperCaseLetterAtStartOfLineRule = Rule(r"(?<=^[A-Z])\.(?=\s)", "∯")

        # Rubular: http://rubular.com/r/gitvf0YWH4
        SingleUpperCaseLetterRule = Rule(r"(?<=\s[A-Z])\.(?=,?\s)", "∯")

        All = [SingleUpperCaseLetterAtStartOfLineRule, SingleUpperCaseLetterRule]

    class AmPmRules:
        # Timezone abbreviations that commonly follow a.m./p.m. and should
        # NOT be treated as sentence starters.
        # Supports both plain (EST) and dotted/protected forms (E.S.T. / E∯S∯T∯)
        # that exist after multi-period abbreviation replacement.
        # Spelled-out timezone names that follow a.m./p.m. as a multi-word unit
        # ("9 a.m. Eastern Standard Time"). These read as a Title-Case sentence
        # start to the generic capital-follower gate, so they are listed here to
        # keep the time+zone unit together. Anchored on the trailing "Time"
        # keyword (or "Universal/Mean Time") so an ordinary capitalized sentence
        # start ("9 a.m. The meeting started.") is never absorbed.
        _TZ_NAME = (
            r"(?:Eastern|Central|Mountain|Pacific|Atlantic|Alaska|Hawaii(?:-Aleutian)?|Newfoundland)"
            r"\s+(?:Standard\s+|Daylight\s+|Summer\s+)?Time"
            r"|Coordinated\s+Universal\s+Time"
            r"|Greenwich\s+Mean\s+Time"
        )
        _TZ = (
            r"(?:" + _TZ_NAME + r"|"
            r"[ECMP][SD]T"  # US: EST, EDT, CST, CDT, MST, MDT, PST, PDT
            r"|GMT|UTC"  # Universal
            r"|CET|CEST|WET|WEST|EET|EEST"  # Europe
            r"|BST|MSK|IST"  # UK, Moscow, India/Ireland/Israel
            r"|JST|KST|HKT|SGT"  # East Asia
            r"|(?:AE|NZ)[SD]T"  # Australia/NZ: AEST, AEDT, NZST, NZDT
            r"|AST|AKST|HST|NST"  # US/Canada outlying
            r"|E[.∯]S[.∯]T|E[.∯]D[.∯]T|C[.∯]S[.∯]T|C[.∯]D[.∯]T"
            r"|M[.∯]S[.∯]T|M[.∯]D[.∯]T|P[.∯]S[.∯]T|P[.∯]D[.∯]T"
            r"|A[.∯]S[.∯]T|A[.∯]D[.∯]T|G[.∯]M[.∯]T|U[.∯]T[.∯]C"
            r")(?:\s|$|[.∯])"
        )

        # Normalize spaced AM/PM forms (e.g. "a. m.", "P. M.") so they
        # behave like compact "a.m."/ "p.m." in boundary logic.
        SpacedAmPmRule = Rule(r"\b([AaPp])\.(\s+)([Mm])\.(?=((\.|:|-|\?|,)|(\s)))", r"\1∯\2\3∯")

        # Restore a.m./p.m. boundaries only when the token is part of a numeric
        # time expression. Bare "P.M. Trudeau" remains a generic two-part
        # initialism, not a time boundary.
        UpperCasePmRule = Rule(r"(\d\s*P∯M)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")

        UpperCaseAmRule = Rule(r"(\d\s*A∯M)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")

        LowerCasePmRule = Rule(r"(\d\s*p∯m)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")

        LowerCaseAmRule = Rule(r"(\d\s*a∯m)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")

        SpacedUpperCasePmRule = Rule(r"(\d\s+P∯\s+M)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")
        SpacedUpperCaseAmRule = Rule(r"(\d\s+A∯\s+M)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")
        SpacedLowerCasePmRule = Rule(r"(\d\s+p∯\s+m)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")
        SpacedLowerCaseAmRule = Rule(r"(\d\s+a∯\s+m)∯(?=\s(?!" + _TZ + r")[A-Z])", r"\1.")

        All = [
            SpacedAmPmRule,
            UpperCasePmRule,
            UpperCaseAmRule,
            LowerCasePmRule,
            LowerCaseAmRule,
            SpacedUpperCasePmRule,
            SpacedUpperCaseAmRule,
            SpacedLowerCasePmRule,
            SpacedLowerCaseAmRule,
        ]

    class Numbers:
        # Rubular: http://rubular.com/r/oNyxBOqbyy
        PeriodBeforeNumberRule = Rule(r"\.(?=\d)", "∯")

        # Rubular: http://rubular.com/r/EMk5MpiUzt
        NumberAfterPeriodBeforeLetterRule = Rule(r"(?<=\d)\.(?=\S)", "∯")

        # Rubular: http://rubular.com/r/rf4l1HjtjG
        NewLineNumberPeriodSpaceLetterRule = Rule(r"(?<=\r\d)\.(?=(\s\S)|\))", "∯")

        # Rubular: http://rubular.com/r/HPa4sdc6b9
        StartLineNumberPeriodRule = Rule(r"(?<=^\d)\.(?=(\s\S)|\))", "∯")

        # Rubular: http://rubular.com/r/NuvWnKleFl
        StartLineTwoDigitNumberPeriodRule = Rule(r"(?<=^\d\d)\.(?=(\s\S)|\))", "∯")

        # "in." as measurement abbreviation (inches) only after a digit.
        # Distinguishes "5 in. wide" (measurement, non-boundary) from
        # "walked in. She left" (preposition, boundary).
        InchesAbbreviationRule = Rule(r"(?<=\d )in\.(?=\s[a-z])", "in∯")

        All = [
            PeriodBeforeNumberRule,
            NumberAfterPeriodBeforeLetterRule,
            NewLineNumberPeriodSpaceLetterRule,
            StartLineNumberPeriodRule,
            StartLineTwoDigitNumberPeriodRule,
            InchesAbbreviationRule,
        ]
