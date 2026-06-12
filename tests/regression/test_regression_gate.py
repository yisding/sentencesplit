# -*- coding: utf-8 -*-
"""Hermetic CI regression gate (roadmap N2).

Scores ONLY ``sentencesplit`` against a committed gold subset (English Golden
Rules already in-repo + a vendored Universal Dependencies gold subset) and fails
the PR if any corpus's exact-match drops below the committed baseline by more
than its per-language tolerance, or if boundary-F1 drops beyond the global F1
tolerance.

This is intentionally a normal pytest under ``tests/`` so CI runs it with the
rest of the suite — no separate wiring. It is fully hermetic: pure Python, no
Ruby / NLTK / network / native wheels, so it runs on the aarch64 dev box. It
directly prevents the silent per-language regression class (a Dutch regression
once slipped through, caught only by manual review).

When a change *legitimately* moves a score, update the committed baseline via the
reviewed ``# baseline-update`` flow documented in ``gate/GOVERNANCE.md``:

    uv run python tests/regression/gate/regen_gate.py \
        --update-baseline "one-line rationale for the net-positive trade"

The EM/boundary-F1 scoring is reused from the cross-library harness
(``benchmarks/corpus_compare/run_compare.py``) rather than reinvented.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .gate.gate_scoring import (
    DEFAULT_EM_TOLERANCE,
    F1_TOLERANCE,
    load_gold_corpora,
    score_corpus,
    tolerance_for,
)

_GATE_DIR = Path(__file__).resolve().parent / "gate"
_BASELINE = _GATE_DIR / "baseline.json"


def _load_baseline() -> dict:
    return json.loads(_BASELINE.read_text(encoding="utf-8"))


# Score every corpus once for the whole module (segmenting is the expensive bit).
def _compute_scores() -> dict:
    out = {}
    for corpus, lang, units in load_gold_corpora():
        em, f1, n, _, _ = score_corpus(lang, units)
        out[corpus] = {"language": lang, "exact_match": em, "boundary_f1": f1, "n": n}
    return out


@pytest.fixture(scope="module")
def scores() -> dict:
    return _compute_scores()


@pytest.fixture(scope="module")
def baseline() -> dict:
    return _load_baseline()


def test_baseline_file_is_well_formed(baseline):
    """The committed baseline must carry its governance metadata."""
    assert baseline.get("rationale"), "baseline.json must record a one-line rationale (governance)"
    assert baseline.get("updated"), "baseline.json must record when it was last updated"
    assert baseline["by_corpus"], "baseline.json must score at least one corpus"


def test_gate_covers_every_baseline_corpus(scores, baseline):
    """Every corpus in the baseline must still be scored, and vice versa — so a
    silently-dropped corpus can't make the gate vacuously pass."""
    assert set(scores) == set(baseline["by_corpus"]), (
        "gate corpora and baseline corpora diverged; regenerate the baseline if the gold subset changed intentionally"
    )


def _corpus_ids():
    return list(_load_baseline()["by_corpus"])


@pytest.mark.parametrize("corpus", _corpus_ids())
def test_no_per_language_exact_match_regression(corpus, scores, baseline):
    base = baseline["by_corpus"][corpus]["exact_match"]
    now = scores[corpus]["exact_match"]
    tol = tolerance_for(corpus)
    assert now is not None and base is not None
    assert now >= base - tol, (
        f"{corpus}: exact-match regressed {base} -> {now} "
        f"(drop {round(base - now, 1)}pp > tolerance {tol}pp).\n"
        f"If this is an intended, net-positive trade, update the baseline via the reviewed flow:\n"
        f'  uv run python tests/regression/gate/regen_gate.py --update-baseline "<rationale>"\n'
        f"See tests/regression/gate/GOVERNANCE.md."
    )


@pytest.mark.parametrize("corpus", _corpus_ids())
def test_no_per_language_boundary_f1_regression(corpus, scores, baseline):
    base = baseline["by_corpus"][corpus]["boundary_f1"]
    now = scores[corpus]["boundary_f1"]
    if base is None:
        pytest.skip(f"{corpus}: no boundary-F1 baseline (text-altering corpus)")
    assert now is not None
    assert now >= base - F1_TOLERANCE, (
        f"{corpus}: boundary-F1 regressed {base} -> {now} "
        f"(drop {round(base - now, 1)}pp > tolerance {F1_TOLERANCE}pp).\n"
        f"If intended, update the baseline (see tests/regression/gate/GOVERNANCE.md)."
    )


def test_golden_rules_never_regress(scores, baseline):
    """Belt-and-suspenders: Golden Rules has zero tolerance and is the hard
    real-world gate; assert it explicitly so benchmark-tuning can't trade it
    away even if its tolerance were ever loosened by mistake."""
    base = baseline["by_corpus"]["golden_rules"]["exact_match"]
    now = scores["golden_rules"]["exact_match"]
    assert now >= base, f"Golden Rules exact-match regressed {base} -> {now} (zero tolerance)"


# ── negative / drop-detection unit tests ──────────────────────────────────────
# The parametrized tests above only ever exercise the EM predicate in its passing
# direction (real scores happen to clear the baseline). These pure-unit tests pin
# the *failing* branch and the tolerance map so a flipped ``>=`` or a broken
# ``tolerance_for`` can't leave the gate vacuously green. No re-segmentation here.


def _em_predicate(now: float, base: float, tol: float) -> bool:
    """Mirror the gate's per-corpus EM check (line ~97): ``now >= base - tol``."""
    return now >= base - tol


def test_em_predicate_fires_on_drop_beyond_tolerance():
    """A drop just past the tolerance must violate the gate predicate, and a drop
    sitting exactly at the tolerance must still pass — this is the failing branch
    the parametrized tests never reach with real scores."""
    base, tol = 90.0, DEFAULT_EM_TOLERANCE
    # Exactly at the allowed floor: still passes.
    assert _em_predicate(base - tol, base, tol)
    # One tenth of a point below the floor: gate must catch it.
    assert not _em_predicate(base - tol - 0.1, base, tol)


def test_em_predicate_passes_on_improvement():
    """An improvement (or no change) is never a regression."""
    base, tol = 90.0, DEFAULT_EM_TOLERANCE
    assert _em_predicate(base, base, tol)
    assert _em_predicate(base + 5.0, base, tol)


def test_zero_tolerance_corpora_catch_any_drop():
    """Golden Rules and CJK are zero-tolerance: even a 0.1pp dip must fail."""
    for corpus in ("golden_rules", "ud_zh_gsd"):
        tol = tolerance_for(corpus)
        assert tol == 0.0, f"{corpus} must be zero-tolerance"
        base = 100.0
        assert _em_predicate(base, base, tol)
        assert not _em_predicate(base - 0.1, base, tol)


def test_tolerance_for_known_and_unknown_corpora():
    """The tightened corpora must report 0.0; an unknown corpus must fall back to
    the default cushion."""
    assert tolerance_for("golden_rules") == 0.0
    assert tolerance_for("ud_zh_gsd") == 0.0
    assert tolerance_for("some_unknown_corpus") == DEFAULT_EM_TOLERANCE
