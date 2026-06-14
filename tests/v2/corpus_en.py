# -*- coding: utf-8 -*-
"""Curated English abbreviation-boundary correctness corpus (V2 acceptance gate).

Per ``analysis/ABBREVIATION_ENGINE_V2_PLAN.md`` §1.2 and §1.5, this corpus is a
PRIMARY gate (alongside the Golden Rules + full suite), NOT a legacy-mimicry
oracle. Each entry labels the **linguistically-correct** sentence segmentation —
which is *not always* what the legacy engine produces today.

Entries are ``CorpusCase`` records. ``xfail=True`` marks a case the LEGACY engine
currently gets wrong or quirky; the listed ``expected`` is the linguistically
correct target, and these become the Phase-2 correctness targets for the V2
``PeriodClassifier`` (the classifier "may FIX load-bearing quirks", plan §0).
A non-xfail entry must pass on the current engine and must keep passing through
the V2 cutover.

Categories covered (V2_RFC_EVALUATION §4): trailing-period abbreviations,
multi-period initialisms (U.S.A., I.B.M.), a.m./p.m., number abbreviations and
the ``??`` placeholder analogue, prepositive starters, adjacent-abbreviation
chains, initials+surname, possessive/standalone ``I``, and decimals/structural
non-abbreviation periods that must stay boundaries-or-not correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CorpusCase:
    text: str
    expected: list[str]
    category: str
    xfail: bool = False  # True => legacy engine currently diverges from `expected`
    note: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


# --- Cases the CURRENT engine already segments correctly (must stay green) ----
_GREEN: list[CorpusCase] = [
    # ---- trailing-period title/abbreviation -> PROTECT, then real boundary ----
    CorpusCase(
        "Dr. Smith went to Washington. He arrived at noon.",
        ["Dr. Smith went to Washington. ", "He arrived at noon."],
        "trailing-title",
    ),
    CorpusCase(
        "Prof. Adams teaches here. Students like him.",
        ["Prof. Adams teaches here. ", "Students like him."],
        "trailing-title",
    ),
    CorpusCase(
        "Mr. and Mrs. Smith arrived. They were late.",
        ["Mr. and Mrs. Smith arrived. ", "They were late."],
        "trailing-title",
    ),
    CorpusCase(
        "Mr. Smith. Mrs. Jones. They came.",
        ["Mr. Smith. ", "Mrs. Jones. ", "They came."],
        "adjacent-title-chain",
    ),
    CorpusCase(
        "He works for Google Inc. and likes it there.",
        ["He works for Google Inc. and likes it there."],
        "trailing-abbr-lowercase-follower",
    ),
    CorpusCase(
        "St. John went to St. Paul. They met.",
        ["St. John went to St. Paul. ", "They met."],
        "saint-vs-street",
    ),
    CorpusCase(
        "Dept. of Defense. It is large.",
        ["Dept. of Defense. ", "It is large."],
        "trailing-abbr",
    ),
    # ---- multi-period initialisms (handled by replace_multi_period_*) ----
    CorpusCase(
        "The U.S.A. is large. Canada is to the north.",
        ["The U.S.A. is large. ", "Canada is to the north."],
        "multi-period-initialism",
    ),
    CorpusCase(
        "I.B.M. makes computers. Apple does too.",
        ["I.B.M. makes computers. ", "Apple does too."],
        "multi-period-initialism",
    ),
    CorpusCase(
        "Visit Washington D.C. tomorrow. It is nice.",
        ["Visit Washington D.C. tomorrow. ", "It is nice."],
        "multi-period-initialism",
    ),
    CorpusCase(
        "The U.N. Secretary-General spoke. He was clear.",
        ["The U.N. Secretary-General spoke. ", "He was clear."],
        "always-join-initialism",
    ),
    CorpusCase(
        "The U.S. Department of State. It is huge.",
        ["The U.S. Department of State. ", "It is huge."],
        "always-join-initialism",
    ),
    # ---- a.m./p.m. ----
    CorpusCase(
        "He arrived at 3 p.m. The meeting started.",
        ["He arrived at 3 p.m. ", "The meeting started."],
        "ampm-boundary",
    ),
    CorpusCase(
        "She left at 10 a.m. and came back later.",
        ["She left at 10 a.m. and came back later."],
        "ampm-lowercase-follower",
    ),
    CorpusCase(
        "They met at 5 p.m., then left.",
        ["They met at 5 p.m., then left."],
        "ampm-comma-follower",
    ),
    CorpusCase(
        "The meeting ran from 9 a.m. to noon.",
        ["The meeting ran from 9 a.m. to noon."],
        "ampm-lowercase-follower",
    ),
    # ---- number abbreviations ----
    CorpusCase(
        "See No. 5 for details.",
        ["See No. 5 for details."],
        "number-abbr-digit",
    ),
    CorpusCase(
        "The No. 1 choice. It won.",
        ["The No. 1 choice. ", "It won."],
        "number-abbr-digit",
    ),
    CorpusCase(
        "Fig. 3 shows the data. It is clear.",
        ["Fig. 3 shows the data. ", "It is clear."],
        "number-abbr-digit",
    ),
    CorpusCase(
        "Vol. IV is here. Read it.",
        ["Vol. IV is here. ", "Read it."],
        "number-abbr-roman",
    ),
    CorpusCase(
        "The meeting is at p. 5. Please read it.",
        ["The meeting is at p. 5. ", "Please read it."],
        "number-abbr-digit",
    ),
    CorpusCase(
        "According to the report (see p. 17), sales rose.",
        ["According to the report (see p. 17), sales rose."],
        "number-abbr-paren",
    ),
    CorpusCase(
        "Read pp. 5-10. Then stop.",
        ["Read pp. 5-10. ", "Then stop."],
        "number-abbr-range",
    ),
    CorpusCase(
        "See Sec. 12 and Art. 3. They apply.",
        ["See Sec. 12 and Art. 3. ", "They apply."],
        "number-abbr-chain",
    ),
    # ---- number-abbr "??" placeholder analogue ----
    CorpusCase(
        "See No. ?? for details.",
        ["See No. ?? for details."],
        "number-abbr-placeholder",
        note="`No. ??` exercises the &ᓷ&&ᓷ& placeholder injection (PLACEHOLDER decision).",
    ),
    CorpusCase(
        "Vol. ?? is missing from the shelf.",
        ["Vol. ?? is missing from the shelf."],
        "number-abbr-placeholder",
    ),
    # ---- prepositive ----
    CorpusCase(
        "It happened in Dec. The year ended.",
        ["It happened in Dec. ", "The year ended."],
        "prepositive-month-boundary",
    ),
    # ---- lowercase abbreviations e.g./i.e./etc./a.k.a. ----
    CorpusCase(
        "e.g. this example. And another.",
        ["e.g. this example. ", "And another."],
        "lowercase-multiperiod",
    ),
    CorpusCase(
        "We use i.e. the right one. Got it.",
        ["We use i.e. the right one. ", "Got it."],
        "lowercase-multiperiod",
    ),
    CorpusCase(
        "etc. and so on. The list ended.",
        ["etc. and so on. ", "The list ended."],
        "lowercase-abbr",
    ),
    CorpusCase(
        "a.k.a. the nickname. It stuck.",
        ["a.k.a. the nickname. ", "It stuck."],
        "lowercase-multiperiod",
    ),
    CorpusCase(
        "The Ph.D. program. It is hard.",
        ["The Ph.D. program. ", "It is hard."],
        "mixed-multiperiod",
    ),
    # ---- initials + surname ----
    CorpusCase(
        "F. J. Garcia signed the form. It was approved.",
        ["F. J. Garcia signed the form. ", "It was approved."],
        "initials-surname",
    ),
    # ---- decimals / possessive / standalone I (must NOT mis-protect) ----
    CorpusCase(
        "The price was $4.50 for the item. It sold out.",
        ["The price was $4.50 for the item. ", "It sold out."],
        "decimal-not-abbr",
    ),
    CorpusCase(
        "I went home. I am tired.",
        ["I went home. ", "I am tired."],
        "standalone-I",
    ),
    CorpusCase(
        "He said I. The end.",
        ["He said I. ", "The end."],
        "standalone-I",
    ),
    CorpusCase(
        "No. The answer is no.",
        ["No. ", "The answer is no."],
        "number-abbr-as-sentence",
        note="`No.` followed by a capital word (not a digit) is a real boundary.",
    ),
    CorpusCase(
        "We met at 10 a.m. Monday morning.",
        ["We met at 10 a.m. ", "Monday morning."],
        "ampm-capital-follower",
    ),
    # ---- titled-name prefix / timezone unit (Phase-3 fixes, promoted from xfail) -
    CorpusCase(
        "Ph.D. Smith arrived. He lectured.",
        ["Ph.D. Smith arrived. ", "He lectured."],
        "initialism-before-name",
        note=(
            "'Ph.D. Smith' is a titled name and stays joined: a degree/title "
            "abbreviation in name-prefix position keeps its final period "
            "non-terminal before a capitalized surname."
        ),
    ),
    CorpusCase(
        "Dr. Ph.D. Smith spoke at noon.",
        ["Dr. Ph.D. Smith spoke at noon."],
        "initialism-before-name",
        note="Title chain 'Dr. Ph.D.' prefixes the surname 'Smith'; one sentence.",
    ),
    CorpusCase(
        "It is 9 a.m. Eastern Standard Time now.",
        ["It is 9 a.m. Eastern Standard Time now."],
        "ampm-timezone",
        note=(
            "'9 a.m. Eastern Standard Time' is one time unit: a spelled-out "
            "timezone name after a.m./p.m. is recognized by the ampm zone guard."
        ),
    ),
]


# --- Cases the LEGACY engine currently gets WRONG (Phase-2 correctness targets) -
# `expected` is the linguistically-correct target; xfail=True marks the divergence.
# The three original Phase-2 targets (Ph.D.-surname titled name, the Dr.+Ph.D.
# title chain, and the "9 a.m. Eastern Standard Time" timezone unit) were fixed in
# Phase 3 (downstream multi-period / a.m.-p.m. passes) and promoted to _GREEN.
_XFAIL: list[CorpusCase] = []


CORPUS: list[CorpusCase] = _GREEN + _XFAIL


def green_cases() -> list[CorpusCase]:
    return [c for c in CORPUS if not c.xfail]


def xfail_cases() -> list[CorpusCase]:
    return [c for c in CORPUS if c.xfail]
