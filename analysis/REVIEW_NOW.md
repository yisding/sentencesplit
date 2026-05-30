# REVIEW_NOW — feat/now-all (N1 + N2 + N5 + N4)

Review of the cumulative work integrated on `feat/now-all` versus `origin/main`, toward
`analysis/LEVEL_UP_PLAN.md` (specs in `analysis/ROADMAP_EXECUTION.md`). Branch is checked
out at `/home/yi/Code/sentencesplit` (HEAD `20a8d4c`). Nothing is pushed; `main` is untouched.

---

## 1. Summary

`feat/now-all` stacks all four roadmap items on top of `origin/main` (6 commits, +5388/-6 lines
across 20 files):

| Item | Commit | What |
|------|--------|------|
| N1 — discovery + metadata + zero-dep guard | `26464c7` | `list_languages()`, package classifiers/keywords, `tests/test_zero_dependencies.py` |
| N2 — hermetic CI regression gate | `2746ff5` | `tests/regression/gate/*` + `test_regression_gate.py`, scores vs committed gold, `--update-baseline` governance |
| N5 — byte-faithful `segment_spans()` round-trip | `ec9d0bf` | `tests/test_span_roundtrip.py`, Hypothesis props, `char_span` deprecated; fixed a latent whitespace-only span-drop bug in `_match_spans()` |
| N4 — `StreamSegmenter` | `419f3b1` | `sentencesplit/stream_segmenter.py`, latency benchmark, TTS recipe |

Integration state (all re-verified this review):

- Full suite `uv run pytest -q --ignore=tests/test_spacy_component.py` = **1634 passed, 8 xfailed, 0 failed**.
- Regression gate `tests/regression/test_regression_gate.py` = **25 passed**. Baseline carries 11 corpora with real (non-None) EM+F1 values (golden_rules EM 97.9/F1 99.6 down to ud_it_isdt EM 50.0/F1 81.5) and a recorded rationale — the positive path is non-vacuous.
- English Golden Rules = **50 passed, 1 xfailed** (index 17, "At 5 a.m. Mr. Smith…"). This is the **pre-existing** `feat/now-integration` baseline state, not a regression: neither merged branch touches English abbreviation/boundary logic.
- Merge was clean: `feat/span-roundtrip` fast-forwarded; `feat/stream-segmenter` merged via ort with no conflicts. `__init__.py` correctly retains BOTH the N1 `list_languages` export and the N4 `StreamSegmenter` export (verified lines 2 and 4).

**Headline verdict: FIX-THEN-SHIP.** N1, N2, and N5 are in good shape. N4 (`StreamSegmenter`) ships
correct plain-string output and a strong streaming==non-streaming contract, but carries one
correctness bug (silent span corruption under `char_span` + `max_buffer_size`) and one scaling
problem (O(n²) per stream) that should be fixed before N4 is advertised as production-ready for
its headline TTS/LLM-streaming use case. None of these block N1/N2/N5.

---

## 2. Confirmed findings

All findings below were reproduced empirically during this review (not just read).

| Item | Severity | Dimension | File | Issue | Fix |
|------|----------|-----------|------|-------|-----|
| N4 | major | correctness | `stream_segmenter.py:268-283`, `flush():148-166` | `char_span=True` + `max_buffer_size` overflow silently resets span offsets to 0, producing overlapping spans where `full[start:end] != sent` | Persist a running base offset across internal flushes (or don't reset offsets on overflow); add a `char_span`+`max_buffer_size` round-trip regression test |
| N4 | major | api-dx | `README.md:60-75, 200` | `StreamSegmenter` is a top-level public export but appears **nowhere** in the README; zero discoverability | Add a "Streaming segmentation" subsection + a "Coming from pysbd" bullet, link `examples/streaming_to_tts_recipe.py` |
| N2 | major | tests | `tests/regression/test_regression_gate.py` | No negative/drop-detection test — the gate is never exercised in its **failing** direction; a flipped `>=` or broken `score_corpus` would leave all 25 green | Add a test that proves the predicate fires: `now = base - tol - 0.1` fails while `now = base - tol` passes; assert `tolerance_for()` returns tightened 0.0 for golden_rules/ud_zh_gsd vs DEFAULT for unknown |
| N4 | major | perf | `stream_segmenter.py:116` | `feed()` re-segments the whole growing buffer every call → O(n²) over a stream (measured: 4.8 → 8.4 → 16 µs/tok as tokens double — textbook quadratic) | Compact buffer at confirmed interior boundaries and rebase offsets, or segment only the unstable tail per feed; add a flat-per-token-cost scaling test |
| N5 | minor | api-dx | `sentencesplit/segmenter.py:85-94` | `char_span` is `.. deprecated::` in the docstring but emits **no** runtime `DeprecationWarning` (verified under `-W error`), and the directive has no version token | Emit `warnings.warn(..., DeprecationWarning, stacklevel=2)` when `char_span=True` (Segmenter + StreamSegmenter forward); add `pytest.warns`; add a version to the directive |
| cross-cutting | minor | api-dx | `sentencesplit/__init__.py` | No `__all__`; `dir()`/`import *` leak every submodule as public. The diff materially expands the curated surface (adds `StreamSegmenter`, `list_languages`) and adds `Typing :: Typed`, so a precise boundary now matters more | Add `__all__ = ["Segmenter", "StreamSegmenter", "list_languages", "TextSpan", "SegmentLookahead", "__version__"]` |
| N4 | minor | tests | `tests/test_stream_segmenter.py:31` | `_sample_for_language` falls back to `。` for ~21 of 26 langs, so per-language tests collapse to the CJK full-stop boundary and never exercise native Latin terminals + lookahead | Build Latin-script samples from a real native-boundary case that splits; reserve CJK terminals for zh/ja/CJK profiles |
| N4 | minor | tests | `tests/test_stream_segmenter.py:78` | Char-by-char/chunked tests assert only `"".join == text`; a buffer-everything-until-flush impl would still pass — the *stream* property (emission before EOF) isn't asserted for multi-chunk/per-lang paths | Assert `get_completed_sentences()` is non-empty BEFORE `flush()` for a multi-sentence multi-chunk input |
| N4 | minor | perf | `stream_segmenter.py:146` | `is_complete()`/`pending_text()` polling triggers a **second** full re-segmentation per feed, ~doubling the already-quadratic cost in the natural TTS poll loop | Cache `should_wait` from `_detect_completed()` and reuse it; resolved automatically once the buffer is compacted |
| N4 | nit | tests | `tests/test_stream_segmenter.py:361` | `test_split_mode_threaded_through` only asserts invalid-mode rejection; never proves a valid `split_mode` changes streamed output (body confirmed: just one `pytest.raises`) | Rename to `test_invalid_split_mode_raises`, or strengthen with a divergent-output assertion |

**On the blockers/majors:** The N4 `char_span`+`max_buffer_size` bug is the one true correctness
defect — it silently produces non-byte-faithful, overlapping spans that violate exactly the N5
contract the rest of the work establishes, and no test combines the two flags, so it is entirely
uncaught (reproduced: spans `[(0,23),(0,14),(14,22)]`, slices don't match `sent`). The N4 O(n²)
scaling means a long LLM/ASR response degrades badly in the headline streaming use case and should
be addressed before N4 is sold as production streaming. The N2 missing-negative-test is a
test-asset gap, not a live failure — the gate works today, but a future refactor could silently
neuter its drop-detection. The README/StreamSegmenter gap is the single most visible DX miss of the
cumulative diff. The plain-string `StreamSegmenter` output, the streaming==non-streaming contract,
N5's spans round-trip, N1, and the gate's positive path are all sound.

---

## 3. By item

**N1 — discovery + metadata + zero-dep guard.** Solid and low-risk. `list_languages()` exported
and tested; `pyproject.toml` adds `Typing :: Typed`, Development Status, and keywords;
`tests/test_zero_dependencies.py` confirms a bare `import sentencesplit` pulls in no non-stdlib
module (also re-verified for Hypothesis and StreamSegmenter — both stay out of the import graph).
The new `Typing :: Typed` classifier raises the bar for the missing `__all__` (cross-cutting minor).

**N2 — hermetic regression gate.** Well-built: pure-Python, runs as ordinary pytest (no separate
wiring), reuses the cross-library EM/F1 scorer, ships a vendored UD gold subset + the English Golden
Rules, and has a reviewed `--update-baseline` governance flow (`gate/GOVERNANCE.md`). Anti-vacuity
guards (`test_gate_covers_every_baseline_corpus`, `test_golden_rules_never_regress`) are good. The
one real gap: the drop-detection math is never tested in its failing direction (major, tests).

**N5 — byte-faithful spans.** This run made `segment_spans()` the canonical lossless API with a
CI-gated round-trip contract (exact slices, contiguous tiling, no gaps/overlaps, reassembly ==
source) across clean and dirty inputs (ZWSP/NBSP/BOM/combining/RTL), 329 cases over all 26
registered codes. It fixed a real latent bug — `_match_spans()` dropped whitespace-/zero-width-only
input so `segment_spans("\n")` returned `[]` — by emitting a trailing-remainder span; the lossy
plain `segment()` path is unchanged. *Design call (RTL/directional-format stripping):* deliberately
NOT added to the zero-width strip set, because `segment_spans()` is the byte-exact lossless API and
directional chars carry rendering semantics; `test_plain_segment_does_not_strip_directional_format_chars`
locks it. Reasonable. Only soft spot: the deprecation is docstring-only with no runtime warning
(minor).

**N4 — StreamSegmenter.** New `stream_segmenter.py` wraps the tested `segment_with_lookahead()` /
`should_wait_for_more()` primitives; purely additive (segmenter.py byte-identical to HEAD). API
matches spec (`feed`, `get_completed_sentences`, `pending_text`, `is_complete`, `flush`, `reset`).
*Design calls:* (1) buffer is the single source of truth, re-segmented whole each feed; interior
boundaries are permanent, the volatile trailing segment is gated by `buffering_mode`
(`conservative`/`balanced` wait for lookahead, `aggressive` trusts terminal punctuation —
`balanced`==`conservative` for emission timing); (2) an `_emitted_chars` watermark + `_emit()` delta
reconciliation guarantees streaming==non-streaming exactly for whole/realistic feeds and
text-preservation for char-by-char; (3) `max_buffer_size` force-flushes the tail to bound memory.
The buffering and watermark design are sound for plain-string output. The two problems are the
`char_span`+overflow correctness bug and the O(n²) scaling (both major, above), plus the
test-strength and README gaps.

---

## 4. Adversarial filter

13 candidate findings were raised; **3 were refuted** during verification and are NOT reported as
issues. The 10 above all survived empirical reproduction on this box (span-overlap repro, scaling
measurement, `-W error` deprecation check, `dir()` introspection, grep-confirmed test/README gaps).
The confirmed set is severity-ordered; confidence is high on all majors and most minors (one minor
medium).

---

## 5. Next steps

Per-branch merge recommendation (everything already stacks onto `feat/now-all`; nothing is pushed):

1. **N1, N2, N5 — ready to ship.** Land as-is. Optionally fold in the quick wins before merge:
   add `__all__` to `__init__.py`, emit the `char_span` `DeprecationWarning` (N5), and add the N2
   negative drop-detection test. These are small and self-contained.
2. **N4 — fix before advertising as production streaming.** Fix order:
   1. The `char_span` + `max_buffer_size` span-corruption bug (major correctness) + a regression
      test combining the two flags against the full span contract.
   2. The O(n²) `feed()` scaling — compact the buffer at confirmed boundaries (this also fixes the
      `is_complete()` double-segmentation minor) + a flat-per-token-cost scaling test.
   3. Add the README "Streaming segmentation" subsection (major DX).
   4. Strengthen the per-language/char-by-char/`split_mode` tests (minors/nit).
3. Re-run the full suite + gate + Golden Rules after each fix; the N2 gate will guard against any
   per-language EM/F1 drift introduced by the N4 buffer-compaction refactor.

Reminder: all four items are integrated on `feat/now-all` (`20a8d4c`); the worktrees were removed
and pruned; `main` and `origin` are untouched until you explicitly push.

---

## Fix pass

Fix pass applied on `feat/now-all` (HEAD `f68ed73`) against the 10 confirmed findings in section 2.
All clusters that had a safe mechanical fix were applied test-first, each guarded by a full-suite +
N2-gate + zero-dep + Golden-Rules check (commit-or-revert). Nothing was pushed; `main`/`origin`
untouched.

### 1. Summary

- **6 of 6 fixable clusters applied; 0 skipped/regressed.** Every cluster landed with its own commit.
- **Post-fix status (all green):** full suite **1658 passed / 8 xfailed** (`pytest -q --ignore=tests/test_spacy_component.py`); regression gate **29 passed** (was 25); zero-dependency guard **3 passed**; English **Golden Rules 47/48** — the historical baseline, unchanged from `origin/main` (the one miss predates this work and was not touched). `ruff check` + `ruff format --check` clean.
- **No targeted finding remains unresolved.** All 10 confirmed findings from section 2 are genuinely fixed (code-read and several empirically re-verified, not just covered by a test's presence).
- **2 deferred decisions** were intentionally NOT auto-fixed because they require a human product/release call (see section 4 below). The mechanical halves were applied; only the policy halves are deferred.

### 2. Fixes applied

| Cluster | Risk | Files | Test added | Commit |
|---------|------|-------|------------|--------|
| all-export-surface | low (surface-only) | `sentencesplit/__init__.py`, `tests/test_zero_dependencies.py` | `test_public_surface_matches_all` | `84676cf` |
| gate-negative-test | low (test-only) | `tests/regression/test_regression_gate.py` | 4 drop-detection unit tests on the EM predicate + tolerance map | `a6e4374` |
| readme-streaming | none (docs-only) | `README.md` | — | `ce17eb2` |
| stream-test-quality | low (test-only) | `tests/test_stream_segmenter.py` | native-Latin-period, pre-flush-emission, split_mode-divergence | `384dde7` |
| char-span-deprecation-warning | medium (runtime behavior) | `sentencesplit/segmenter.py`, `sentencesplit/stream_segmenter.py`, `tests/regression/test_char_span_deprecation.py` | `tests/regression/test_char_span_deprecation.py` (5 tests) | `e3dc6b1` |
| stream-buffer-compaction | high (correctness + perf) | `sentencesplit/stream_segmenter.py`, `tests/test_stream_segmenter.py` | 6 tests (overflow spans, flat-per-token cost, compaction contract) | `f68ed73` |

- **all-export-surface** — Added `__all__ = ["Segmenter", "StreamSegmenter", "list_languages", "TextSpan", "SegmentLookahead", "__version__"]` so `import *` and `dir()` stop leaking submodules; a guard test pins the surface to exactly those six names.
- **gate-negative-test** — Closed the gate's untested failing branch with pure-unit tests proving a drop one tenth past tolerance violates the EM predicate while a drop exactly at tolerance passes, and that `golden_rules`/`ud_zh_gsd` are zero-tolerance (catch a 0.1pp dip); confirmed via a mutation probe that flipping the `>=` inverts them.
- **readme-streaming** — Added a "Streaming segmentation" subsection (feed/get_completed_sentences/flush loop, the streaming==non-streaming contract, buffering params) plus a "Coming from pysbd" anchor link to the runnable `examples/streaming_to_tts_recipe.py`.
- **stream-test-quality** — Fixed the `_sample_for_language` helper so 14 Latin-script languages exercise the native `.` terminal + lookahead path instead of collapsing to `。`; added pre-flush emission and `split_mode` end-to-end divergence assertions.
- **char-span-deprecation-warning** — `char_span=True` now emits a real `DeprecationWarning` (`stacklevel=2`, points at the user's call site) from both `Segmenter` and `StreamSegmenter`, exactly once; the package had no `import warnings` at all before. Versioned the directive `.. deprecated:: 0.0.5` (next patch release).
- **stream-buffer-compaction** — Replaced whole-buffer re-segmentation with a persistent `_base_offset` + interior-boundary compaction: per-token cost is now flat (was textbook O(n²)); `char_span` spans stay byte-faithful and monotonic through `max_buffer_size` overflow (overflow no longer resets offsets to 0); `is_complete()` reuses the cached lookahead verdict instead of re-segmenting.

### 3. Skipped

None. No cluster regressed and no fixable finding was left without a safe fix. The only items not
mechanically completed are the two policy decisions below — their code-level halves were applied; the
remaining open questions are product/release judgments, not skipped fixes.

### 4. Deferred decisions (NOT auto-fixed — need a human call)

1. **`max_buffer_size` overflow semantics during compaction.** The span-reset bug and the O(n²) fix
   were clustered (shared buffer-management root cause) and both are fixed, but *how* overflow should
   behave once a persistent base offset exists is a contract decision. Today `_enforce_max_buffer_size()`
   force-flushes the pending tail (possible mid-sentence cut) and `flush()` resets `_base_offset` to 0.
   **Question:** after overflow, should the stream continue as one logical stream with monotonic
   stream-relative spans (compact + rebase, never reset), or keep the current force-flush-and-reset
   semantics — i.e. is overflow a hard stream boundary or a transparent memory-bound compaction?
2. **`char_span` deprecation: removal version / whether to deprecate at all.** The warning now fires
   and the directive carries `.. deprecated:: 0.0.5`, but the removal timeline and the deeper question
   stand. **Question:** what version goes in the directive and what is the intended removal version (or
   is removal explicitly NOT planned and `char_span` kept indefinitely as a `segment_spans()` alias),
   and should the warning fire on every `char_span=True` construction (current behavior) or be
   one-time?

### 5. Next steps

- Branch state: all 6 fix commits sit on `feat/now-all` on top of the N1+N2+N5+N4 integration
  (`84676cf` → `f68ed73`). Tree is clean of tracked changes; only pre-existing untracked
  `.codex`, `.claude/workflows/*`, `analysis/*.md` artifacts remain.
- **Nothing is pushed.** `main` and `origin` are untouched. Push/PR only on explicit request.
- Before merge, resolve the 2 deferred decisions above (overflow contract + `char_span` removal
  policy); both are documentation/policy, not blocking code work. After that, `feat/now-all` is
  ship-ready: suite/gate/zero-dep/Golden-Rules all green.
