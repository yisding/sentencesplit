# -*- coding: utf-8 -*-
"""Regression: abbreviation protection must be order-independent on a single line.

The ``PeriodClassifier`` deduplicates candidates to ONE representative per
``(am_lower, follower_char)`` key and then realizes the representative's decision
GLOBALLY over the line. ``follower_char`` is populated only for the ``". "``
(period + ASCII space) case; every other real follower — an immediate non-space
follower (``inc.)``, ``inc.x``) or a non-ASCII / other-whitespace follower
(``inc.\xa0``, ``inc.\t``) — collapses to ``follower_char == ""``. So two
occurrences of the SAME abbreviation with genuinely DIFFERENT real followers
shared one dedup key, and only the FIRST (the representative) was classified.

When the representative was a BOUNDARY (e.g. ``(see inc.)`` — immediate ``)``
follower, classified BOUNDARY by the regular branch) the global realization was
skipped entirely, so a colliding sibling that should have PROTECTed (e.g.
``inc.\xa0bob`` — a whitespace follower) was dropped and the line split between
``inc.`` and its follower. Swapping the clause order made the protecting
occurrence the representative instead, so the SAME line segmented differently
depending on the order of its clauses — an order-dependence bug.

The fix widens the dedup key with a structural follower-class discriminator
(immediate non-space / ASCII-space / other-whitespace / end-of-line) so distinct
real followers no longer collide; each is classified on its own period and the
decision is order-independent.
"""

from __future__ import annotations

import pytest

import sentencesplit
from sentencesplit.languages import Language

# A boundary-producing occurrence ``(see inc.)`` and a protect-producing
# occurrence (``inc.<ws>bob``) of the SAME abbr, with DIFFERENT real followers,
# on ONE line. Both ``inc.`` tokens are space-prefixed so the word-boundary
# match_re enumerates them ( a ``(``-prefixed inc is NOT enumerated). ``A`` puts
# the BOUNDARY occurrence first (it would become the representative); ``B`` puts
# the PROTECT occurrence first.
DECOY_NBSP_A = "(see inc.) and inc.\xa0bob filed."  # boundary-rep first
DECOY_NBSP_B = "inc.\xa0bob filed and (see inc.) too."  # protect-rep first
DECOY_TAB_A = "(see inc.) and inc.\tbob filed."  # follower-class 'W' (tab)
DECOY_TAB_B = "inc.\tbob filed and (see inc.) too."


def _seg():
    return sentencesplit.Segmenter(language="en")  # default split_mode='balanced'


@pytest.mark.parametrize(
    ("ws_a", "ws_b"),
    [(DECOY_NBSP_A, DECOY_NBSP_B), (DECOY_TAB_A, DECOY_TAB_B)],
)
def test_segment_is_order_independent(ws_a: str, ws_b: str) -> None:
    seg = _seg()
    segs_a = seg.segment(ws_a)
    segs_b = seg.segment(ws_b)
    # Order-independence: the two orderings of the SAME clauses produce the same
    # number of segments, and neither splits between "inc." and its follower.
    assert len(segs_a) == len(segs_b)
    for segs in (segs_a, segs_b):
        # No segment may END at the protected period (i.e. split inc. -> follower).
        assert not any(s.endswith("inc.") or s.rstrip().endswith("inc.") for s in segs), segs


@pytest.mark.parametrize("text", [DECOY_NBSP_A, DECOY_NBSP_B, DECOY_TAB_A, DECOY_TAB_B])
def test_whitespace_followed_abbr_is_protected(text: str) -> None:
    seg = _seg()
    segs = seg.segment(text)
    # The whitespace-followed "inc.<ws>bob" stays intact inside ONE segment: no
    # boundary falls between "inc." and "bob".
    joined = "".join(segs)
    assert "inc.\xa0bob" in joined or "inc.\tbob" in joined
    # And it is not split: every "inc.<ws>bob" run lives wholly within a segment.
    target = "inc.\xa0bob" if "\xa0" in text else "inc.\tbob"
    assert any(target in s for s in segs), segs


@pytest.mark.parametrize(
    ("text_a", "text_b"),
    [(DECOY_NBSP_A, DECOY_NBSP_B), (DECOY_TAB_A, DECOY_TAB_B)],
)
def test_classifier_rewrite_order_independent(text_a: str, text_b: str) -> None:
    """Sharper: pin the mechanism at the classifier level.

    The whitespace-followed period must become the ``∯`` sentinel in BOTH
    orderings (the boundary-producing ``(see inc.)`` occurrence keeps its ``.``).
    """
    lang = Language.get_language_code("en")
    rep = lang.AbbreviationReplacer("", lang, split_mode="balanced")
    pc = rep._period_classifier()
    out_a = pc.rewrite(text_a)
    out_b = pc.rewrite(text_b)
    # The whitespace-followed occurrence protects in BOTH orderings.
    assert "inc∯" in out_a, out_a
    assert "inc∯" in out_b, out_b
    # The bracketed occurrence stays a boundary in both (period unchanged there).
    assert "(see inc.)" in out_a
    assert "(see inc.)" in out_b


def test_german_global_realization_deduplicates_identical_suffix_decisions() -> None:
    """German must not rescan the same abbr/suffix decision for each follower.

    DE_POLICY protects every known abbreviation period before whitespace with a
    constant suffix, so many distinct follower chars still share one global
    realization. Re-realizing each candidate would materialize O(n²) duplicate
    edits before rewrite-time deduplication.
    """
    lang = Language.get_language_code("de")
    rep = lang.AbbreviationReplacer("", lang, split_mode="balanced")
    pc = rep._period_classifier()
    text = " ".join(f"Dr. {chr(0x4E00 + i)}" for i in range(80))

    assert len(pc.enumerate_candidates(text)) == 80
    edits = pc._collect_edits(text)

    assert len(edits) == 80
    assert len({edit.start for edit in edits}) == 80
