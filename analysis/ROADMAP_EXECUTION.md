# ROADMAP_EXECUTION.md — living execution backlog

The operational backlog for the LEVEL_UP_PLAN roadmap (see
`analysis/LEVEL_UP_PLAN.md` §4 "Roadmap" and §5 "Accuracy & evaluation plan").
This file tracks what is done, the dependency-ordered queue of remaining items,
per-item specs, how to run the next item, and the cross-cutting stability
contract that must be reconciled before the public leaderboard.

Last updated: 2026-05-30.

---

## 1. Status

### Done

- **N1 — list_languages + metadata + zero-dependency import test.** Implemented
  on a separate branch (per task brief). Public language enumeration / metadata
  plus a test asserting the package imports with zero runtime dependencies.

- **N2 — Hermetic CI regression gate.** Implemented this run.
  - Commit: `2746ff5` (`test(regression-gate): add hermetic CI gate scoring
    sentencesplit vs committed gold`).
  - Branch left for review: `feat/regression-gate`.
  - Lives at `tests/regression/test_regression_gate.py` +
    `tests/regression/gate/` (`gate_scoring.py`, `regen_gate.py`,
    `baseline.json`, `gold/ud_gold_subset.json`, `GOVERNANCE.md`). Reuses
    `benchmarks/corpus_compare/run_compare.py::boundary_f1` so the gate and the
    Tier-2 comparison measure the same thing.
  - **Verify verdict: PASS.** Suite green; runs on this aarch64 box; hermetic
    (pure Python, no Ruby/NLTK/network/native wheels); catches a planted
    single-language regression (`return False` in `_is_initials_name`), failing
    red and naming Dutch.
  - Sensitivity note (not a defect): the planted regression dropped
    `ud_nl_alpino` by exactly 3.4pp (66.7 → 63.3), landing exactly on the Dutch
    tolerance; the strict `now >= base - tol` comparison still fails it
    deterministically (IEEE-754: `63.3 >= 63.30000000000001` is `False`). By
    design, a sub-one-unit dip (<3.4pp) in a single n=30 corpus would pass — the
    gate's per-language EM sensitivity floor is ~one unit (3.3pp). This matches
    the documented tolerance rationale in `tests/regression/gate/GOVERNANCE.md`.

N2 is the gate that guards every behavior-changing item below.

---

## 2. Execution order

Dependency-ordered checklist. Check an item off when its branch is merged.

### Now

- [ ] **N5** — Span-faithful round-trip contract + property tests (S-M, now, ready) — depends on: none
- [ ] **N4** — StreamSegmenter (first-class streaming) (S-M, now, ready) — depends on: none
- [ ] **N1b** — `extra_abbreviations=` constructor argument (M, now, needs-decision) — depends on: N2

### Next

- [ ] **N6** — Publish versioned public leaderboard with standard metrics + credibility discipline (L, next, needs-decision) — depends on: N2
- [ ] **N9** — Add Portuguese; close Dutch/German abbreviation gap (L, next, needs-external) — depends on: N2
- [ ] **N10** — Offline/air-gapped legal-RAG niche: triage 36 divergences, harden en_legal, citation-faithful recipe (M, next, ready) — depends on: N2, N5, N6

### Later

- [ ] **N11** — Open-quote / multi-sentence boundary suppression (1/3 → 3/3) (M, later, needs-decision) — depends on: N2
- [ ] **N12** — Deepen thin-tail languages + new-language scaffold (L, later, needs-external) — depends on: N2
- [ ] **N13** — Optional structure-aware pre-pass for markdown/code (gated behind `doc_type='markdown'`) (L, later, needs-decision) — depends on: none

---

## 3. Per-item specs

### N5 — Span-faithful round-trip contract + property tests

- **Kind / effort / horizon / ready:** dev-tests / S-M / now / ready (no deps).
- **Summary.** Enforce a CI-gated, byte-for-byte round-trip contract for
  `segment_spans()`: every sentence must map to an exact `[start,end)` slice of
  the source, and reassembling all spans reproduces the source verbatim. Add
  Hypothesis property tests (dev-only dependency) across clean and dirty inputs
  (ZWSP/NBSP/BOM/combining marks/RTL markers), and retire the redundant
  `char_span` flag by making `segment_spans()` the canonical spans API.
- **Files.**
  - `sentencesplit/segmenter.py`
  - `sentencesplit/processor.py`
  - `sentencesplit/utils.py`
  - `tests/conftest.py`
  - `tests/test_segmenter.py`
  - `tests/test_span_roundtrip.py` (new)
- **Public API.** `segment_spans() -> list[TextSpan]`;
  `Segmenter.__init__(char_span=...)` flag deprecated but maintained for
  backward compatibility.
- **Test plan.**
  1. Property-based round-trip (Hypothesis) across all 24 languages + `en_es_zh`:
     `all(text[s.start:s.end] == s.sent ...)` AND
     `text == "".join(s.sent for s in segment_spans(text))`. Generated inputs:
     ASCII, Latin accents, CJK, Arabic (RTL), Devanagari, Armenian, Greek,
     Burmese, Persian, Korean, Bulgarian, hybrid `en_es_zh`; split across
     boundaries with leading/trailing/interior whitespace, newlines, empty.
  2. Dirty-input fixtures (explicit, non-generated): ZWSP U+200B, NBSP U+00A0,
     BOM U+FEFF, combining marks (U+0301 on 'a'), RTL marker U+202E. Verify
     spans non-empty, offsets cover whole source, no overlaps.
  3. Span consistency `segment()` vs `segment_spans()`: `char_span=False`
     returns str with `"".join(segment(text)) == text`; `char_span=True` returns
     `TextSpan` with `"".join(s.sent ...) == text`; both match `segment_spans()`.
  4. Bounds/overlap/gap: `0 <= start < end <= len(text)`; no overlaps; no gaps
     (first start 0, last end `len(text)`).
  5. Lock existing manual checks in conftest:
     `test_segment_spans_preserve_leading_whitespace`, `test_zh_corner_quote_spans`,
     `test_zh_char_spans`, `test_ja_char_spans`.
  6. Edge cases: empty/whitespace-only input; single vs multi-sentence;
     leading/trailing whitespace vs interior punctuation; zero-width char at
     boundary; multiple zero-width chars in sequence; combining marks on
     punctuation.
- **Risks.**
  - Hypothesis shrinking may reveal latent bugs in `_match_spans()` /
    `_strip_zero_width_chars()`; fixing revealed bugs is on the critical path.
  - Hypothesis is a new **dev-only** dependency — add to
    `[project.optional-dependencies] dev` only; core must stay zero-dep.
  - `char_span` deprecation is a minor breaking change for explicit callers;
    plan a 0.x bump and update README/release notes.
  - `_match_spans` (clean=False) vs `_strip_zero_width_chars` (clean=True path)
    may diverge on dirty input; document and test the interaction.
  - RTL marker U+202E and directional formatting chars are not in the
    `_ZERO_WIDTH_CHARS` sets — decide whether to strip them; validate against the
    existing suite before committing.
- **Dependency / readiness:** ready. No external input; no decision blocker. The
  one in-scope design call (whether RTL/directional formatting chars get stripped
  from plain segments) can be made during implementation and validated against
  the suite.

### N4 — StreamSegmenter (first-class streaming)

- **Kind / effort / horizon / ready:** additive / S-M / now / ready (no deps).
- **Summary.** A stateful `StreamSegmenter` wrapping the tested
  `segment_with_lookahead()` / `should_wait_for_more()` primitives. Accepts
  text/token deltas, emits completed sentences once their boundary is stable (via
  lookahead probes), buffers the unstable tail, defaults to conservative
  buffering. Ship a latency-to-first-stable-sentence benchmark and a
  streaming-to-TTS recipe for voice agents.
- **Files.**
  - `sentencesplit/stream_segmenter.py` (new)
  - `tests/test_stream_segmenter.py` (new)
  - `benchmarks/streaming_latency_benchmark.py` (new)
  - `examples/streaming_to_tts_recipe.py` (new)
  - `sentencesplit/__init__.py`
- **Public API.**
  ```
  class StreamSegmenter:
    def __init__(language="en", clean=False, char_span=False,
                 split_mode="balanced", buffering_mode="conservative")
    def feed(delta: str) -> None
    def get_completed_sentences() -> list[str | TextSpan]
    def pending_text() -> str
    def is_complete() -> bool
    def flush() -> list[str | TextSpan]
    def reset() -> None
  ```
  Exported from `sentencesplit.__init__`.
- **Test plan.**
  1. Unit: `feed()` with chars/tokens/multi-sentence chunks; ordered
     `get_completed_sentences()`; accurate `pending_text()`; `is_complete()`
     reflects tail stability; `flush()` emits stable+unstable tail; `reset()`
     clears state; `char_span=True` returns `TextSpan` with correct offsets;
     `aggressive` emits sooner, `conservative` later.
  2. Integration: all 24 `LANGUAGE_CODES` with lookahead probes;
     streaming==non-streaming (`feed(full).flush() == segment(full)`);
     abbreviation handling (Dr. delays, capital triggers); decimal continuation
     (GPT 3. 1 vs GPT 3. Next); empty/None/whitespace/very-long-tail edge cases.
  3. Latency benchmark: time-to-first-stable-sentence; compare buffering modes;
     median/p95/p99 on standard corpora.
  4. Regression: streaming output matches `segment_with_lookahead()` golden rules;
     `clean=True` disallows `char_span` (same constraint as Segmenter);
     per-language probe coverage.
  5. Recipe test: mock LLM output fed incrementally to TTS; no duplication, no
     dropped text, correct span ordering.
- **Risks.**
  - Premature partial emission corrupts TTS → default conservative; CI-validate
    per-language probe coverage; test all lookahead edge cases.
  - Unbounded tail on pathological input → optional `max_buffer_size` with
    overflow strategy; document typical per-language bounds.
  - Span corruption in `char_span=True` if delta merging is wrong → reuse
    `_match_spans`; test against corpus_compare corpora with `char_span=True`.
  - Per-char `_segment_result()` perf regression → batch deltas internally;
    expose `flush()` as explicit sync point.
  - Sub-sentence granularity mismatch → document that it emits full sentences
    only; point sub-sentence flows at an external tokenizer.
- **Dependency / readiness:** ready. Builds on existing tested lookahead
  primitives; no external input. Soft synergy with N5 (`char_span` span fidelity)
  but not a hard dependency.

### N1b — `extra_abbreviations=` constructor argument

- **Kind / effort / horizon / ready:** behavior-change / M / now / needs-decision
  / depends on N2.
- **Summary.** Add `extra_abbreviations=[...]` (default `None`) as a first-class
  Segmenter constructor argument letting users extend any language's abbreviation
  list without subclassing. Feed the caller list into the existing Aho-Corasick
  automaton, guarding cache invalidation so two Segmenters with different
  `extra_abbreviations` get independent cached `_AbbreviationData`. Cache
  isolation correctness is the real work.
- **Files.**
  - `sentencesplit/segmenter.py`
  - `sentencesplit/abbreviation_replacer.py`
  - `sentencesplit/processor.py`
  - `sentencesplit/language_profile.py`
  - `tests/test_segmenter.py`
  - `tests/test_abbreviation_replacer.py`
- **Public API.**
  `Segmenter.__init__(language, clean=False, doc_type=None, char_span=False,
  split_mode='balanced', extra_abbreviations=None)`. `extra_abbreviations` is an
  optional `list[str]` merged into the language's `Abbreviation.ABBREVIATIONS`
  before automaton construction. Default (`None`) is unchanged.
- **Test plan.**
  1. Regression baseline unchanged: `None` vs `[]` on all 24 languages
     (spot-check en/es/zh against `scoreboard.baseline.json`); N2 gate must not
     regress.
  2. Cache isolation: two `Segmenter("en")` with different lists do not share
     cached `_AbbreviationData`; inspect cache identity separation; Processor
     receives the correct merged automaton.
  3. Functional: `["myabbr"]` protects the period in
     "He is myabbr. He continues."; baseline splits it without the extra list.
  4. Edge cases: `[]` == `None`; duplicate with base (`["dr"]`) dedups; case
     (`["MYABBR"]` lowercased to canonical `myabbr`); prepositive/number_abbr
     interaction (extras are plain, never prepositive — deliberate scope
     boundary); Unicode/script (`["мин."]` in Russian).
  5. Integration: parameterized across `LANGUAGE_CODES.keys()` with `["zz123"]`,
     no errors/hangs/regex-compile failures.
  6. Processor/LanguageProfile thread: extras flow Segmenter → Processor →
     `abbreviations_replacer`.
- **Risks.**
  - Cache invalidation: `_data_cache` keyed by `Abbreviation` class will not
    distinguish two Segmenters with different extras → composite key
    `(class, frozenset(extra))` or per-Segmenter cache shadow.
  - Processor API creep → keep `extra_abbreviations` optional/private.
  - Automaton build is O(n) in pattern count → document as user responsibility;
    no precompilation of extras.
  - `segment_clean` bypasses some path → verify factory passes extras through.
  - Not compatible with Segmenter subclassing in the initial PR → document.
  - pysbd users expect this → README must contrast with pysbd's subclass-only
    approach.
- **Dependency / readiness:** **needs-decision** + depends on N2 (gate must catch
  any silent per-language regression from an upstream abbreviation-set mutation
  during development).
  - **Decision needed — threading strategy.** Spec recommends **Option A: pass
    `extra_abbreviations` through `Processor.__init__`** (Processor is private,
    instantiated via `Segmenter.processor(text)`; optional param is
    non-breaking). Cache key becomes
    `(lang.Abbreviation.__class__, frozenset(extra_abbreviations or []))` to
    enforce isolation. Alternatives: Option B (dynamic per-instance `Abbreviation`
    subclass with `id()`-based cache key) or a per-Segmenter cache shadow.
    Confirm Option A before implementation.

### N6 — Publish versioned public leaderboard with standard metrics + credibility discipline

- **Kind / effort / horizon / ready:** docs / L / next / needs-decision /
  depends on N2.
- **Summary.** Promote `benchmarks/corpus_compare` into a CI-generated, versioned
  public artifact tied to each release (README badge + static leaderboard page).
  Three metric sub-projects: character-level boundary-F1 (WtP/SaT format),
  stdlib reimplementation of CoNLL-18 UD Sentences-F1 (no dependency), and
  corpus-download scripts (never vendor gold text) for Ersatz/GENIA/
  MultiLegalSBD. Enforce credibility discipline: publish every overall metric
  with sample size (n=348/318/258), mixed-n caveats, per-UD-corpus n=30
  breakdowns with explicit small-sample framing, and documented
  annotation-artifact out-of-scope decisions.
- **Files.**
  - `benchmarks/corpus_compare/run_compare.py`
  - `benchmarks/corpus_compare/corpora.py`
  - `benchmarks/corpus_compare/segmenters.py`
  - `benchmarks/corpus_compare/results/scoreboard.json`
  - `benchmarks/corpus_compare/results/scoreboard.baseline.json`
  - `benchmarks/corpus_compare/results/verdicts.json`
  - `README.md`
  - `.github/workflows/python-package.yml`
  - `pyproject.toml`
- **Public API.** Leaderboard becomes a stable CI-generated artifact published on
  each release tag at a canonical URL (e.g.
  `docs/leaderboard/{version}/index.html`). Programmatic consumers read
  `scoreboard.json` from release assets / canonical CDN path. New CoNLL-18 UD-F1
  and char-level boundary-F1 fields added to `scoreboard.json` alongside existing
  `exact_match` / `boundary_f1`. Download scripts vendored code-only (never gold
  text) with cache invalidation and reproduction instructions in a `LEADERBOARD.md`.
- **Test plan.**
  1. Metric correctness: unit tests for CoNLL-18 UD-F1 (against published
     reference scorer on a golden subset, round-trip on 10 treebanks);
     char-level boundary-F1 equivalence to WtP on the Golden Rules subset.
  2. Reproducibility: full harness locally, commit baseline, cold-cache re-runs
     produce bit-identical JSON within float tolerance.
  3. Credibility discipline: automated CI audit that every leaderboard number
     carries sample size + mixed-n caveat + annotation-artifact disclaimer.
  4. Release integration: tag `v0.0.5-rc`, verify Actions generates the artifact,
     uploads to release assets, README badge points correctly.
  5. Regression gate: CI scoreboard (N2) and published leaderboard report the
     same numbers (diff check).
  6. Download-script validation: Ersatz/GENIA/MultiLegalSBD fetch (with retries +
     cache), parse, and load in `run_compare.py`.
- **Risks.**
  - Corpus licensing (CC-BY / non-commercial / academic-only) — scripts only,
    never vendor gold text; document constraints.
  - Float metric instability across platforms (aarch64 BLAS) — lock CI tolerance
    (±0.01 F1), report at 1 decimal.
  - Over-claiming undermines trust — automate caveat-check; require
    `# baseline-update` reason on every `scoreboard.json` diff.
  - Static HTML rot — canonical versioned URL path; releases page links latest +
    per-version archive.
  - N2 must land first (it has) — N6 publishes the gate externally, so the N2
    governance flow must be reviewed before N6 ships.
- **Dependency / readiness:** **needs-decision** + depends on N2.
  - **Decisions needed:** (a) canonical publish URL/hosting (GitHub Pages
    `docs/leaderboard/{version}/` vs release assets vs CDN); (b) which standard
    metrics are headline vs supplementary (CoNLL-18 UD-F1 + char-level F1 added
    alongside EM/boundary-F1); (c) the SemVer/stability policy from §5 must be
    published with this item (see Cross-cutting below) — the leaderboard is the
    public half of that contract.

### N9 — Add Portuguese; close Dutch/German abbreviation gap

- **Kind / effort / horizon / ready:** lang / L / next / needs-external /
  depends on N2.
- **Summary.** Add Portuguese (`pt`) via the TDD recipe (register in
  `LANGUAGE_CODES`, create `lang/portuguese.py` with an `Abbreviation` list, add
  regression tests). Then mine UD treebank divergences for abbreviations/patterns
  Punkt catches but sentencesplit misses in Dutch (63.3% EM, trailing Punkt 90.0%
  and pysbd 66.7%) and German (63.3% vs Punkt 73.3%). Hand-curate per case, gated
  by the N2 gate. Where misses are shared-rule issues, fix the rule, not the
  abbreviation list. Measure per-language ROI after the first pass; stop when
  curation cost exceeds gain.
- **Files.**
  - `sentencesplit/lang/portuguese.py` (new)
  - `sentencesplit/languages.py`
  - `tests/test_languages.py`
  - `tests/regression/test_issues.py`
  - `tests/regression/gate/gold/ud_gold_subset.json`
  - `benchmarks/corpus_compare/results/scoreboard.baseline.json`
  - `sentencesplit/lang/common/standard.py`
- **Public API.** `LANGUAGE_CODES["pt"]`, via `Segmenter(language="pt")` and
  `sentencesplit.languages.Portuguese`. No new methods; reuses existing
  Segmenter + `segment()` / `segment_spans()` / `segment_with_lookahead()`.
- **Test plan.**
  1. `test_languages.py`: `pt` registered; iso_code matches; abbreviations
     deduped/trimmed; PREPOSITIVE/NUMBER subsets (reuse parametrized tests).
  2. UD fixtures in `ud_gold_subset.json` include `ud_pt_*` units (n=30,
     ≤5-sentence, ≤2000-char pattern).
  3. Per-case regression tests in `test_issues.py` for each Dutch/German fix with
     before/after EM scores.
  4. Run `tests/regression/test_regression_gate.py`; if a net-positive trade is
     intended, update `baseline.json` via `gate/regen_gate.py --update-baseline`
     with rationale.
  5. Cross-library bench shows `pt` added across supported libraries.
- **Risks.**
  - UD Portuguese annotation artifacts (cf. Italian colon-as-boundary) — scope
    out, do not chase; validate on MultiLegalSBD where available.
  - n=30 curation variance — per-language ROI is critical; Dutch (trailing pysbd)
    is the target; German's smaller gap; stop on plateau.
  - N2 must land first (done).
  - Maintainer-bottlenecked hand-curation; defer shared-rule issues to
    N11/architectural work; abbreviations-only first pass.
  - Corpus sourcing: UD available; MultiLegalSBD recommended for legal
    validation; need native-speaker/corpus validation before shipping.
- **Dependency / readiness:** **needs-external** + depends on N2.
  - **External input needed:** native-speaker or corpus validation of the
    Portuguese abbreviation list and of each hand-curated Dutch/German addition.
    Do not ship coverage theater. UD treebanks are available; MultiLegalSBD is
    recommended for Portuguese legal validation.

### N10 — Offline/air-gapped legal-RAG niche

- **Kind / effort / horizon / ready:** domain / M / next / ready /
  depends on N2, N5, N6.
- **Summary.** Legal text is the single largest cross-library divergence source
  (36 cases vs 24 Golden Rules, 18 Italian). All 36 lack gold standards and are
  genuine disagreements, primarily sentencesplit/pysbd/pragmatic (aligned) vs
  punkt/syntok. Triage into curatable abbreviation/rule bugs vs structural
  ambiguities; harden `en_legal` with verified abbreviations; create a
  citation-faithful legal recipe (exact span round-trip, deterministic, zero-dep)
  positioned as an offline/air-gapped alternative to torch-based tools; publish
  on the N6 leaderboard. Validated by NUPunkt's April-2025 legal-SOTA result.
- **Files.**
  - `sentencesplit/lang/en_legal.py`
  - `tests/lang/test_en_legal.py`
  - `benchmarks/corpus_compare/results/divergences_all.json`
  - `benchmarks/corpus_compare/results/verdicts.json`
  - `sentencesplit/processor.py`
  - `sentencesplit/abbreviation_replacer.py`
  - `sentencesplit/segmenter.py`
  - `sentencesplit/utils.py`
  - `benchmarks/corpus_compare/run_compare.py`
  - `sentencesplit/lang/common/standard.py`
  - `examples/legal_citation_recipe.py` (new, per recipe)
- **Public API.** `Segmenter(language='en_legal', char_span=True)` for
  citation-faithful segmentation via `segment_spans()`; a recipe doc + example
  script showing exact span alignment for citation anchoring.
- **Test plan.**
  1. Expand `test_en_legal.py` with 20+ verified cases from the 36 divergences:
     citation abbreviations (v., F.3d, U.S.C.), court/tribunal terms (Cir.,
     Bankr., Dist.), statutory refs (Amend., 42 U.S.C. § N), parenthesized
     fragments ((a), (1)), quotation-wrapped legal text, ellipsis-heavy summaries
     (Held: ... Pp. ...).
  2. Span round-trip property tests (Hypothesis, from N5) on legal corpora —
     byte-for-byte reassembly.
  3. Cross-library bench: `en_legal` vs the 36 divergences on the Tier-2 harness;
     track EM/F1 and divergence-win count vs pysbd/pragmatic/punkt.
  4. Regression: golden rules + 10 adjudicated `en_legal` divergences in the
     gold-KEEP suite (N2 gate).
  5. Clean-input: ZWSP/NBSP/BOM fragments do not corrupt span fidelity (N5).
  6. Performance: single-threaded `segment_spans()` on legal text <5ms/KB.
- **Risks.**
  - 36 divergences lack gold; adjudicated verdicts are sparse (n=8) — anchor on
    the 10 adjudicated cases; document genuine ambiguities as locked design
    choices.
  - Hard deps on N2 (gate, landed) and N5 (span contract) — N5 must land before
    the N10 test suite ships.
  - MultiLegalSBD is non-commercial — verify license; download scripts only.
  - No legal-domain maintainer expertise — curate against the 36 only; document
    limits; accept contributions for regional/temporal gaps.
  - Quotation resplit risk in nested legal quotes — test against adjudicated
    divergences; err toward under-splitting (citation chains are valuable).
- **Dependency / readiness:** ready (spec is grounded), but **gated on N5 and
  N6** in addition to N2. Sequence: land N5 (span contract) before the N10 test
  suite; land N6 (leaderboard) before publishing N10 results externally.

### N11 — Open-quote / multi-sentence boundary suppression (1/3 → 3/3)

- **Kind / effort / horizon / ready:** behavior-change / M / later /
  needs-decision / depends on N2.
- **Summary.** Build a more discriminating signal for the open-quote resplit
  (interior terminal-punctuation count, capitalization runs inside the quote,
  quote-pair span length) validated against gold-KEEP cases. Subsumes the genuine
  Italian sub-bug (dangling-open-quote suppression) and extends to CJK quote
  continuations. The prior improve pass closed only 1/3 because the remaining
  cases are structurally indistinguishable from gold-KEEP — genuinely hard, hence
  "Later".
- **Files.**
  - `sentencesplit/processor.py`
  - `sentencesplit/between_punctuation.py`
  - `sentencesplit/lang/italian.py`
  - `sentencesplit/lang/en_es_zh.py`
  - `tests/regression/test_issues.py`
  - `benchmarks/corpus_compare/results/verdicts.json`
- **Public API.** Touches `Processor._resplit_multi_sentence_quote()`
  (processor.py ~lines 78-117), invoked from `Processor._resplit_segments()`
  (~lines 316-342). `min_interior_sentences` / `min_words` thresholds come from
  `_quote_resplit_thresholds()` (~lines 302-314), gated by `split_mode`. New
  features (punctuation count, capitalization runs, quote-pair span) are internal
  refinements — no new public surface; function signature unchanged.
- **Test plan.**
  - Unit (`test_issues.py`): expand `MULTI_SENTENCE_QUOTATION_DATA` and
    `MULTI_SENTENCE_QUOTATION_KEEP_DATA` to include Italian open-quote (never
    closed) and CJK continuation cases; add regression fixtures for the 1/3, 2/3,
    3/3 steps (one per step) so each is CI-gated.
  - Property tests (Hypothesis, from N5): round-trip invariant on resplit output
    (no text loss, valid spans).
  - Cross-library bench: re-run Tier-2 (`verdicts.json`); confirm Italian
    open-quote and CJK continuations improve without regressing English golden
    rules (case_0102, case_0110, dinah, oh_dear, case_0106, case_0080).
  - Accuracy target: 1/3 → 3/3 on the three structurally-hard cases (locate via
    `verdicts.json`, match `open.?quote|dangling` and `cjk.*continuation`).
- **Risks.**
  - Over-fitting Italian/CJK regresses English golden rules — validate against all
    `MULTI_SENTENCE_QUOTATION_KEEP_DATA` before commit.
  - Brittle feature engineering creates English-only tuning — gate behind language
    profile (check `lang.iso_code` / pass a language-specific config dict).
  - O(n) features per segment degrade throughput — apply only after existing
    thresholds pass (amortized over candidates).
  - case_0080 is a structurally-similar gold-KEEP — add to regression suite,
    require it to stay correct.
  - Order of operations: open-quote resplit (processor.py) vs CJK merge in
    `en_es_zh.py` `_should_merge_quote_continuation` (~lines 125-134) — clarify
    `_resplit_segments` ordering; test the two passes cooperate.
- **Dependency / readiness:** **needs-decision** + depends on N2.
  - **Decision needed:** how to gate the new feature signal so it does not become
    English-only tuning — language-profile gate (recommended: check `iso_code` or
    pass a per-language config dict) vs a global heuristic. Decide before
    implementation.

### N12 — Deepen thin-tail languages + new-language scaffold

- **Kind / effort / horizon / ready:** lang / L / later / needs-external /
  depends on N2.
- **Summary.** Curate real abbreviation lists for six thin-tail languages
  (Amharic, Armenian, Burmese, Urdu, Marathi, Persian) that currently carry only
  boundary regex + punctuation, validated by native speakers or corpus analysis.
  Ship a reusable scaffold (test template + lang module + registry-entry
  generator) and a "good first language" contributor path. When adding
  high-demand absent languages (Korean, Vietnamese, Thai, Turkish, Indonesian,
  Hebrew, Nordics), scope RTL and scriptio-continua as distinct work — they break
  span/round-trip assumptions and need dedicated fixtures before shipping.
- **Files.**
  - `sentencesplit/languages.py`, `sentencesplit/language_profile.py`
  - `sentencesplit/lang/{amharic,armenian,burmese,marathi,persian,urdu}.py`
  - `sentencesplit/lang/common/standard.py`
  - `sentencesplit/abbreviation_replacer.py`
  - `tests/conftest.py`
  - `tests/lang/test_{amharic,armenian,burmese,marathi,persian,urdu}.py`
  - `benchmarks/corpus_compare/results/scoreboard.baseline.json`
  - `benchmarks/corpus_compare/corpora.py`
  - `tests/regression/gate/baseline.json`
- **Public API.** `Segmenter(language="am"|"hy"|"my"|"ur"|"mr"|"fa", ...)` (codes
  already accepted). Abbreviations added as nested `Abbreviation` classes
  (pattern from Spanish/Greek). New-language scaffold provides: (a)
  `new_language_test_template.py` (fixtures + golden-rules pattern); (b)
  `lang_module_scaffold.py` generator (boundary regex + punctuation + abbreviation
  stub); (c) a contributor guide linking the template + curation workflow.
- **Test plan.** Each thin-tail language gains
  `tests/lang/test_{lang}.py` with: (1) 2-5 golden-rules cases (pattern from
  `test_hindi.py` / `test_spanish.py`); (2) abbreviation cases once curated; (3)
  property-based round-trip on dirty input (from N5); (4) regression fixtures
  tied to adjudicated losses if benchmarked. N2 monitors each language
  independently. Scaffold: a template suite validates a generated module produces
  valid Python, imports, and passes golden rules (behind a `--validate-scaffold`
  flag, not in CI by default). For RTL/scriptio-continua (Hebrew, Thai): fixtures
  explicitly test span round-trip on RTL/script-continuous input, failing before
  shipping if offsets corrupt.
- **Risks.**
  - Thin-tail curation is labor-intensive and language-specific — native-speaker
    validation is a hard blocker; no coverage theater.
  - RTL/scriptio-continua may expose architectural assumptions in the span
    pipeline (N5) — Unicode bidi (U+202E, RLM, LRM) and Thai word-segmentation
    are known foot-guns; understand and test before shipping.
  - Scaffold + contributor path may attract low-quality PRs — enforce a checklist
    (native-speaker validation, corpus cite, ≥5 golden-rules cases) + maintainer
    sign-off.
  - "Good first language" assumes a contributor backlog — publish the guide
    prominently; measure engagement.
  - Low-precision diminishing returns at n=30 — validate on corpus subsets;
    prefer broad rules over exhaustive lists for low-resource languages.
- **Dependency / readiness:** **needs-external** + depends on N2.
  - **External input needed:** native-speaker or corpus validation per thin-tail
    language; for any new RTL/scriptio-continua language, dedicated round-trip
    fixtures must exist (depends on N5 span contract) before shipping.

### N13 — Optional structure-aware pre-pass for markdown/code

- **Kind / effort / horizon / ready:** behavior-change / L / later /
  needs-decision / no deps.
- **Summary.** A pre-segmentation pass that protects fenced code blocks
  (` ``` ... ``` `), inline code (backticks), and markdown list markers from
  triggering sentence boundaries, activated only when
  `Segmenter(doc_type='markdown')`. Runs after `cleaner.clean()` (if applicable)
  and before the Processor pipeline, wrapping regions in sentinels identical to
  the existing abbreviation/punctuation protection scheme. Never affects the
  default code path; regression-tested before shipping.
- **Files.**
  - `sentencesplit/segmenter.py`
  - `sentencesplit/processor.py`
  - `sentencesplit/markdown_structure.py` (new)
  - `tests/test_markdown_structure.py` (new)
  - `tests/regression/test_markdown_regression.py` (new)
- **Public API.** `Segmenter.__init__(doc_type: str | None = None)` extended to
  accept `'markdown'` alongside `None` and `'pdf'`. All other APIs unchanged. The
  pre-pass is internal to Processor; no new public class.
- **Test plan.**
  1. Unit (`test_markdown_structure.py`): fenced-code / inline-code / list-marker
     regex match on isolated samples; edge cases (unclosed fences, nested
     backticks, list markers inside code blocks).
  2. Round-trip: span offsets + reassembled text byte-for-byte (property-based on
     fixtures).
  3. Regression (`test_markdown_regression.py`): README excerpt, code comment
     with examples, mixed markdown+prose; protected blocks not split,
     non-protected split normally.
  4. Boundary: sentence ending a code block splits from following prose.
  5. No regression on English Golden Rules with `doc_type=None`.
  6. Per-language sampling (en, zh, fr): `'markdown'` mode no false negatives on
     non-markdown; protects code.
  7. Span fidelity with `clean=False` + `char_span=True` under `'markdown'`.
- **Risks.**
  - Highest regression risk if the pre-pass mutates text before
    `split_into_segments` (C901-exempt) — pre-pass only inserts sentinels;
    `process()` structure unchanged; always run the N2 gate before shipping.
  - Sentinel collision — handled by existing
    `Processor._build_sentinel_escape_tables`; test with input containing
    reserved sentinels.
  - Misidentified code block suppresses real boundaries — strict fenced regex
    (≥3 backticks/tildes), balanced inline backticks only, list markers only at
    line starts with whitespace; document heuristics.
  - `doc_type` validation — extend `{None,'pdf'}` to `{None,'pdf','markdown'}` in
    Segmenter + propagate through Cleaner.
  - `clean=True` + `doc_type='markdown'` interaction — safest default: cleaner
    runs first, then markdown protection; document, no mutual exclusion.
  - No Hypothesis harness yet — reuse N5 infrastructure if available (not a
    blocking prerequisite).
- **Dependency / readiness:** **needs-decision** (no hard code dependency, though
  it benefits from N5's property harness).
  - **Decisions needed:** (a) confirm `clean=True` + `doc_type='markdown'`
    ordering (recommended: clean first, then protect); (b) confirm the heuristic
    strictness (≥3 backticks/tildes for fences, balanced inline backticks,
    line-start list markers). Decide before implementation.

---

## 4. How to run the next item

Each remaining item is implemented end-to-end by the `execute-roadmap`
workflow with the same guardrails used for N2:

```
Workflow({name: "execute-roadmap", args: {items: ["<id>"]}})
```

For example, `Workflow({name:"execute-roadmap", args:{items:["N5"]}})`
implements N5. Honor the dependency order in §2 — run an item only after its
`depends_on` items are merged.

The **N2 hermetic regression gate now guards every behavior-changing item**
(`tests/regression/test_regression_gate.py`, run automatically with the suite).
For any item that changes segmentation output (N1b, N9, N10, N11, N12, N13):

- A per-language EM drop beyond that corpus's tolerance, or a boundary-F1 drop
  beyond the global tolerance, fails the PR red and names the language.
- To intentionally move the committed baseline for a net-positive trade, use the
  reviewed flow — never hand-edit `baseline.json`:
  ```
  uv run python tests/regression/gate/regen_gate.py \
      --update-baseline "one-line rationale for the trade"
  ```
  Commit the regenerated `baseline.json` in the same PR; put per-corpus deltas
  in the PR body. `golden_rules` and `ud_zh_gsd` are pinned at **zero tolerance**
  and may not regress at all. See `tests/regression/gate/GOVERNANCE.md` for the
  net-positive-trade rule.

---

## 5. Cross-cutting: SemVer / stability contract

From LEVEL_UP_PLAN §4 "Cross-cutting: stability & versioning contract (applies to
N1b, N4)" and §5:

We are adding new public surfaces (`StreamSegmenter` from N4, `extra_abbreviations=`
from N1b) at **v0.0.x**, with no stated commitment about when *output* may change —
and a CI gate that "fails on any EM drop" is in direct tension with shipping
accuracy improvements that, by definition, change segmentation output.

**This must be resolved before the public leaderboard (N6) ships.** Publish a short
SemVer + stability policy stating:

- **(a)** which surfaces are **stable vs. experimental** (e.g. `segment()` /
  `segment_spans()` stable; `StreamSegmenter`, `extra_abbreviations=`, lookahead
  experimental at v0.0.x);
- **(b)** that **segmentation output may change in minor releases when net
  accuracy improves**, with the change noted in the changelog;
- **(c)** a **deprecation window** for API changes (e.g. the `char_span` flag
  retired in N5).

The **N2 governance flow is the operational half** of this contract (the gate +
the `# baseline-update` net-positive-trade rule); the **policy doc is the public
half**. Without both, "we never change your output" and "we keep improving
accuracy" remain contradictory promises and a trust liability. N6 is the natural
landing point because the leaderboard is where users first see output changes
between releases.
