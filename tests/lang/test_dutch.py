# -*- coding: utf-8 -*-
import pytest

from tests.helpers import assert_segments

GOLDEN_NL_RULES_TEST_CASES = [
    (
        "Hij schoot op de JP8-brandstof toen de Surface-to-Air (sam)-missiles op hem af kwamen. 81 procent van de schoten was raak.",
        [
            "Hij schoot op de JP8-brandstof toen de Surface-to-Air (sam)-missiles op hem af kwamen.",
            "81 procent van de schoten was raak.",
        ],
    ),
    (
        "81 procent van de schoten was raak. ...en toen barste de hel los.",
        ["81 procent van de schoten was raak.", "...en toen barste de hel los."],
    ),
    ("Afkorting aanw. vnw.", ["Afkorting aanw. vnw."]),
    ("Zie deelw. voorbeeld. Daarna klaar.", ["Zie deelw. voorbeeld.", "Daarna klaar."]),
    ("Volgens art. 5 geldt dit. Daarna volgt uitleg.", ["Volgens art. 5 geldt dit.", "Daarna volgt uitleg."]),
    ("Zie blz. 10 voor details. Daarna verder.", ["Zie blz. 10 voor details.", "Daarna verder."]),
    ("Dit is d.w.z. een voorbeeld. Daarna volgt uitleg.", ["Dit is d.w.z. een voorbeeld.", "Daarna volgt uitleg."]),
    ("Lees aant. bij het artikel. Daarna verder.", ["Lees aant. bij het artikel.", "Daarna verder."]),
    ("Zie nr. 12 in het rapport. Daarna volgt tekst.", ["Zie nr. 12 in het rapport.", "Daarna volgt tekst."]),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_NL_RULES_TEST_CASES)
def test_nl_sbd(nl_default_fixture, text, expected_sents):
    """Dutch language SBD tests"""
    assert_segments(nl_default_fixture, text, expected_sents)
