# Regression-gate governance

This directory holds the hermetic, CI-gated regression gate (roadmap item **N2**).
The gate scores **only `sentencesplit`** against a committed gold subset and fails a
PR on a per-language accuracy drop. It runs as a normal pytest
(`tests/regression/test_regression_gate.py`), so CI runs it automatically with the
rest of the suite — no separate wiring.

It exists to make one realized process failure structurally impossible: a global
rule change once **silently regressed Dutch** during the period-before-comma fix and
was caught only by manual review. The gate now catches that class before merge.

## What the gate checks

For each corpus in `baseline.json` it recomputes, for the current code:

- **exact-match** — predicted sentence list equals the gold list (strict, after
  per-sentence `strip()` and dropping empties);
- **boundary-F1** — F1 over whitespace-insensitive boundary positions.

It **fails the PR** if any corpus's exact-match drops below its committed baseline
by more than that corpus's **per-language tolerance**, or if boundary-F1 drops by
more than the global F1 tolerance. The scoring is **reused** from the cross-library
harness (`benchmarks/corpus_compare/run_compare.py::boundary_f1`) — not reinvented —
so the gate and the Tier-2 comparison measure the same thing.

## Hermetic by construction

Pure Python, **no Ruby, no NLTK, no network, no native wheels** — it runs on the
aarch64 dev box. The gold is committed in-repo:

- **English Golden Rules** — referenced directly from `benchmarks/english_golden_rules.py`
  (already in-repo; not duplicated). Hard gate, **zero tolerance**.
- **Universal Dependencies gold subset** — vendored in `gold/ud_gold_subset.json`:
  only the small gold units actually scored (text + gold sentence list per unit),
  not the full treebanks. Each treebank's license and homepage are recorded there
  for attribution. UD treebanks are redistributable under their stated licenses
  (CC BY-SA / CC BY-NC-SA); see `gold/ud_gold_subset.json` and
  https://universaldependencies.org/.

## Per-language tolerances

Tolerances live in `gate_scoring.py::TOLERANCES` (exact-match, in percentage points)
plus a single global `F1_TOLERANCE`. Rationale:

- Each UD corpus is **n=30**, so one unit ≈ 3.3pp. The default EM tolerance is
  **3.4pp** (about one unit of noise).
- **`golden_rules` and `ud_zh_gsd` are pinned at 0.0** — Golden Rules is the hard
  real-world gate and CJK is a headline best-in-field claim; neither may regress at all.
- The historically fragile European corpora (`ud_nl_alpino`, `ud_de_gsd`) and the
  high scorers (`ud_fr_gsd`, `ud_es_gsd`, `ud_ru_gsd`) sit at the one-unit default so
  a second silent dip like the Dutch incident is caught.

Tightening a tolerance is always safe. Loosening one is a baseline-governance change
and must carry a rationale in the PR.

## The `# baseline-update` flow (reviewed)

A change that improves overall accuracy will, at n=30 per corpus, sometimes cost EM
in *some* language on *some* PR. That is expected. To move the committed baseline,
use the explicit, reviewed flow — never hand-edit `baseline.json`:

```bash
uv run python tests/regression/gate/regen_gate.py \
    --update-baseline "one-line rationale for the trade"
```

This re-scores the current code over the committed gold, rewrites `baseline.json`,
and stamps the **one-line rationale** and date into the file. Then:

1. Commit the regenerated `baseline.json` **in the same PR** as the change that moved it.
2. Put the rationale (and the per-corpus deltas) in the commit body / PR description so
   a reviewer can see exactly which scores moved and why.
3. The reviewer checks the diff: scores should move only where the change predicts.

## The net-positive-trade rule

A baseline update is allowed when the change is **net-positive on the union of the
gold corpora** — i.e. total exact-match across all corpora goes up (or holds) — **even
if one language dips**, provided:

- the dip is within a sane bound (don't trade a large drop in one language for a tiny
  gain elsewhere — prefer changes that are Pareto-improving or close to it);
- **`golden_rules` does not regress at all** (zero tolerance, non-negotiable); and
- the one-line rationale names the trade explicitly (e.g.
  *"de/nl abbreviation curation: +6.7 de, +3.3 nl, −3.3 es; net +2.3 EM"*).

The `overall` block in `baseline.json` records total EM/F1 so the net direction of any
trade is auditable from the committed diff alone.

## Regenerating the vendored gold

Only when the vendored units must change (e.g. adding a treebank). This is **not** on
the hermetic test path and needs the network-populated corpus cache:

```bash
# populate benchmarks/corpus_compare/corpora_cache/ if needed (network)
uv run python benchmarks/corpus_compare/corpora.py
# re-extract the vendored gold subset
uv run python tests/regression/gate/regen_gate.py --vendor-gold
```

The extraction mirrors `benchmarks/corpus_compare/corpora.py` exactly, so the vendored
units stay identical to the units the Tier-2 cross-library comparison scores.

## Relationship to the cross-library harness

This is **Tier 1** (CI-gated, hermetic, self-vs-gold). The full cross-library comparison
in `benchmarks/corpus_compare/` (pysbd, Ruby pragmatic_segmenter, Punkt, syntok) is
**Tier 2** — manual/scheduled, kept off the PR path because it needs Ruby + NLTK +
network + native wheels. `benchmarks/corpus_compare/results/scoreboard.baseline.json`
is the Tier-2 artifact; this gate's `baseline.json` is independent and tracks current
`sentencesplit` behavior.
