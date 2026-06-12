# -*- coding: utf-8 -*-
import pytest

from tests.helpers import assert_segments

GOLDEN_PL_RULES_TEST_CASES = [
    ("To słowo bałt. jestskrótem.", ["To słowo bałt. jestskrótem."]),
    (
        "W tekście użyto np. prostego przykładu. Potem podano wynik.",
        ["W tekście użyto np. prostego przykładu.", "Potem podano wynik."],
    ),
    ("Ten skrót łac. pozostaje w zdaniu. Drugie zdanie.", ["Ten skrót łac. pozostaje w zdaniu.", "Drugie zdanie."]),
    ("Kupiono chleb, mleko itd. Lista była długa. Koniec.", ["Kupiono chleb, mleko itd.", "Lista była długa.", "Koniec."]),
    ("Wymieniono jabłka, gruszki itp. To wystarczyło.", ["Wymieniono jabłka, gruszki itp.", "To wystarczyło."]),
    ("To forma niem. używana w tekście. Potem koniec.", ["To forma niem. używana w tekście.", "Potem koniec."]),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_PL_RULES_TEST_CASES)
def test_pl_sbd(pl_default_fixture, text, expected_sents):
    """Polish language SBD tests"""
    assert_segments(pl_default_fixture, text, expected_sents)
