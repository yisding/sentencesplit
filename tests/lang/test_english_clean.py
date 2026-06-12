# -*- coding: utf-8 -*-
import pytest

import sentencesplit
from tests.data.lang.english_clean import TESTS_WITH_CLEAN, TESTS_WO_CLEAN
from tests.helpers import assert_segments


@pytest.mark.parametrize("text,expected_sents", TESTS_WITH_CLEAN)
def test_en_sbd_with_clean(en_with_clean_no_span_fixture, text, expected_sents):
    """SBD tests from Pragmatic Segmenter needs clean:true"""
    assert_segments(en_with_clean_no_span_fixture, text, expected_sents)


@pytest.mark.parametrize("text,expected_sents", TESTS_WO_CLEAN)
def test_en_sbd_wo_clean(text, expected_sents):
    """SBD tests from Pragmatic Segmenter without clean:true"""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert_segments(seg, text, expected_sents)
