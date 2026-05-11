# -*- coding: utf-8 -*-
import pytest

GOLDEN_FA_RULES_TEST_CASES = [
    ("خوشبختم، آقای رضا. شما کجایی هستید؟ من از تهران هستم.", ["خوشبختم، آقای رضا.", "شما کجایی هستید؟", "من از تهران هستم."])
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_FA_RULES_TEST_CASES)
def test_fa_sbd(fa_default_fixture, text, expected_sents):
    """Persian language SBD tests"""
    segments = fa_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


def test_fa_handles_embedded_english_abbreviation(fa_default_fixture):
    """An English honorific in Persian text must not split inside `Dr.`.

    Exercises the Persian-specific AbbreviationReplacer.scan_for_replacements
    override, which protects the period after each registered abbreviation
    (`dr`, `mr`, etc., inherited from Standard) by substituting it with a
    placeholder before sentence boundary detection runs.
    """
    text = "He met Dr. Smith. آنها صحبت کردند."
    segments = fa_default_fixture.segment(text)
    assert segments == ["He met Dr. Smith. ", "آنها صحبت کردند."]
