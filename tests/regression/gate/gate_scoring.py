# -*- coding: utf-8 -*-
"""Hermetic scoring helpers shared by the regression gate and its regen script.

Pure Python, zero third-party imports. The exact-match and boundary-F1 scoring
is *reused* from the cross-library harness (``benchmarks/corpus_compare/run_compare.py``)
rather than reimplemented, so the gate and the Tier-2 comparison measure the same
thing. The harness module is pure-Python (its native/Ruby/NLTK adapters are all
lazy-imported inside functions), so importing ``boundary_f1`` from it pulls in no
third-party dependency and keeps the gate runnable on the aarch64 box.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
_GOLD_DIR = _HERE / "gold"
_UD_GOLD = _GOLD_DIR / "ud_gold_subset.json"
_BENCH = _REPO_ROOT / "benchmarks"
_HARNESS = _BENCH / "corpus_compare"

# Reuse the harness's boundary-F1 (whitespace-insensitive, character-stream-aware).
if str(_HARNESS) not in sys.path:
    sys.path.insert(0, str(_HARNESS))
from run_compare import boundary_f1  # noqa: E402

# ── per-language EM tolerances (percentage points) ────────────────────────────
# How far a corpus's exact-match may dip below the committed baseline before the
# gate fails the PR. n=30 per UD corpus, so single-unit noise is ~3.3pp; we allow
# a small cushion per language and tighten it where the score is load-bearing.
# Golden Rules is a hard real-world gate — no tolerance. Boundary-F1 uses a single
# global tolerance (it is far less jumpy than EM at this sample size).
DEFAULT_EM_TOLERANCE = 3.4  # ~one unit at n=30
F1_TOLERANCE = 1.5
TOLERANCES: dict[str, float] = {
    # Golden Rules is the hardest real-world signal: it may not regress at all.
    "golden_rules": 0.0,
    # CJK boundary detection is near-perfect and a headline claim: keep it tight.
    "ud_zh_gsd": 0.0,
    # French/Spanish/Russian sit high; a one-unit dip is tolerable but not more.
    "ud_fr_gsd": 3.4,
    "ud_es_gsd": 3.4,
    "ud_ru_gsd": 3.4,
    # Dutch/German are the known-fragile European corpora a global rule change has
    # silently regressed before; keep them at the default one-unit cushion so a
    # second silent dip is caught.
    "ud_nl_alpino": 3.4,
    "ud_de_gsd": 3.4,
}


def tolerance_for(corpus: str) -> float:
    return TOLERANCES.get(corpus, DEFAULT_EM_TOLERANCE)


def _norm(sentences) -> list[str]:
    """Match the harness: strip each sentence, drop empties (boundary-only compare)."""
    return [s.strip() for s in sentences if s and s.strip()]


def load_gold_corpora() -> list[tuple[str, str, list[dict]]]:
    """Return ``[(corpus, language, units)]`` where each unit is ``{text, gold}``.

    Golden Rules are read from the in-repo ``benchmarks/english_golden_rules.py``
    (already vendored, the canonical English gate); UD units are read from the
    vendored ``gold/ud_gold_subset.json``.
    """
    corpora: list[tuple[str, str, list[dict]]] = []

    # English Golden Rules (already in-repo — reference, do not duplicate).
    if str(_BENCH) not in sys.path:
        sys.path.insert(0, str(_BENCH))
    from english_golden_rules import GOLDEN_EN_RULES

    gr_units = [{"text": text, "gold": list(expected)} for text, expected in GOLDEN_EN_RULES]
    corpora.append(("golden_rules", "en", gr_units))

    # Vendored UD gold subset.
    doc = json.loads(_UD_GOLD.read_text(encoding="utf-8"))
    for c in doc["corpora"]:
        units = [{"text": u["text"], "gold": list(u["gold"])} for u in c["units"]]
        corpora.append((c["corpus"], c["language"], units))
    return corpora


def score_corpus(language: str, units: list[dict]):
    """Score sentencesplit over one corpus.

    Returns ``(em_pct, f1_pct, n, (em_correct, em_total), (f1_sum, f1_n))``.
    Imports ``sentencesplit`` lazily so module import stays cheap.
    """
    import sentencesplit

    seg = sentencesplit.Segmenter(language=language, clean=False)
    em_correct = 0
    f1_sum = 0.0
    f1_n = 0
    for u in units:
        pred = _norm(seg.segment(u["text"]))
        gold = list(u["gold"])
        if pred == gold:
            em_correct += 1
        prf = boundary_f1(pred, gold)
        if prf is not None:
            f1_sum += prf[2]
            f1_n += 1
    n = len(units)
    em_pct = round(em_correct / n * 100, 1) if n else None
    f1_pct = round(f1_sum / f1_n * 100, 1) if f1_n else None
    return em_pct, f1_pct, n, (em_correct, n), (f1_sum, f1_n)
