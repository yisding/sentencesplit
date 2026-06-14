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
1. **Abbreviation replacement (~40%)** — but NOT the scan (see §2a); it is the
   ~25 `re.sub` per call: per-occurrence replacements + always-on rule passes.
2. **List-item detection (~18%)** — runs 4 sub-formatters even on non-list text.

These ~58% are the structural gap. The `between_punctuation` / zero-width work
already addressed in #72 was <4% on short input (it helped large text instead).

### 2a. The Aho-Corasick scan is NOT the bottleneck (measured)

An earlier draft of this plan assumed the abbreviation *scan* (Aho-Corasick) was
the cost and proposed replacing it with pySBD's `in`-loop. **Direct measurement
disproves that.** Our pure-Python automaton `search()` vs a pySBD-style
`in`-filter loop over the same 199 abbreviations (identical match sets):

| input | AC | `in`-loop | winner |
|-------|---:|----------:|--------|
| tiny (15c)   | 2.4 µs | 7.2 µs | **AC 3.0×** |
| short (87c)  | 11.3 µs | 12.0 µs | **AC ~tied** |
| medium (198c)| 25.3 µs | 18.0 µs | `in` 1.4× |
| large (4k)   | 497 µs | 229 µs | `in` 2.2× |

Our AC is faster on short input; `in` only overtakes around ~100–150 chars.
(The crossover is inverted from textbook AC-wins-on-long because the automaton is
**pure Python**: its per-char loop has a large constant, so on long text 199
C-level `in` scans beat thousands of Python iterations.)

Crucially, the AC scan is only **~11 µs ≈ 3% of the 400 µs short call**. Swapping
it for `in` would *slow short down* and save nothing meaningful. The 39%
abbreviation cost is the **~25 `re.sub`/call** that follow discovery:
`scan_for_replacements` (a global `re.sub` per matched abbreviation),
`replace_multi_period_abbreviations`, and the always-on rule passes
(`PossessiveAbbreviationRule`, `SingleLetterAbbreviationRules`, `_COMPACT_AMPM_RE`,
`_UPPERCASE_INITIALISM_BOUNDARY_RE`, allcaps-imprint, the a.m./p.m. rules).
pySBD runs the per-occurrence regex too — so the gap is our **extra always-on
passes**, not the discovery mechanism.

---

## 3. Why pySBD is cheaper per call (structural delta)

pySBD does **not** have fewer phases (~20 full-text passes, similar to ours).
The difference is per-pass constant cost and cheap short-circuits:

1. **Abbreviation discovery is a wash on short text.** pySBD short-circuits with
   C-level `in` (`pysbd/abbreviation_replacer.py:82`); ours uses a pure-Python
   Aho-Corasick automaton (`sentencesplit/abbreviation_replacer.py:535-564`). Per
   §2a these cost ~the same on short input (AC is actually slightly faster), so
   this is **not** where the gap is — both then run the same per-occurrence regex
   work. Discovery is ~3% of the call either way.
2. **Always-on extra passes ours added** in `replace()` that pySBD lacks (this,
   not the scan, is the abbreviation-phase cost):
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

### ~~P1 — Abbreviation scan fast-path~~ — DROPPED (premise disproved, see §2a)

The original P1 (replace the Aho-Corasick scan with pySBD's `in`-loop or a
compiled alternation) is **invalid**: measurement shows the AC scan is ~3% of the
call and is already faster than `in` on short input. Switching would slow short
text down. Do not pursue. The abbreviation-phase cost lives in the always-on
passes (now P1, below), not discovery.

*Optional, low priority:* a length-gated `in` fallback would help medium/large
discovery (~7 µs on medium, ~270 µs on 4k) but hurts short, so only worth it as a
threshold switch if medium/large latency becomes a target — not for this goal.

### P1 — Gate the always-on abbreviation `replace()` passes (was P2; now top)

`AbbreviationReplacer.replace()` runs ~25 `re.sub`/call on short text, several of
them unconditional rule passes that almost never match. Guard each behind a cheap
`in`/structural check so it only runs when it can fire:
- `_COMPACT_AMPM_RE` — only if a digit is adjacent to `a/p`+`.`+`m`.
- `_UPPERCASE_INITIALISM_BOUNDARY_RE`, non-ASCII a.m./p.m. restores — only if the
  `∯` sentinel is present (it only exists after an abbreviation matched).
- allcaps-imprint — only if the text has a 2+ all-caps run.
- the a.m./p.m. rule set (`apply_ampm_boundary_rules`, ~5–7%) — gate on an
  `[ap]·m` pattern being present.
This is the largest *safe* slice of the abbreviation phase. *Risk:* low (each
regex already requires the guarded condition). *DoD:* suite green + byte-identical
corpus output.

### P2 — List-item detection guards (target: the ~18% list phase)

`_mark_list_item_boundaries` constructs a fresh `ListItemReplacer` and runs 4
sub-formatters every call. Safe reductions:
- **P2a — Trigger-char guards per sub-formatter.** Skip the numbered-list passes
  when the text has no digit; skip the parens passes when there is no `(`/`)`;
  skip alphabetical/roman passes when no single letter precedes `.`/`)`. Each
  formatter's regex already requires those chars, so skipping is a no-op.
- **P2b — Early-out in `iterate_alphabet_array`** when `re.findall` returns empty
  (avoid building the 26-entry `alphabet_index` dict and the lower/filter work).
*Risk:* low-medium (list logic is subtle; guards must be on chars the regexes
require). *DoD:* suite green; the list-heavy Golden Rules unchanged.

### P3 — Remove the per-call lock on the abbreviation-data read (low risk, small gain)

`AbbreviationReplacer.__init__` takes an `RLock` every call just to read the
per-class `_data`. Use a lock-free fast read (double-checked: read the dict
first, only lock to build on miss) or resolve `_data` once and stash it on the
Abbreviation class / LanguageProfile. *Risk:* low; preserve thread-safety of the
first build. *DoD:* suite green + a concurrency smoke test.

---

## 5. Sequencing, guardrails, and non-goals

**Sequence:** P3 first (mechanical, lowest risk, de-risks the harness loop), then
P1 (gate the always-on abbreviation passes — the biggest *safe* slice of the 40%
abbreviation phase), then P2 (the ~18% list phase). Re-run `phase_profile.py` +
competitive CodSpeed after each. Note the discovery scan is deliberately left
alone (see §2a).

**Guardrails (non-negotiable):**
- Byte-identical `segment()`/`segment_spans()` output. Full suite + Golden Rules
  green is the gate; add a corpus-wide equivalence diff (old vs new) per change.
- Each change is reverted automatically if the suite or Golden Rules regress.
- Keep changes isolated per branch/PR so CodSpeed attributes each delta.

**Non-goals / risks to avoid:**
- Do **not** touch the abbreviation *discovery* scan — it is faster than `in` on
  short input and only ~3% of the call (§2a). The Aho-Corasick automaton stays.
- Do not change boundary semantics to chase speed. This is a pure
  constant-factor effort; if a change can't be made byte-identical, it is out of
  scope for this plan.

**Expected envelope:** all three items (P1 gate always-on passes, P2 list guards,
P3 lock) are low-risk and target the always-on `re.sub` count + the list phase.
Together they address roughly the abbreviation always-on slice (a chunk of the
40%) plus the ~18% list phase. Treat individual gains as unproven until measured
per-change with `phase_profile.py` and the competitive CodSpeed run; the honest
expectation is incremental (single-digit to low-double-digit %), not a dramatic
close, because much of the abbreviation phase is genuine per-occurrence regex
work that pySBD also pays.
