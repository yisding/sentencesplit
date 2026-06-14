# -*- coding: utf-8 -*-
"""Curated English correctness-corpus gate for the V2 abbreviation engine.

GREEN cases (``green_cases()``) assert the current AND future engine produce the
linguistically-correct segmentation — they must stay green at every commit.

XFAIL cases (``xfail_cases()``) are Phase-2 correctness targets: the legacy
engine currently diverges from the labeled correct expectation. They are marked
``strict=True`` so that when the V2 ``PeriodClassifier`` FIXES one, the xfail
turns into an XPASS and the suite goes red — forcing the entry to be promoted to
GREEN (i.e. the fix is acknowledged and locked in, never silently regressed).
"""

from __future__ import annotations

import pytest

from sentencesplit import Segmenter
from tests.v2.corpus_en import green_cases, xfail_cases


@pytest.fixture(scope="module")
def seg() -> Segmenter:
    return Segmenter("en")


@pytest.mark.parametrize("case", green_cases(), ids=lambda c: c.text)
def test_corpus_en_green(seg: Segmenter, case) -> None:
    assert seg.segment(case.text) == case.expected, case.note or case.category


@pytest.mark.skipif(
    not xfail_cases(),
    reason="no Phase-2 xfail targets left (all promoted to GREEN); see corpus_en.py for the strict-xfail promotion mechanism",
)
@pytest.mark.parametrize("case", xfail_cases(), ids=lambda c: c.text)
def test_corpus_en_xfail(seg: Segmenter, case) -> None:
    # strict xfail: a fix that makes this pass is intentional and must be
    # promoted to a GREEN case (the suite goes red on the unexpected XPASS).
    pytest.xfail(reason=case.note or f"Phase-2 correctness target: {case.category}")
    assert seg.segment(case.text) == case.expected
