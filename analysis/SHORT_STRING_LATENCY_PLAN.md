# Short/Medium `segment()` Latency — Investigation & Action Plan

**Goal:** close the ~22% per-call latency gap vs pySBD on short/medium English
text (surfaced by the competitive CodSpeed benchmarks in #71), **without**
changing segmentation output (byte-identical) or losing the Aho-Corasick
automaton's advantage on very large abbreviation lists.

This is a living plan. It pairs with the reusable exploration harness
`benchmarks/phase_profile.py` (the "workflow"): run it to re-attribute per-call
cost to pipeline phases after each change.

---

## 1. How to reproduce the measurements (the workflow)

```bash
# Per-phase wall-time attribution for one input size:
uv run python benchmarks/phase_profile.py --size short  --iters 20000
uv run python benchmarks/phase_profile.py --size medium --iters 12000

# End-to-end latency (and cProfile hot functions):
uv run python benchmarks/latency_baseline.py --iters 4000 [--profile]

# Deterministic CI verdict (instruction count) vs pySBD/punkt:
#   the competitive benchmarks run on every PR via .github/workflows/codspeed.yml
#   (benchmarks/test_competitive_codspeed.py): watch test_segment[short-ours] etc.
```

`phase_profile.py` wraps each Processor / AbbreviationReplacer / Segmenter stage
with a timer. The `*wrapper` rows (e.g. `abbr: replace (whole)`,
`split_into_segments`) **contain** the rows below them — do not sum across them.

---

## 2. Where the time goes (measured, Python 3.13, warm)

`segment("Dr. Smith went to Washington. … Sen. Jones.")` — **short, 87 chars,
~0.40 ms/call:**

| phase | ms/call | % of call |
|-------|--------:|----------:|
| `replace_abbreviations` (text phase) | 0.156 | **39%** |
|   ↳ `search_for_abbreviations_in_string` (automaton scan + per-abbr sub) | 0.091 | 23% |
|   ↳ `apply_ampm_boundary_rules` | 0.026 | 7% |
| `_mark_list_item_boundaries` (ListItemReplacer.add_line_break) | 0.078 | **20%** |
| `split_into_segments` (wrapper: boundary phases + postprocess) | 0.090 | 22% |
|   ↳ `between_punctuation` | 0.013 | 3% |
| `replace_numbers` / `_protect_special_tokens` | ~0.010 ea | 2.5% ea |

**Medium (198 chars, ~0.88 ms/call)** is the same shape: `replace_abbreviations`
**43%** (of which `search_for_abbreviations_in_string` **31%**),
`_mark_list_item_boundaries` **18%**.

**Conclusion:** two fixed-cost phases dominate and run on *every* call regardless
of whether the input needs them:
1. **Abbreviation replacement (~40%)** — dominated by the abbreviation scan.
2. **List-item detection (~18%)** — runs 4 sub-formatters even on non-list text.

These ~58% are the structural gap. The `between_punctuation` / zero-width work
already addressed in #72 was <4% on short input (it helped large text instead).

---

## 3. Why pySBD is cheaper per call (structural delta)

pySBD does **not** have fewer phases (~20 full-text passes, similar to ours).
The difference is per-pass constant cost and cheap short-circuits:

1. **Abbreviation loop short-circuits in C before any regex.** pySBD iterates its
   188 English abbreviations and does `if stripped not in lowered: continue`
   (`pysbd/abbreviation_replacer.py:82`). For short text ~186/188 fail the
   C-level `str.__contains__` instantly; only 0–2 reach a regex.
   **Ours** replaced this with an Aho-Corasick automaton
   (`sentencesplit/abbreviation_replacer.py:535-564`) whose `search()`
   (`:63-76`) runs a **pure-Python per-character state-machine loop over the
   whole lowered text on every call** — slower than a handful of C `in` checks
   on short strings. The automaton wins only when the abbreviation list is huge;
   for ~200 entries on short text it is a net loss.
2. **Always-on extra passes ours added** in `replace()` that pySBD lacks:
   `_COMPACT_AMPM_RE`, `_UPPERCASE_INITIALISM_BOUNDARY_RE`, allcaps-imprint
   protection, non-ASCII a.m./p.m. restores (`:311-357`). Each is an
   unconditional full-text regex pass.
3. **Per-call `RLock` acquisition.** Every `AbbreviationReplacer.__init__`
   (`:55-58`) takes `_cache_lock` to fetch the cached `_data`, on every call.
   pySBD has no such lock.

What we already match: a no-punctuation boundary guard
(`processor.py:691` `check_for_punctuation`) skips the boundary pipeline for
segments lacking sentence-ending punctuation — same idea as pySBD.

---

## 4. Action plan (prioritized by leverage × safety)

Every item is **behavior-preserving**: the validation bar is byte-identical
`segment()`/`segment_spans()` output (full suite incl. Golden Rules stays green,
and a cross-corpus equivalence check). Implement **test-first**, on its own
branch, auto-revert if Golden Rules or the suite regress (mirror the
`improve-sentencesplit` discipline). Measure each with `phase_profile.py` and the
competitive CodSpeed benchmark.

### P1 — Abbreviation scan fast-path (target: the ~25–30% `search_in_string` cost)

The automaton's job is to find the **set** of abbreviations present, then run a
per-occurrence `re.sub`. Three candidate mechanisms, to prototype in order:

- **P1a — Single compiled alternation regex (preferred to prototype first).**
  Replace the pure-Python `search()` char loop with one cached
  `re.compile("|".join(escaped_abbrevs))` (anchored as the automaton expects) and
  a single C-level `.findall`/`.finditer` to discover the present set. One C pass
  vs a Python per-char loop should beat both the automaton and pySBD's 188 `in`s.
  *Risk:* must reproduce the automaton's matched-set **exactly** (case-folding,
  overlap, boundary semantics). *DoD:* for a large corpus, the present-set is
  identical to the automaton's for every line.
- **P1b — Length-gated fallback.** Below a small text-length threshold, use a
  pySBD-style `in`-guarded loop (cheap on short text); above it, keep the
  automaton (wins on long text / big lists). *Risk:* two code paths must produce
  identical sets — property-test them against each other.
- **P1c — Cheap pre-filter.** Skip the scan entirely when a one-pass check proves
  no abbreviation can match (e.g. no `.` in the line). Cheapest, smallest gain;
  stack on top of P1a/P1b.

### P2 — Gate the always-on `replace()` regexes (low risk, modest gain)

Guard each unconditional pass in `AbbreviationReplacer.replace()` behind a cheap
`in`/structural check so it only runs when it can match:
- `_COMPACT_AMPM_RE` — only if a digit is adjacent to `a/p` + `.` + `m`.
- `_UPPERCASE_INITIALISM_BOUNDARY_RE`, non-ASCII a.m./p.m. restores — only if the
  `∯` sentinel is present (it only exists after an abbreviation matched).
- allcaps-imprint — only if the text has an all-caps run.
*Risk:* low (each regex already requires the guarded condition). *DoD:* suite
green + byte-identical corpus output.

### P3 — Remove the per-call lock on the abbreviation-data read (low risk, small gain)

`AbbreviationReplacer.__init__` takes an `RLock` every call just to read the
per-class `_data`. Use a lock-free fast read (double-checked: read the dict
first, only lock to build on miss) or resolve `_data` once and stash it on the
Abbreviation class / LanguageProfile. *Risk:* low; preserve thread-safety of the
first build. *DoD:* suite green + a concurrency smoke test.

### P4 — List-item detection guards (target: the ~18% list phase)

`_mark_list_item_boundaries` constructs a fresh `ListItemReplacer` and runs 4
sub-formatters every call. Safe reductions:
- **P4a — Trigger-char guards per sub-formatter.** Skip the numbered-list passes
  when the text has no digit; skip the parens passes when there is no `(`/`)`;
  skip alphabetical/roman passes when no single letter precedes `.`/`)`. Each
  formatter's regex already requires those chars, so skipping is a no-op.
- **P4b — Early-out in `iterate_alphabet_array`** when `re.findall` returns empty
  (avoid building the 26-entry `alphabet_index` dict and the lower/filter work).
*Risk:* low-medium (list logic is subtle; guards must be on chars the regexes
require). *DoD:* suite green; the list-heavy Golden Rules unchanged.

### P5 (stretch) — a.m./p.m. rule gating

`apply_ampm_boundary_rules` is ~5–7%. Guard the rule set on the presence of an
`m`/`.`-adjacent pattern. Lower priority; do after P1–P4 re-measure.

---

## 5. Sequencing, guardrails, and non-goals

**Sequence:** P2 + P3 first (cheap, low-risk warm-up + de-risks the harness),
then P4 (clear ~18% target), then P1 (biggest but riskiest — prototype P1a,
fall back to P1b). Re-run `phase_profile.py` + competitive CodSpeed after each.

**Guardrails (non-negotiable):**
- Byte-identical `segment()`/`segment_spans()` output. Full suite + Golden Rules
  green is the gate; add a corpus-wide equivalence diff (old vs new) per change.
- Each change is reverted automatically if the suite or Golden Rules regress.
- Keep changes isolated per branch/PR so CodSpeed attributes each delta.

**Non-goals / risks to avoid:**
- Do **not** regress the automaton's advantage on very large abbreviation lists
  or the combined `en_es_zh` profile — P1 must keep (or length-gate to) the
  automaton for the large-list case.
- Do not change boundary semantics to chase speed. This is a pure
  constant-factor effort; if a change can't be made byte-identical, it is out of
  scope for this plan.

**Expected envelope:** P2+P3+P4 are low-risk and should recover a meaningful
slice of the list phase + always-on passes (rough order ~10–20% of the call).
P1 is where the abbreviation ~30% lives and is the swing item; treat its gain as
unproven until P1a is prototyped and shown byte-identical.
