# -*- coding: utf-8 -*-
import pytest

from tests.helpers import assert_segments

GOLDEN_SK_RULES_TEST_CASES = [
    (
        "Ide o majiteľov firmy ABTrade s. r. o., ktorí stoja aj za ďalšími spoločnosťami, napr. XYZCorp a.s.",
        ["Ide o majiteľov firmy ABTrade s. r. o., ktorí stoja aj za ďalšími spoločnosťami, napr. XYZCorp a.s."],
    ),
    (
        "„Prieskumy beriem na ľahkú váhu. V podstate ma to nezaujíma,“ reagoval Matovič na prieskum agentúry Focus.",
        ["„Prieskumy beriem na ľahkú váhu. V podstate ma to nezaujíma,“ reagoval Matovič na prieskum agentúry Focus."],
    ),
    ("Toto sa mi podarilo až na 10. pokus, ale stálo to za to.", ["Toto sa mi podarilo až na 10. pokus, ale stálo to za to."]),
    ("Ide o príslušníkov XII. Pluku špeciálneho určenia.", ["Ide o príslušníkov XII. Pluku špeciálneho určenia."]),
    (
        "Spoločnosť bola založená 7. Apríla 2020, na zmluve však figuruje dátum 20. marec 2020.",
        ["Spoločnosť bola založená 7. Apríla 2020, na zmluve však figuruje dátum 20. marec 2020."],
    ),
    (
        "Používame .NET Framework. Funguje to.",
        ["Používame .NET Framework.", "Funguje to."],
    ),
    ("Stretli sme sa s prof. Novákom. Potom odišiel.", ["Stretli sme sa s prof. Novákom.", "Potom odišiel."]),
    ("Pozri zák. č. 40/1964 Z. z. Platí dodnes.", ["Pozri zák. č. 40/1964 Z. z.", "Platí dodnes."]),
    (
        "Firma ABC s. r. o. vznikla v roku 2020. Pokračuje ďalej.",
        ["Firma ABC s. r. o. vznikla v roku 2020.", "Pokračuje ďalej."],
    ),
    ("Čakali sme do 5. mája 2024. Potom prišla odpoveď.", ["Čakali sme do 5. mája 2024.", "Potom prišla odpoveď."]),
    ("Na IV. poschodí je kancelária. Dvere sú otvorené.", ["Na IV. poschodí je kancelária.", "Dvere sú otvorené."]),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_SK_RULES_TEST_CASES)
def test_sk_sbd(sk_default_fixture, text, expected_sents):
    """Slovak language SBD tests"""
    assert_segments(sk_default_fixture, text, expected_sents)
