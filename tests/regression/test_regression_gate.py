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
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_GATE_DIR = _HERE / "gate"
_BASELINE = _GATE_DIR / "baseline.json"

if str(_GATE_DIR) not in sys.path:
    sys.path.insert(0, str(_GATE_DIR))

from gate_scoring import (  # noqa: E402
    F1_TOLERANCE,
    load_gold_corpora,
    score_corpus,
    tolerance_for,
)


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
