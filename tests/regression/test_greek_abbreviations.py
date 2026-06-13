# -*- coding: utf-8 -*-
"""Regression tests for Greek abbreviation handling.

Greek previously inherited the English (Standard) abbreviation list, so common
Greek multi-period abbreviations such as ``μ.Χ.`` (A.D.) and ``Ε.Ε.`` (E.U.)
were not recognised. The internal periods were treated as sentence boundaries,
shattering e.g. ``Το 49 μ.Χ.`` into ``Το 49 μ.`` + ``Χ.``.
"""

import pytest

import sentencesplit

GREEK_ABBREVIATION_CASES = [
    (
        "case_0056",
        "Το 49 μ.Χ. ο Απόστολος Παύλος ίδρυσε εδώ την πρώτη εκκλησία του Χριστού στην Ευρώπη.",
        ["Το 49 μ.Χ. ο Απόστολος Παύλος ίδρυσε εδώ την πρώτη εκκλησία του Χριστού στην Ευρώπη."],
    ),
    (
        "case_0017",
        "Ο πρόεδρος, ο οποίος από τη Σύνοδο Ε.Ε. - ΗΠΑ στην Πράγα μίλησε για έναν κόσμο χωρίς πυρηνικά.",
        ["Ο πρόεδρος, ο οποίος από τη Σύνοδο Ε.Ε. - ΗΠΑ στην Πράγα μίλησε για έναν κόσμο χωρίς πυρηνικά."],
    ),
    (
        "pi_chi",
        "Γεννήθηκε το 480 π.Χ. στην Αθήνα.",
        ["Γεννήθηκε το 480 π.Χ. στην Αθήνα."],
    ),
]


@pytest.mark.parametrize("case_id,text,expected", GREEK_ABBREVIATION_CASES)
def test_greek_multi_period_abbreviations(case_id, text, expected):
    seg = sentencesplit.Segmenter(language="el")
    assert [s.strip() for s in seg.segment(text)] == expected


# A Greek multi-period abbreviation whose final period is followed by a Greek
# CAPITAL letter is a genuine sentence boundary: Greek (unlike German) does not
# capitalize common nouns mid-sentence, so a capital after "π.Χ. " reliably marks
# a new sentence. The internal periods stay protected; only the final one splits.
GREEK_ABBREVIATION_BOUNDARY_CASES = [
    (
        "pi_chi_capital",
        "Έζησε το 480 π.Χ. Ήταν σοφός.",
        ["Έζησε το 480 π.Χ.", "Ήταν σοφός."],
    ),
    (
        "mu_chi_capital",
        "Συνέβη το 49 μ.Χ. Όλοι το θυμούνται.",
        ["Συνέβη το 49 μ.Χ.", "Όλοι το θυμούνται."],
    ),
    (
        "ee_capital",
        "Είναι μέλος της Ε.Ε. Η χώρα ευημερεί.",
        ["Είναι μέλος της Ε.Ε.", "Η χώρα ευημερεί."],
    ),
]


@pytest.mark.parametrize("case_id,text,expected", GREEK_ABBREVIATION_BOUNDARY_CASES)
def test_greek_multi_period_abbreviation_boundary_before_capital(case_id, text, expected):
    seg = sentencesplit.Segmenter(language="el")
    assert [s.strip() for s in seg.segment(text)] == expected


GREEK_LATIN_TWO_LETTER_INITIALISM_CASES = [
    (
        "us_embassy",
        "Η U.S. Embassy άνοιξε. Ήταν πρωί.",
        ["Η U.S. Embassy άνοιξε.", "Ήταν πρωί."],
    ),
    (
        "eu_commission",
        "Η E.U. Commission άνοιξε. Ήταν πρωί.",
        ["Η E.U. Commission άνοιξε.", "Ήταν πρωί."],
    ),
]


@pytest.mark.parametrize("case_id,text,expected", GREEK_LATIN_TWO_LETTER_INITIALISM_CASES)
def test_greek_keeps_common_latin_two_letter_initialism_phrases_joined(case_id, text, expected):
    seg = sentencesplit.Segmenter(language="el")
    assert [s.strip() for s in seg.segment(text)] == expected


def test_greek_latin_two_letter_initialism_before_greek_capital_follows_split_mode():
    text = "Είδε την U.S. Ήταν αργά."

    conservative = sentencesplit.Segmenter(language="el", split_mode="conservative")
    assert [s.strip() for s in conservative.segment(text)] == [text]

    for mode in ("balanced", "aggressive"):
        seg = sentencesplit.Segmenter(language="el", split_mode=mode)
        assert [s.strip() for s in seg.segment(text)] == ["Είδε την U.S.", "Ήταν αργά."]
