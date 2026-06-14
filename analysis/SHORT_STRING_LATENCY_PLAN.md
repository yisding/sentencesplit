# Short/Medium `segment()` Latency — Deep Investigation & Action Plan

**Original goal:** close the ~22–28% per-call gap vs pySBD on short/medium
English text reported by the competitive CodSpeed benchmark (#71).

**Headline finding (measured): the regression is already gone as of #72.** In
real wall-clock we are at parity-to-ahead of pySBD on short and medium, and on a
cachegrind-style instruction-count proxy we are now *ahead*. The original
CodSpeed gap was (a) an instruction-count artifact of pure-Python per-character
loops, whose single biggest contributor — the zero-width scanner — was removed by
#72, and (b) measured before #72 landed. What remains below is a menu to *extend*
the lead, not to catch up.

This document is backed by three reusable harnesses (the "workflow"):
`benchmarks/phase_profile.py`, `benchmarks/differential_profile.py`,
`benchmarks/abbr_scan_compare.py`.

---

## 1. The workflow (how every number here is reproduced)

```bash
# Per-phase wall-time attribution of our own call:
uv run python benchmarks/phase_profile.py --size short  --iters 20000

# Head-to-head vs pySBD: wall time, regex-op counts, time-in-re, top funcs:
uv run python benchmarks/differential_profile.py --size short
uv run python benchmarks/differential_profile.py --size medium

# Aho-Corasick scan vs naive `in`-loop crossover:
uv run python benchmarks/abbr_scan_compare.py

# Instruction-count proxy (Python line-events ≈ what CodSpeed counts):
#   sys.settrace line-event count of ours vs pysbd (see §3).
```

CodSpeed's CI mode counts **CPU instructions** (cachegrind), not wall time. The
two diverge sharply here, so we measure both: wall-clock for real latency, and a
`sys.settrace` line-event count as a faithful, local instruction-count proxy.

---

## 2. Measured state, post-#72

`segment()` on the short (87c) and medium (198c) samples, Python 3.13, warm,
8000 iters (wall-clock reproduced across runs; line-events are deterministic):

| metric | input | ours | pySBD | ratio |
|--------|-------|-----:|------:|------:|
| wall-clock µs/call | short | ~312 | ~316 | **0.99×** |
| wall-clock µs/call | medium | ~689 | ~743 | **0.93×** |
| regex ops/call | short | 118 | 266 | **we run fewer** |
| line-events/call (instr. proxy) | short | 2059 | 2203 | **0.93×** |

We are at parity or ahead on every axis. Note we run **fewer** regex ops than
pySBD (118 vs 266) — the "we do more passes" theory is false; pySBD does ~2× the
regex ops but they are tiny literal-replacement subs.

### 2a. Abbreviation *discovery* is not the bottleneck (and AC is fine)

`benchmarks/abbr_scan_compare.py` (199 patterns, identical match sets):

| input | AC | `in`-loop | winner |
|-------|---:|----------:|--------|
| tiny (15c)   | 2.4 µs | 8.2 µs | **AC 3.4×** |
| short (87c)  | 11.3 µs | 13.5 µs | **AC** |
| medium (198c)| 30.5 µs | 21.0 µs | `in` 1.4× |
| large (4k)   | 619 µs | 286 µs | `in` 2.2× |

Our pure-Python Aho-Corasick is *faster* than a pySBD-style `in`-loop on short
input; `in` only overtakes around ~150 chars. The scan is ~3% of the call. **Do
not replace it.** (It can, however, be made ~2× faster outright — see §4, P-AC.)

---

## 3. What the original gap actually was (root cause)

A `sys.settrace` line-event count (≈ instructions executed) on the **pre-#72**
code: ours **2787** vs pySBD **2243** = **1.24×** — almost exactly the ~28%
CodSpeed gap, and far above the ~1.06× wall-clock ratio. The gap was concentrated
in pure-Python per-character loops that cost almost nothing in wall-clock but
execute hundreds of *counted* interpreted operations:

| our function | line-events/call | wall-clock cost | pySBD equivalent |
|--------------|-----------------:|-----------------|------------------|
| `_strip_zero_width_before_sentence_closers` | **876** | **~0 µs** | none (pySBD has no zero-width handling) |
| `AhoCorasickAutomaton.search` | 394 | *faster* than pySBD's scan | C-level `abbr in lowered` |
| `_GluedLowercaseRunOnRegex.sub` (`lang/common/standard.py:11`) | 309 | small | one C `re.sub` |
| `apply_rules` / `_sub_symbols_fast` | 156 / 132 | small | C `re.sub` |

**Two distinct causes, two distinct truths:**
1. **CodSpeed instruction-count gap (~28%)** — largely an *artifact*: CPython
   pushes pySBD's work into the C `re` engine (≈1 counted op per `re.sub`), while
   our pure-Python loops are fully counted. The zero-width scanner alone was 876
   of our 2787 events. **#72 gated it** (`segmenter.py:89`, return early when no
   zero-width char), cutting ~730 events → post-#72 proxy is **2059 vs 2203 =
   0.93×, we are ahead.**
2. **Wall-clock gap (~6–9%, pre-#72)** — real, and came from our heavier
   *non-destructive* pipeline (span mapping `_match_spans`/`_find_sentence_start`,
   the resplit passes, the sentinel-escape disjointness check, and callback-driven
   subs), not regex efficiency. #72's zero-width guard plus normal variance brings
   short to parity; medium we already win.

**So #72 — framed at the time as "helps large text" — actually closed the
short/medium gap, because the zero-width scanner ran per output segment and
dominated the instruction count on short input. Its wall-clock effect on short
was within noise; its instruction-count effect was the whole ballgame.** The
competitive CodSpeed benchmark on `main` (post-#72) should now show short/medium
at parity-or-ahead; the next competitive run will confirm.

---

## 4. Menu to *extend* the lead (all behavior-preserving / byte-identical)

We are no longer catching up, so these are prioritized by **(improves both
metrics) > (improves one)** × leverage × safety. Implement test-first on isolated
branches with a byte-identical gate (full suite + Golden Rules + a corpus diff;
auto-revert on regression). Re-measure each with `phase_profile.py`,
`differential_profile.py`, and the competitive CodSpeed run.

### Tier 1 — improves BOTH wall-clock and instruction-count

- **P-LIST — List-item early-out + guards (~18% phase).** In
  `lists_item_replacer.py`: (a) early-`return` in `iterate_alphabet_array` when
  `re.findall` is empty (kills the 4×/call 26-entry `alphabet_index` dict builds);
  (b) skip the numbered formatters when the text has no digit, the parens
  formatters when no `)`; (c) reuse the identical alphabetical `findall` across
  the roman/non-roman passes (4 scans → 2). Each guard char is required by every
  alternative of its regex, so skipping is byte-identical. **Guard inside the
  formatter methods** so Slovak's `add_line_break` override inherits them.
  Validate with a differential oracle (old vs new `add_line_break` char-for-char).
  *Risk:* low (items a/b), moderate (item c — confirm shared pattern+flags).
- **P-RESPLIT/CALLBACK — Gate the non-destructive passes + de-callback subs.** Per
  Agent C, the real wall-clock cost is span mapping + resplit + callback subs.
  Extend the eager-gate discipline already in `_maybe_resplit_multi_sentence_quote`
  to the other resplit/postprocess passes (skip `_split_on_uppercase_boundary`
  scans for segments with no `.)`/multi-terminator), and replace constant-result
  callback subs with literal-string subs / `str.replace` (the
  punctuation/continuous/double-punct callbacks). *Risk:* medium — touches
  boundary-adjacent code; needs the full byte-identical gate.
- **P-ABBR — Gate the always-on abbreviation `replace()` passes.**
  `AbbreviationReplacer.replace()` runs ~25 `re.sub`/call; gate the rarely-firing
  ones (`_COMPACT_AMPM_RE`, `_UPPERCASE_INITIALISM_BOUNDARY_RE`, non-ASCII a.m./p.m.
  restores, allcaps-imprint, the a.m./p.m. set) on a cheap presence check (digit
  adjacency, `∯`-sentinel presence, all-caps run). *Risk:* low.

### Tier 2 — Aho-Corasick ~2× (helps both; bigger on medium/large)

- **P-AC — DFA δ-table precompute + length-gated hybrid.** Empirically (Agent A):
  precomputing fail-links into a flat DFA table (removing the inner `while`
  fail-link loop in `AhoCorasickAutomaton.search`) gives **short 9.8→4.9 µs (~2×),
  long 270→~160 µs (~1.7×)**, drop-in, cached, ~2 ms one-time build. Add a
  length-gated hybrid (DFA under ~200 chars, naive C `in`-loop above) to beat both
  the automaton and pySBD's `in`-loop across all sizes. *Risk:* low–moderate (two
  code paths; ship a `dfa == naive == current` fuzz/property test). Rejected by
  measurement and not to be tried: `re`-alternation (3–5× slower), byte/array/tuple
  transition tables (all slower than `dict.get`), first-char prefilter (English's
  24 first-chars defeat it).

### Tier 3 — instruction-count only (low wall-clock value)

- **P-GLUED — rewrite the `_GluedLowercaseRunOnRegex` Python char scanner
  (`lang/common/standard.py:11`) into a single C-engine `re` call.** ~309
  line-events, near-zero wall-clock. Only worth it if the CodSpeed number is a
  release gate; it barely moves real latency.

---

## 5. Guardrails & non-goals

- **Byte-identical** `segment()`/`segment_spans()` output is the bar. Full suite +
  Golden Rules green + a corpus-wide old-vs-new diff per change; auto-revert on
  any regression; one change per branch/PR so CodSpeed attributes each delta.
- **Do not touch the abbreviation discovery semantics** — AC is fine and faster
  than `in` on short (§2a). P-AC keeps the automaton, only speeds its inner loop.
- **No boundary-semantics changes** to chase speed; if a change can't be made
  byte-identical it is out of scope.
- **Pick the metric deliberately.** If the goal is *real latency*, prioritize
  Tier 1 (and skip Tier 3). If the goal is the *CodSpeed gate number*, Tier 2/3
  (the pure-Python loops) move it most. They overlap in Tier 1, which is why Tier
  1 leads.

**Honest expectation:** we are already at parity/ahead, so these are
incremental "pull further ahead" wins, not a turnaround. Tier 1 + P-AC together
are the worthwhile set; treat each gain as unproven until measured per-change.
