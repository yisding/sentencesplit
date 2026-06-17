# -*- coding: utf-8 -*-
"""Regression: titled-name prefix and spelled-out a.m./p.m. timezone unit.

These three boundaries are owned by the abbreviation passes that run AFTER the
PeriodClassifier:

* ``replace_multi_period_abbreviations`` — a degree/title abbreviation such as
  "Ph.D." in *name-prefix* position (opening the line, or itself preceded only
  by another protected title like "Dr.") prefixes a capitalized surname, so its
  final period is a name-internal separator, not a sentence boundary. A trailing
  degree ("She earned a Ph.D. Smith advised her.") still splits, and a pure
  all-caps initialism ("A.S.E. Ackermann") still follows the split-mode dial.
* the a.m./p.m. boundary rules — a spelled-out timezone name ("Eastern Standard
  Time", "Pacific Time") after "<num> a.m./p.m." is part of the time unit, so the
  boundary-restore is suppressed just as it already is for "p.m. EST". An ordinary
  capitalized sentence start ("9 a.m. The meeting started.") still splits.
"""

import pytest

from sentencesplit import Segmenter


@pytest.fixture(scope="module")
def seg() -> Segmenter:
    return Segmenter("en")


@pytest.mark.parametrize(
    "text,expected",
    [
        # A: titled name "Ph.D. Smith" stays joined; the real boundary follows.
        (
            "Ph.D. Smith arrived. He lectured.",
            ["Ph.D. Smith arrived. ", "He lectured."],
        ),
        # B: title chain "Dr. Ph.D." prefixes the surname; one sentence.
        (
            "Dr. Ph.D. Smith spoke at noon.",
            ["Dr. Ph.D. Smith spoke at noon."],
        ),
        # C: spelled-out timezone after a.m. is one time unit.
        (
            "It is 9 a.m. Eastern Standard Time now.",
            ["It is 9 a.m. Eastern Standard Time now."],
        ),
        (
            "The webinar starts at 2 p.m. Pacific Time and ends at four.",
            ["The webinar starts at 2 p.m. Pacific Time and ends at four."],
        ),
    ],
)
def test_titled_name_and_timezone_units_stay_joined(seg, text, expected):
    assert seg.segment(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        # Trailing degree (not a name prefix) still splits before a new subject.
        (
            "She earned a Ph.D. Smith advised her.",
            ["She earned a Ph.D. ", "Smith advised her."],
        ),
        # Pure all-caps 3-part initialism still follows the split-mode dial.
        (
            "A.S.E. Ackermann and team published the findings in 2007.",
            ["A.S.E. ", "Ackermann and team published the findings in 2007."],
        ),
        # Multi-period abbr before a genuine new sentence still splits.
        (
            "His Ph.D. The committee met.",
            ["His Ph.D. ", "The committee met."],
        ),
        # a.m. before an ordinary capitalized sentence start still splits.
        (
            "It is 9 a.m. The meeting started.",
            ["It is 9 a.m. ", "The meeting started."],
        ),
        # a.m. before a non-timezone all-caps acronym still splits.
        (
            "The launch was at 3 p.m. NASA broadcast it live.",
            ["The launch was at 3 p.m. ", "NASA broadcast it live."],
        ),
    ],
)
def test_real_boundaries_after_abbreviation_still_split(seg, text, expected):
    assert seg.segment(text) == expected


# ``NAME_TITLE_PREFIX_ABBREVIATIONS`` is the English-honorific default for the
# shared title-prefix heuristic and lives on the base ``AbbreviationReplacer``;
# every Latin-script language inherits it by class inheritance (no language
# overrides it today). These parametrized cases pin that cross-language
# inheritance contract so an accidental change to which languages treat which
# tokens as title prefixes is caught: the title chain "Dr. Ph.D. Smith" must
# stay joined, while a trailing degree "Ph.D." (not a name prefix) must still
# split, for every Latin-script language plus the en_legal profile.
@pytest.mark.parametrize("language", ["en", "es", "fr", "it", "de", "en_legal"])
@pytest.mark.parametrize(
    "text,expected",
    [
        # Title chain stays joined (Dr. + degree prefixing a surname).
        (
            "Dr. Ph.D. Smith spoke at noon.",
            ["Dr. Ph.D. Smith spoke at noon."],
        ),
        # Trailing degree (not a name prefix) still splits before a new subject.
        (
            "She earned a Ph.D. Smith advised her.",
            ["She earned a Ph.D. ", "Smith advised her."],
        ),
    ],
)
def test_title_prefix_default_inherited_across_latin_languages(language, text, expected):
    assert Segmenter(language).segment(text) == expected
