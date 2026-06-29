# -*- coding: utf-8 -*-
import pytest

import sentencesplit
from tests.helpers import assert_segments

GOLDEN_DA_RULES_TEST_CASES = [
    ("Hej Verden. Mit navn er Jonas.", ["Hej Verden.", "Mit navn er Jonas."]),
    ("Lad os spørge Jane og co. De burde vide det.", ["Lad os spørge Jane og co.", "De burde vide det."]),
    (
        "De lukkede aftalen med Pitt, Briggs & Co. Det lukkede i går.",
        ["De lukkede aftalen med Pitt, Briggs & Co.", "Det lukkede i går."],
    ),
    ("Mød Fru. Jensen i dag. Hun bliver.", ["Mød Fru. Jensen i dag.", "Hun bliver."]),
    ("De holdt Skt. Hans i byen.", ["De holdt Skt. Hans i byen."]),
    ("St. Michael's Kirke er på 5. gade nær ved lyset.", ["St. Michael's Kirke er på 5. gade nær ved lyset."]),
    ("Jeg bor i E.U. Hvad med dig?", ["Jeg bor i E.U.", "Hvad med dig?"]),
    ("I live in the U.S. Hvad med dig?", ["I live in the U.S.", "Hvad med dig?"]),
    ("Han bor i s.u. Det er kendt.", ["Han bor i s.u.", "Det er kendt."]),
    ("Han bor i s.U. Det er kendt.", ["Han bor i s.U.", "Det er kendt."]),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_DA_RULES_TEST_CASES)
def test_da_sbd(da_default_fixture, text, expected_sents):
    """Danish language SBD tests"""
    assert_segments(da_default_fixture, text, expected_sents)


DA_RULES_CLEAN_TEST_CASES = [
    (
        "Hello world.I dag is Tuesday.Hr. Smith went to the store and bought 1,000.That is a lot.",
        ["Hello world.", "I dag is Tuesday.", "Hr. Smith went to the store and bought 1,000.", "That is a lot."],
    ),
    ("It was a cold \nnight in the city.", ["It was a cold night in the city."]),
]

DA_PDF_TEST_DATA = [
    ("This is a sentence\ncut off in the middle because pdf.", ["This is a sentence cut off in the middle because pdf."])
]


@pytest.mark.parametrize("text,expected_sents", DA_RULES_CLEAN_TEST_CASES)
def test_da_sbd_clean(da_with_clean_no_span_fixture, text, expected_sents):
    """Danish language SBD tests with text clean"""
    assert_segments(da_with_clean_no_span_fixture, text, expected_sents)


@pytest.mark.parametrize("text,expected_sents", DA_PDF_TEST_DATA)
def test_da_pdf_type(text, expected_sents):
    """SBD tests from Pragmatic Segmenter for doctype:pdf"""
    seg = sentencesplit.Segmenter(language="da", clean=True, doc_type="pdf")
    assert_segments(seg, text, expected_sents)
