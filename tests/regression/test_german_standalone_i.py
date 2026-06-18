"""Regression test for German standalone-"I" boundary handling.

``I`` is not a German pronoun, so German must NOT restore standalone-``I``
sentence boundaries the way the English family (english / en_legal / en_es_zh)
does — those profiles run a standalone-``I`` restoration stage that German omits.
This pins that language-specific behavior: German keeps "... you and I. ..."
joined where the English family would split after the standalone "I".
"""

import pytest

from sentencesplit.segmenter import Segmenter


@pytest.fixture
def german_segmenter():
    return Segmenter(language="de", clean=False)


def test_german_does_not_restore_standalone_i_boundary(german_segmenter):
    # German keeps "... you and I. Did it work." as a single segment: it does
    # not treat the standalone "I" the way English does (English would split
    # after "I." here). This is the historically-joined result.
    text = "... you and I. Did it work."
    assert german_segmenter.segment(text) == ["... you and I. Did it work."]


def test_german_standalone_i_mid_clause_not_split(german_segmenter):
    text = "He said hi to you and I. Did it work."
    assert german_segmenter.segment(text) == ["He said hi to you and I. Did it work."]


def test_german_normal_sentence_boundary_still_splits(german_segmenter):
    # Sanity check that ordinary German boundaries are unaffected.
    text = "Karl und ich. Es hat funktioniert."
    assert german_segmenter.segment(text) == ["Karl und ich. ", "Es hat funktioniert."]
