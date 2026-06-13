"""Regression test for German standalone-"I" boundary handling.

Finding 8 (pre-release review): ``sentencesplit/lang/deutsch.py`` carried a
``if self.RESTORE_STANDALONE_I_BOUNDARIES: ...`` branch in its
``AbbreviationReplacer.replace()`` override, but German never sets that flag
``True`` (only english / en_legal / en_es_zh do), so the branch was permanently
dead. ``I`` is not a German pronoun, so restoring standalone-``I`` boundaries is
inapplicable to German.

This is a characterization test: it pins the intended German behavior so that
removing the dead branch is provably output-preserving. German must NOT split a
standalone ``I`` boundary.
"""

import pytest

from sentencesplit.languages import LANGUAGE_CODES
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


def test_german_restore_standalone_i_flag_is_disabled():
    # The standalone-"I" restoration must remain inapplicable to German; the
    # base default is False and German must not flip it on.
    assert LANGUAGE_CODES["de"].AbbreviationReplacer.RESTORE_STANDALONE_I_BOUNDARIES is False
