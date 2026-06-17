# -*- coding: utf-8 -*-
"""Regression: STARTER_AWARE prepositive boundaries are decided per occurrence.

en_legal's court abbreviations (``Cir.``, ``Bankr.``, ...) are *starter-aware*
prepositives: in ``aggressive`` mode the boundary decision depends on the
per-occurrence follower (``_follower_is_likely_sentence_start``) — "Cir. held"
joins, "Cir. The" splits.

The V2 PeriodClassifier realizes a PROTECT decision GLOBALLY per (abbr, follower)
unit by re-anchoring a follower-independent suffix (``\\.(?=(\\s|:\\d+))``). For a
position-dependent starter-aware decision that is wrong: a single joined "Cir."
on a line re-protected EVERY other "Cir. <whitespace>" on that line, so a sibling
occurrence that should end a sentence was wrongly merged. ``en_legal`` now uses an
``AbbrPolicy(realize_per_occurrence=True)`` so each occurrence is anchored to its
own period from its own context (matching the pre-V2 per-match ``re.sub`` callback).
"""

import pytest

from sentencesplit import Segmenter


@pytest.fixture(scope="module")
def seg() -> Segmenter:
    return Segmenter("en_legal", split_mode="aggressive")


@pytest.mark.parametrize(
    "text,expected",
    [
        # Two "Cir." on one line: the first joins (lowercase "held"), the second
        # ends the sentence (capital "The"). The global-realization bug merged the
        # whole line into one segment by re-protecting the second "Cir." too.
        (
            "The 9th Cir. held the 2nd Cir. The panel reversed.",
            ["The 9th Cir. held the 2nd Cir. ", "The panel reversed."],
        ),
        # Single starter-aware occurrence before a capital still splits.
        (
            "The 9th Cir. The panel reversed.",
            ["The 9th Cir. ", "The panel reversed."],
        ),
        # Single starter-aware occurrence before a lowercase word still joins.
        (
            "The 9th Cir. held today.",
            ["The 9th Cir. held today."],
        ),
    ],
)
def test_starter_aware_decided_per_occurrence(seg: Segmenter, text: str, expected: list[str]) -> None:
    assert seg.segment(text) == expected
