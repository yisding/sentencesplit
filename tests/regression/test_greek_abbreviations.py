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
