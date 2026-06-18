# -*- coding: utf-8 -*-
"""Curated English abbreviation-boundary correctness-corpus gate.

GREEN cases (``green_cases()``) assert the engine produces the
linguistically-correct segmentation — they must stay green at every commit.

XFAIL cases (``xfail_cases()``) are correctness targets: the engine currently
diverges from the labeled correct expectation. They are marked ``strict=True`` so
that when the ``PeriodClassifier`` FIXES one, the xfail turns into an XPASS and
the suite goes red — forcing the entry to be promoted to GREEN (i.e. the fix is
acknowledged and locked in, never silently regressed).
"""

from __future__ import annotations

import pytest

from sentencesplit import Segmenter
from tests.data.abbreviation_corpus_en import green_cases, xfail_cases


@pytest.fixture(scope="module")
def segmenters() -> dict[str, Segmenter]:
    # Cases declare their own language (en or the en_legal specialization); cache
    # one Segmenter per code so the en_legal-only parity arms can be asserted in
    # the same corpus without re-instantiating per case.
    return {"en": Segmenter("en"), "en_legal": Segmenter("en_legal")}


@pytest.mark.parametrize("case", green_cases(), ids=lambda c: f"{c.lang}:{c.text}")
def test_corpus_en_green(segmenters: dict[str, Segmenter], case) -> None:
    seg = segmenters[case.lang]
    assert seg.segment(case.text) == case.expected, case.note or case.category


def _xfail_params() -> list:
    # Wrap each correctness target in a per-case strict xfail marker rather than
    # calling pytest.xfail() inside the body: the imperative call raises
    # immediately, short-circuiting the assert below so the case could never
    # XPASS and the strict-xfail promotion gate was dead. As a marker the assert
    # actually runs, so a fix that makes the case pass XPASSes and (being strict)
    # turns the suite red, forcing promotion to a GREEN case.
    return [
        pytest.param(
            case,
            marks=pytest.mark.xfail(strict=True, reason=case.note or f"correctness target: {case.category}"),
        )
        for case in xfail_cases()
    ]


@pytest.mark.skipif(
    not xfail_cases(),
    reason="no xfail targets left (all promoted to GREEN); see abbreviation_corpus_en.py for the strict-xfail promotion mechanism",
)
@pytest.mark.parametrize("case", _xfail_params(), ids=lambda c: f"{c.lang}:{c.text}")
def test_corpus_en_xfail(segmenters: dict[str, Segmenter], case) -> None:
    seg = segmenters[case.lang]
    assert seg.segment(case.text) == case.expected
