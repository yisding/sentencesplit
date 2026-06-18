# -*- coding: utf-8 -*-
import pytest

from tests.helpers import assert_segments

GOLDEN_MY_RULES_TEST_CASES = [("ခင္ဗ်ားနာမည္ဘယ္လိုေခၚလဲ။၇ွင္ေနေကာင္းလား။", ["ခင္ဗ်ားနာမည္ဘယ္လိုေခၚလဲ။", "၇ွင္ေနေကာင္းလား။"])]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_MY_RULES_TEST_CASES)
def test_my_sbd(my_default_fixture, text, expected_sents):
    """Burmese language SBD tests"""
    assert_segments(my_default_fixture, text, expected_sents)
