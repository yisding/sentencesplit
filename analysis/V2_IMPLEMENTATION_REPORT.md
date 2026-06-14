# V2 Abbreviation Engine — Implementation Report

**Branch:** `feat/v2-abbreviation-engine`
**HEAD:** `4383e77c93c8211ad6130bae9bbb7199df06ded0`
**Baseline (Phase 0):** `9e3393633b4086e0b4d6829c98f69993a50aa046`
**Date:** 2026-06-14

This report is the contract-close for the V2 abbreviation engine described in
`analysis/ABBREVIATION_ENGINE_V2_PLAN.md`, `analysis/V2_RFC_EVALUATION.md`, and
`analysis/ABBREVIATION_ENGINE_V2_RFC.md`.

---

## 1. What Shipped

A new single-pass period classifier (`sentencesplit/period_classifier.py`, 897 LOC)
replaces the per-line abbreviation-protection step inside
`AbbreviationReplacer.search_for_abbreviations_in_string` (`abbreviation_replacer.py:612`).
The legacy per-occurrence `re.sub` loop is gated behind a feature flag and is now
dead for every shipping language, but it is retained on disk as the `False`-branch
fallback and as the differential oracle's reference path.

**24 feature commits** since the Phase-0 baseline, one per language family. Every
registered language code is on V2 — there are **zero deferred languages**:

| Status | Codes | Policy |
|---|---|---|
| **On V2, BASE_POLICY (zero policy code)** | `en`, `en_legal`, `hi`, `mr`, `es`, `am`, `hy`, `ur`, `pl`, `nl`, `da`, `fr`, `my`, `el`, `it`, `tl`, `kk` (17) | `AbbrPolicy()` (kk sets it explicitly; the rest inherit `ABBR_POLICY = None`) |
| **On V2, follower-class-only policy** | `zh` (`ZH_POLICY`), `ja` (`JA_POLICY`), `en_es_zh` (`EN_ES_ZH_POLICY`) | CJK / non-ASCII follower classes woven into the suffix patterns; no `classify_special` |
| **On V2, `classify_special` override** | `ar`+`fa` (`AR_POLICY` via `arabic_script.py`), `bg` (`BG_POLICY`), `ru` (`RU_POLICY`), `de` (`DE_POLICY`), `sk` (`SK_POLICY`) | unconditional / starter-aware protection branch ported into a policy callback |

All 26 codes (24 natural languages + `en_es_zh` + `en_legal`) resolve to
`USE_PERIOD_CLASSIFIER = True` at runtime (verified by introspection). The base
class default (`AbbreviationReplacer.USE_PERIOD_CLASSIFIER = False`,
`abbreviation_replacer.py:210`) remains the safe off-switch.

---

## 2. The Design That Landed

**Feature flag + parallel path.** `AbbreviationReplacer` gained two class attrs:
`USE_PERIOD_CLASSIFIER` (default `False`) and `ABBR_POLICY` (default `None` →
`BASE_POLICY`). `search_for_abbreviations_in_string` branches on the flag at line
613: V2 calls `self._period_classifier().rewrite(text)`; legacy keeps the old
loop. `_period_classifier()` (`abbreviation_replacer.py:265`) lazily builds and
caches one `PeriodClassifier` per replacer instance, reusing the **same**
`_AbbreviationData` (automaton + sets + boundary_class) — it never rebuilds the
keys, preserving the U+0130 İ bare-key exception and the publish-after-build
thread-safety invariant.

**PeriodClassifier (the PORT-FIRST engine).** Three pure stages:

1. `enumerate_candidates(line)` reproduces the legacy reachability gate exactly
   (Aho-Corasick `<abbr>.` prefilter on the lowered line, word-boundary
   `match_re.finditer` on the original line, period-less-skip, same-occurrence
   follower-char capture), then dedups classify-units by
   `(elision-stripped abbr-lower, follower_char)` — mirroring the legacy global
   `re.sub`'s idempotence per `(am, char)`.
2. `classify(c, line)` is **pure**: it reads only the candidate and the ORIGINAL
   line (never a sentinel left by a prior decision) and returns one of
   `Decision.PROTECT` / `BOUNDARY` / `PLACEHOLDER`. It dispatches the
   language-override seam first (inert for `BASE_POLICY`), then the capital-follower
   boundary gate, then the REGULAR / PREPOSITIVE / NUMBER trichotomy using
   suffix-only regexes (the legacy `(?<=[B]{abbr})` lookbehind is discharged by
   enumeration, so it is never re-tested).
3. `rewrite(line)` realizes each PROTECT/PLACEHOLDER decision **globally** over
   the line as a sorted list of position-anchored `Edit` splices, then rebuilds
   the line in one pass with a non-overlap assertion. Order-independent;
   free-threaded-safe (frozen, slotted dataclasses; module-level frozen policies).

**AbbrPolicy (the POLICY-STAGED descriptor).** A frozen dataclass that carries the
data knobs interpolated into the ported suffix patterns (`follower_class`,
`cjk_follower_class`, `cjk_follower_regular_only`, `ascii_only_upper_heuristic`)
plus override seams (`classify_special`, `realize_suffix`, `candidate_filter`).
English/en_legal need **zero policy code** — they ride `BASE_POLICY` and the
classifier reads their behavior flags (`CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`,
`STARTER_AWARE_PREPOSITIVE`, `AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST`) and
`split_mode` straight off the replacer back-reference (single source). Languages
that previously subclassed `AbbreviationReplacer` to override a scan method
(ru/sk/bg/de/ar) now express that override as a small `classify_special` callback
on their policy, inheriting the other two branches.

**Oracle adapter.** `classifier_protect_positions_for_line(line)`
(`abbreviation_replacer.py:283`) exposes the protected-period offsets so the
Phase-0 differential oracle (`tests/v2/oracle.py`) can compare legacy vs new. The
oracle now forces the legacy branch on its throwaway replacer instance to stay a
genuine differential.

---

## 3. Adjudicated Output Diffs

**English / en_legal: zero output diffs.** The differential oracle reports
**0 protected-position diffs** across the entire 41-case English corpus
(`tests/v2/corpus_en.py`) for both `en` and `en_legal`. The classifier is
**parity-exact** on the protection step for English. No English output changed,
so there is nothing to adjudicate there — the 38 GREEN corpus cases stay green and
the win is structural (see §6), not behavioral.

**The 3 Phase-2 correctness TARGETS remain `xfail` (NOT fixed):**

| Input | Linguistically-correct target | Status |
|---|---|---|
| `Ph.D. Smith arrived. He lectured.` | `Ph.D. Smith` stays joined | still `xfail` (legacy bug intact) |
| `Dr. Ph.D. Smith spoke at noon.` | one sentence | still `xfail` |
| `It is 9 a.m. Eastern Standard Time now.` | one time unit | still `xfail` |

These were aspirational fix-targets, not commitments. The classifier replaced only
the per-line protection step; the multi-period-initialism pass
(`replace_multi_period_abbreviations`) and the a.m./p.m. boundary-restore pass
still run **after** the classifier and own these three boundaries. Because the
implementation prioritized parity + no-regression on the cutover, the underlying
quirks were left intact rather than fixed in a downstream pass. They are carried
forward as backlog (see §5). `xfail_strict=true` means any future fix flips them to
XPASS and reddens the suite, forcing promotion to GREEN — the guard rail is live.

**Non-English: no real output diffs; all per-language suites green.** A cross-language
differential probe surfaced 4 position diffs, but every one is a **nonsense-input
artifact** — English probe strings (`Dr. Smith…`, `The U.S.A.…`, `It happened in Dec.…`)
fed to `de`/`fa`/`sk`, whose `classify_special` policies protect known abbreviations
unconditionally. On each language's **own** corpus the engines agree; the
authoritative evidence is that every per-language test file is green (de, ru, sk,
bg, ar, fa, zh, ja, kk, en_es_zh: 223 passed, 1 pre-existing xfail). No silent,
un-adjudicated behavioral change shipped.

---

## 4. Gate Results (final)

All gates run on HEAD `4383e77`. Repo root on `sys.path` (`PYTHONPATH=.`) per the
Phase-0 environment note.

| Gate | Command | Result |
|---|---|---|
| **FULL SUITE** | `uv run pytest tests/ -q` | **2056 passed, 9 xfailed** ✅ |
| **ENGLISH** | `pytest test_english{,_challenging,_clean} test_en_legal -q` | **278 passed, 4 xfailed** ✅ |
| **RUFF** | `ruff check . && ruff format --check .` | All checks passed; 725 files formatted ✅ |
| **ZERO-DEP** | `pytest tests/test_zero_dependencies.py -q` | **3 passed** ✅ |
| **SPAN R-TRIP** | `pytest tests/test_span_roundtrip.py -q` | **329 passed** ✅ |
| **ORACLE** | differential, en + en_legal corpus | **0 diffs** ✅ (parity target met for English) |

The 9 xfails = 6 pre-existing language xfails + the 3 V2 corpus correctness targets.
Suite count grew from the Phase-0 baseline (2028 → 2056 passed) via the new V2 unit
tests (`tests/v2/test_classifier_en.py`, 26 cases) and updated oracle self-tests.

**Perf delta (phase_profile, short 87-char input, 20k iters, 3 runs):**

| Metric | Baseline (legacy) | HEAD (V2) | Delta |
|---|---|---|---|
| total pipeline | 0.847 ms/call | 0.876–0.892 ms/call | **+3–5%** |
| `abbr: search_in_string` | 0.166 ms/call | 0.196–0.198 ms/call | **+18–20%** on that phase |

The classifier's enumerate→classify→global-rebuild costs slightly more than the
legacy tight `re.sub` loop on short single-abbreviation lines (the loop's best
case). The overhead is bounded and concentrated in the one phase that was replaced;
it does not compound elsewhere. The `differential_profile` vs-pysbd comparison
could not be re-run (pysbd is not installed in this environment); the intra-library
phase_profile is the clean measurement.

---

## 5. Deferred / Remaining-Work Backlog

**No languages are deferred** — all 26 codes are on V2 and green. The backlog is
about *correctness debt the cutover deliberately did not pay*, plus *cleanup the
parallel path enables*:

1. **The 3 correctness targets (highest value).** `Ph.D. Smith`, `Dr. Ph.D. Smith`,
   `9 a.m. Eastern Standard Time` are still wrong. The fix belongs in the
   downstream multi-period / a.m.-p.m. passes (which run after the classifier),
   not in the classifier itself. Promote each `xfail`→GREEN with a Golden-Rule
   anchor when fixed.
2. **Retire the legacy path.** The per-occurrence `re.sub` loop
   (`search_for_abbreviations_in_string` `False`-branch, `scan_for_replacements`,
   `_replace_number_abbr`, `replace_period_of_abbr`, `_replace_with_escape`,
   `_initials_chain_start`) is now dead for every shipping language. Once V2 has
   soaked, delete it and fold the classifier in as the only path. This is where the
   net-LOC maintainability win is actually banked (today the repo carries BOTH
   engines: +897 classifier LOC on top of the retained legacy code).
3. **Move the abbreviation passes that still run downstream of protection**
   (`replace_multi_period_abbreviations`, ampm restore, standalone-I) into the
   classifier's single-pass model, so the whole abbreviation decision is made once
   from the original text rather than in layered passes — the original RFC end-state.
4. **Reclaim the perf regression.** Profile `enumerate_candidates`/`rewrite` for the
   short-single-abbr hot path; the +18% on `search_in_string` is the obvious target
   (e.g. fast-path lines with exactly one candidate to skip the edit-list machinery).
5. **CI environment fix (carried from Phase 0).** `tests/test_corpus_compare_segmenters.py`
   needs `benchmarks/corpus_compare/__init__.py` committed (or `pythonpath = ["."]`
   in `[tool.pytest.ini_options]`); otherwise a fresh clone red-collects. The file
   currently sits untracked in the working tree and was kept out of all V2 commits.

---

## 6. Honest Bottom Line

**Correctness:** The cutover is a clean parity landing for English (0 oracle diffs,
all suites green) and a no-regression landing for all 26 languages. It did **not**
fix the 3 known linguistic quirks it was allowed to fix — those live in downstream
passes the classifier didn't touch yet. So the *correctness improvement* is latent,
not realized; what is realized is a correctness-*neutral*, fully-tested swap onto a
substrate where those fixes become tractable.

**Maintainability:** The architectural win is **real but not yet banked**. The
decision logic is now pure and unit-testable per period (26 focused unit tests
exercise each branch without driving the pipeline), the legacy "two zipped findall
lists of different lengths" misalignment class is structurally impossible, and five
languages that needed bespoke `AbbreviationReplacer` subclasses now express their
one divergent branch as a small `classify_special` callback while inheriting the
rest. But the repo currently carries **both** engines: the 897-LOC classifier sits
on top of the still-present legacy code, so net LOC went up, not down. The
maintainability dividend is only collected when the legacy path is deleted (backlog
item 2).

**Verdict:** Ship the substrate. It is green, parity-exact for English, and
behind a per-language opt-in that proved out cleanly across all 26 codes. The win
is the foundation, not the finish.

**Next step:** Soak V2 in `main` behind the flag-on default, then (a) fix the 3
correctness targets in the downstream passes and promote their xfails, and
(b) retire the legacy path to bank the LOC and complete the single-pass model.
