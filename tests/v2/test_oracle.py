# -*- coding: utf-8 -*-
"""Self-tests for the differential oracle (the debugging aid, not a gate).

The legacy per-line protection engine was deleted at the Phase-6 cutover, so the
oracle's ``legacy`` side is now a FROZEN snapshot (captured while that engine was
still live). These tests assert the oracle's *mechanics*: that the frozen
snapshot's offsets are all real ``.`` characters, that the known length-changing
``??`` placeholder case aligns on the classifier side, that multi-line input maps
offsets correctly, that an input absent from the snapshot fails loudly, and that
the V2 classifier reproduces the historical legacy output for the known-good
English corpus.
"""

from __future__ import annotations

import pytest

from tests.v2.oracle import (
    ClassifierUnavailable,
    classifier_protect_positions,
    diff_positions,
    legacy_protect_positions,
)


def test_legacy_positions_are_real_periods() -> None:
    text = "Dr. Smith met Sen. Jones. The U.S. agreed."
    positions = legacy_protect_positions(text, "en")
    assert positions  # Dr. and Sen. periods are protected by the per-line step
    for p in positions:
        assert text[p] == ".", f"position {p} is not a period in {text!r}"


def test_legacy_excludes_later_pass_decisions() -> None:
    # U.S.A. is handled by replace_multi_period_abbreviations (a later pass), not
    # the per-line protection step the oracle measures, so it reports nothing here.
    assert legacy_protect_positions("The U.S.A. is large.", "en") == []


def test_placeholder_alignment_resyncs() -> None:
    # "No. ??" -> "No∯ &ᓷ&&ᓷ&": the protected period precedes a length-changing
    # placeholder expansion; the protected offset must still point at the '.'.
    # Asserted on the classifier side (the live path that does the resync).
    text = "See No. ?? for details."
    positions = classifier_protect_positions(text, "en")
    assert positions == [text.index("No.") + 2]
    # ...and it matches the frozen legacy snapshot.
    assert legacy_protect_positions(text, "en") == positions


def test_multiline_offsets_map_to_original() -> None:
    text = "Line one with etc. trailing.\nLine two has Dr. Adams here."
    positions = classifier_protect_positions(text, "en")
    for p in positions:
        assert text[p] == "."
    assert positions == [text.index("etc.") + 3, text.index("Dr.") + 2]
    assert legacy_protect_positions(text, "en") == positions


_CROSS_LANG_SAMPLES = {
    "en": "Dr. Smith met Sen. Jones. The U.S. agreed.",
    "en_legal": "See Bankr. Court. The 9th Cir. reversed. Cf. id. at 5.",
    "de": "Das ist z.B. wichtig. Hr. Müller kam am 5. Mai.",
    "ru": "Это рус. Большой текст. См. рис. 3 ниже.",
    "sk": "To je napr. dôležité. Pán Dr. Novák prišiel.",
    "bg": "Това е напр. важно. Г-н Иванов дойде.",
    "ar": "هذا مثل ذلك. وهكذا.",
    "fr": "C'est M. Dupont. Voir p. 5 svp.",
    "it": "Il Sig. Rossi è qui. Vedi p. 10.",
    "zh": "这是中文。Dr. Smith 来了。",
    "kk": "Бұл мысалы. Қараңыз 5-бет.",
    "nl": "Dhr. Jansen kwam. Zie blz. 3.",
}


@pytest.mark.parametrize("code", sorted(_CROSS_LANG_SAMPLES))
def test_oracle_offsets_are_periods_across_languages(code: str) -> None:
    # Every offset on BOTH sides (frozen legacy snapshot + live classifier) must
    # point at a real '.'; a non-period offset would mean a silent alignment bug.
    # Equality is deliberately NOT required here — the oracle exists to *surface*
    # adjudicated divergences (e.g. V2 fixes the bg/ru unescaped-lookbehind quirk
    # by protecting напр./См. that the buggy legacy path missed), not freeze them.
    text = _CROSS_LANG_SAMPLES[code]
    for p in legacy_protect_positions(text, code):
        assert text[p] == ".", f"frozen-legacy position {p} is not a period in {text!r}"
    for p in classifier_protect_positions(text, code):
        assert text[p] == ".", f"classifier position {p} is not a period in {text!r}"


def test_unknown_snapshot_input_raises() -> None:
    # The frozen snapshot is a closed corpus; an input that was never captured
    # must fail loudly rather than silently return [] (which would masquerade as
    # "the legacy engine protected nothing here").
    with pytest.raises(KeyError):
        legacy_protect_positions("A brand new sentence never snapshotted. Etc.", "en")
    with pytest.raises(KeyError):
        diff_positions("A brand new sentence never snapshotted. Etc.", "en")


def test_classifier_available_and_at_parity_for_kazakh() -> None:
    # Kazakh rides the V2 classifier with KK_POLICY. Its single-token abbreviations
    # are now stored dotless (the automaton enumerates them directly), so the
    # retired whole-text ``replace_single_period_abbreviations`` pass is gone.
    # KK_POLICY reproduces it byte-for-byte: the formerly-dotted stems are
    # classified against the WIDE Kazakh-Cyrillic + Latin lowercase follower class
    # (so "обл. қала" does NOT split), while every other abbreviation — including
    # the always-dotless "см" in "См. рис." below — falls through to the base
    # ASCII-follower REGULAR branch and is NOT protected, exactly as the legacy
    # pass left it. The frozen legacy positions therefore stay [] and parity holds.
    text = "Бұл мысалы. Қараңыз 5-бет. См. рис. 3 ниже."
    positions = classifier_protect_positions(text, "kk")
    for p in positions:
        assert text[p] == ".", f"position {p} is not a period in {text!r}"
    legacy_only, new_only = diff_positions(text, "kk")
    assert (legacy_only, new_only) == ([], []), f"classifier diverges from legacy for kk: {legacy_only=} {new_only=}"


def test_classifier_unavailable_without_hook() -> None:
    # A replacer that exposes no `classifier_protect_positions_for_line` hook must
    # raise loudly so the debugging-aid oracle never silently no-ops.
    from sentencesplit.lang.kazakh import Kazakh

    replacer_cls = Kazakh.AbbreviationReplacer
    prior = replacer_cls.__dict__.get("classifier_protect_positions_for_line")
    # Shadow the inherited hook with None on this subclass to simulate "no hook".
    replacer_cls.classifier_protect_positions_for_line = None
    try:
        with pytest.raises(ClassifierUnavailable):
            classifier_protect_positions("Бұл мысалы. Қараңыз 5-бет.", "kk")
    finally:
        if prior is None:
            del replacer_cls.classifier_protect_positions_for_line
        else:
            replacer_cls.classifier_protect_positions_for_line = prior


@pytest.mark.parametrize("code", ["en", "en_legal"])
def test_classifier_available_and_at_parity_for_english(code: str) -> None:
    # en/en_legal ride the V2 PeriodClassifier; it must be reachable and, for
    # English (whose legacy output is known-good), produce byte-identical
    # protected positions vs the frozen legacy snapshot (the Phase-2 equality
    # TARGET). A divergence here is a real regression to adjudicate, not noise.
    text = "Dr. Smith met Sen. Jones. See No. 5 and Vol. IV. The 9th Cir. reversed."
    positions = classifier_protect_positions(text, code)
    for p in positions:
        assert text[p] == ".", f"position {p} is not a period in {text!r}"
    legacy_only, new_only = diff_positions(text, code)
    assert (legacy_only, new_only) == ([], []), f"classifier diverges from legacy for {code}: {legacy_only=} {new_only=}"
