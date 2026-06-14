# -*- coding: utf-8 -*-
"""Self-tests for the differential oracle (the debugging aid, not a gate).

These assert the oracle's *mechanics* on the unmodified engine: that
``legacy_protect_positions`` returns original-text offsets that are all real
``.`` characters, that the known length-changing ``??`` placeholder case aligns,
that multi-line input maps offsets correctly, and that the V2 stub fails loudly
until the classifier path lands.
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
    text = "See No. ?? for details."
    positions = legacy_protect_positions(text, "en")
    assert positions == [text.index("No.") + 2]


def test_multiline_offsets_map_to_original() -> None:
    text = "Line one with etc. trailing.\nLine two has Dr. Adams here."
    positions = legacy_protect_positions(text, "en")
    for p in positions:
        assert text[p] == "."
    assert positions == [text.index("etc.") + 3, text.index("Dr.") + 2]


@pytest.mark.parametrize("code", ["en", "en_legal", "de", "ru", "sk", "bg", "ar", "fr", "it", "zh", "kk", "nl"])
def test_oracle_does_not_crash_across_languages(code: str) -> None:
    # The alignment assertion must never fire on these representative inputs; a
    # crash here would mean a silent offset bug, not "no protected positions".
    samples = {
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
    positions = legacy_protect_positions(samples[code], code)
    for p in positions:
        assert samples[code][p] == "."


def test_classifier_unavailable_for_non_opted_languages() -> None:
    # Languages that have NOT opted into the V2 classifier
    # (``USE_PERIOD_CLASSIFIER`` is False/unset) still raise loudly, so the
    # debugging-aid oracle never silently no-ops for a non-migrated language.
    # ``zh`` (Chinese) remains on the legacy path; ``de``/``ru``/``sk``/``bg``/
    # ``ar``/``fa`` opted in at Phase 5.
    with pytest.raises(ClassifierUnavailable):
        classifier_protect_positions("这是中文。Dr. Smith 来了。", "zh")
    with pytest.raises(ClassifierUnavailable):
        diff_positions("这是中文。Dr. Smith 来了。", "zh")


@pytest.mark.parametrize("code", ["en", "en_legal"])
def test_classifier_available_and_at_parity_for_english(code: str) -> None:
    # en/en_legal opted into the V2 PeriodClassifier; it must be reachable and,
    # for English (whose legacy output is known-good), produce byte-identical
    # protected positions vs the legacy per-line step (the Phase-2 equality
    # TARGET). A divergence here is a real regression to adjudicate, not noise.
    text = "Dr. Smith met Sen. Jones. See No. 5 and Vol. IV. The 9th Cir. reversed."
    positions = classifier_protect_positions(text, code)
    for p in positions:
        assert text[p] == ".", f"position {p} is not a period in {text!r}"
    legacy_only, new_only = diff_positions(text, code)
    assert (legacy_only, new_only) == ([], []), f"classifier diverges from legacy for {code}: {legacy_only=} {new_only=}"
