# V2 Refactor Roadmap

Post-landing analysis of `feat/v2-abbreviation-engine` (PeriodClassifier single-pass engine, PR #78).
Status verified on this branch: suite **2100 passed / 1 skipped / 6 xfailed** (`uv run pytest -q`, 49.8s).

**Framing:** this is a v2 — *backwards compatibility can be broken*. Items below propose the right design,
not the compatible one. Each carries effort (S/M/L/XL), risk (low/med/high), reward (low/med/high), and a
`[BC: none/minor/major]` tag. Cited locations were opened and confirmed during analysis.

---

## 1. Headline verdict

**The v2 abbreviation cutover succeeded; the codebase's organization health is *good-but-uneven*.**
The PeriodClassifier is a genuine improvement: per-language behavior is now an `AbbrPolicy` (closures over a
typed `Candidate`) co-located in each `lang/*.py`, and the engine keeps only shared machinery. The suite is
green and the test corpus is broad (28 per-language modules, regression dir, a dedicated `tests/v2/` layer).

But three structural debts remain, in decreasing severity:

1. **The in-band sentinel model is the dominant architectural smell.** Decisions are carried as *printable
   codepoints* (`∯♬♭☉…☝`, processor.py:193) spliced into the text and threaded through the whole pipeline.
   Because those are ordinary characters a user can type, processor.py:184-438 carries ~250 LOC of
   defensive escape/restore machinery (`_build_sentinel_escape_tables`, `_absent_noncharacter_delimiter`,
   the private-use/noncharacter-delimiter search) purely to stay non-destructive. The RFC called the
   placeholder "the clearest symptom" and it still is. **However** — see §6 "considered & dropped" — the
   naive "carry offsets instead" rewrites were adversarially rejected as *under-scoped and net-worse*; `∯` is
   load-bearing IR for ~13 downstream passes, not a leaf. The sentinel deletion is a real prize but only as
   the *payoff* of completing single-pass first, not a standalone cut.

2. **Language configuration flows through two unrelated channels.** Processor reads 14 resolved hooks via
   `self.profile.*` and 13 static rule hooks straight off the class via `self.lang.*` (processor.py:480-484,
   511, 529-536, 650, 697, 710, 720, 724-738). One config channel would let `self.lang` stop being threaded
   into Processor at all.

3. **Single-pass is incomplete, and the data layer is unlinted.** Titled-name / a.m.-p.m. / standalone-I
   decisions still live in downstream string passes (abbreviation_replacer.py:411-453); Kazakh still carries
   whole-text wrapper scaffolding; and the abbreviation lists are large and unvalidated-by-behavior (Dutch
   1585 entries / 1033 internal-dot, Italian 2223; 10 languages including `ja`/`zh` inherit the 199-entry
   *English* list verbatim).

The good news: every one of these is incrementally addressable, and the test scaffolding to make the changes
*safe* (a 26-language `segment()` snapshot harness) already exists but is **not wired into CI** — the single
highest-leverage cheap win.

---

## 2. Quick wins — S effort, low risk, real reward

Do these first; several de-risk the structural work.

### QW1 — Wire the orphan 26-language segment snapshot into CI as the cross-language regression gate `[BC: none]`
`tests/v2/segment_snapshot.py` is a complete, deterministic, AST-driven `segment()` snapshot+diff harness with
a committed, currently-clean baseline (`tests/v2/segment_snapshot.json`, ~122 KB). **No test module imports
it** (`grep` confirms zero `test_*.py` references). Add `tests/v2/test_segment_snapshot.py` asserting
`diff() == []` with a regenerate hint, and put the `__main__` regenerate path behind a documented `--update`
flag. **Effort S, risk low, reward med.** Baseline is diff-clean so it passes immediately; afterward *every*
structural refactor below gets a byte-level 26-language safety net for free. **This unblocks §3 and §4 — do
it absolutely first.**

### QW2 — Promote the shared whole-span policy to `lang/common/`, kill the bulgarian→slovak import `[BC: none]`
`lang/bulgarian.py:6` does `from sentencesplit.lang.slovak import _sk_classify_special, _sk_protect_edit` —
the only lang→lang import of *private helpers* in the tree (the `en_es_zh.py:16 → spanish` import is a
deliberate combined-profile merge, not the same smell). The logic is generic ("unconditional whole-span
PROTECT on the regular branch; NOT_HANDLED for prepositive/number"), not Slovak-specific. Move both functions
into `lang/common/whole_span_abbr.py` (mirroring the existing `lang/common/arabic_script.py` shared-base
precedent) exposing a `whole_span_policy()` factory; have slovak.py and bulgarian.py both import from there.
**Effort S, risk low, reward low.** Sole importer is bulgarian.py:6; no test imports `_sk_*` directly.

### QW3 — Fix the two stale `period_classifier._sk_*` comments `[BC: none]`
slovak.py:110 and bulgarian.py:145 still claim the policy lives at `period_classifier._sk_classify_special` /
`_sk_protect_edit`, but those functions live in `lang/slovak.py:54,66` (grep confirms the
`period_classifier._sk` path does not exist). Comment-only; fold into QW2's relocation so the comments point
at the real `lang/common/` home. **Effort S, risk low, reward low.**

### QW4 — Remove the cosmetic empty-param skip `[BC: none]`
The 1 skip is purely cosmetic: `tests/v2/corpus_en.py:275` sets `_XFAIL = []` (all Phase-2 targets promoted to
green), so `test_corpus_en_xfail` (test_corpus_en.py:32) collects an empty param set and pytest reports
`SKIPPED [1] ... got empty parameter set`. Guard with `@pytest.mark.skipif(not xfail_cases(), ...)` **and keep
the strict-xfail promotion mechanism** documented at test_corpus_en.py:7-11 — do *not* delete the path
outright. **Effort S, risk low, reward low.**

### QW5 — Promote the real public exceptions + registry functions to the top-level namespace `[BC: none]`
`InvalidConfigurationError` / `UnknownLanguageError` (the exceptions callers catch) are not in
`sentencesplit.__all__` nor importable from the top-level package (only `SentenceSplitError` is,
__init__.py:1-16). README documents `register_language` / `unregister_language` (languages.py) but they are
not re-exported. Add all four to `__init__.py` + `__init__.pyi` + `__all__`. **Effort S, risk low, reward
low.** Breaks exactly one test: `tests/test_zero_dependencies.py` `test_public_surface_matches_all` asserts
`__all__` equals the current 7-name set — extend it.

### QW6 — Triage/index the six standing xfails `[BC: none]`
The six xfails (arabic bidi-mark abbr; "a.m./P.M. hardest"; two no-space-after-period OCR cases; the Pt.
medical note; issue #83 four-dot ellipsis) carry no shared backlog index. Add stable `reason=` strings making
them discoverable as a backlog. **Do NOT delete the #83 xfail on a "no longer desired" theory** (adversarially
flagged): that would leave the suite asserting a model inconsistent with the passing 2-dot/3-dot siblings.
Index now; re-adjudicate #83 as its own scoped task later. **Effort S, risk low, reward low** (part 1 only).

> **Note on CI hermeticity (downgraded):** the seed flagged `tests/test_corpus_compare_segmenters.py` as
> needing `benchmarks/corpus_compare/__init__.py`. **Verified false in practice:** that test runs
> **3 passed / 0 skipped** here; `benchmarks/__init__.py` exists and `corpus_compare/` resolves as a PEP-420
> namespace subpackage under the default `pytest` rootdir-on-`sys.path`. The leaf `__init__.py` is genuinely
> absent, so a run under `--import-mode=importlib` or an installed-package layout *would* break — but the
> "fresh-clone-1-skip" framing is wrong; the actual single skip is QW4. **Recommendation:** add the leaf
> `__init__.py` + `pythonpath = ["."]` as a cheap belt-and-braces hardening (S/low/low), but it is *not* the
> cause of the current skip and should not be sold as such.

---

## 3. Structural refactors

Larger, dependency-ordered. Each lists what it unlocks.

### S1 — Complete the single-pass model: fold downstream per-period decisions into classifier post-stages `[BC: minor]`
**Problem.** `AbbreviationReplacer.replace()` (abbreviation_replacer.py:411-453) runs ~14 sequential string
passes *after* the classifier — `replace_multi_period_abbreviations` (titled-name / initialism / a.m.-p.m.,
:586-664), `protect_allcaps_imprint_abbreviations` (:479), `apply_ampm_boundary_rules` (:455),
`restore_standalone_i_boundaries` (:500). Several are structurally the *same single-period classification* the
PeriodClassifier already makes, re-parsed from strings. The `AbbrPolicy.pre_stages` / `post_stages` tuples
(period_classifier.py:158-159) exist for exactly this and are **unused by every shipping policy**.
**Proposal.** Promote each per-period downstream decision that is genuinely a single-period classify into an
ordered `post_stage` owned by the classifier, running against the typed context instead of re-parsing text.
**Effort L, risk med, reward med.** Blast radius: the v2 byte-equivalence snapshot, `test_titled_name_and_timezone.py`
(28 cases), `test_split_mode.py` (9 ampm), `test_issues.py`, the German standalone-I regression, and the
number-branch shared by `en_es_zh`/`zh`. **Unlocks S4** (sentinel deletion) by collapsing the count of passes
that still consume `∯`. *Do this before attempting any sentinel removal.*

### S2 — Fold the 13 static `self.lang.*` rule hooks into `LanguageProfile` (one config channel) `[BC: minor]`
**Problem.** Two indirections (`self.profile.*` resolved vs `self.lang.*` static) for the same concept.
**Proposal.** Move every per-language rule the Processor consumes onto `LanguageProfile` as resolved fields
built once in `LanguageProfile._build` (language_profile.py:54-74). Languages keep declaring rules as class
attributes (ergonomic authoring); Processor reads *only* `self.profile.*` and `self.lang` is no longer
threaded in. **Effort M, risk low, reward med.** Internal-only; no public API change. Breaks
`tests/test_language_profile.py:14-29` (asserts the exact resolved-field set by identity — extend it). Pairs
naturally with the language-profile already being the single resolved home.

### S3 — Extract a `boundary_resplit` module out of processor.py `[BC: minor]`
**Problem.** processor.py (763 LOC) owns 6 module-private resplit regexes + helpers
(`_CJK_QUOTE_RESPLIT_RE`, `_CJK_BANG_RESPLIT_RE`, `_LATIN_RESPLIT_RE`, `_MULTI_TERMINATOR_RESPLIT_RE`,
`_split_on_uppercase_boundary`, `_resplit_multi_sentence_quote` at :29-93,391-402,126-181), and
`en_es_zh.py` + `cjk.py` re-implement the quote-continuation merge.
**Proposal.** Create `sentencesplit/boundary_resplit.py` owning the regexes, the uppercase-boundary splitter,
the multi-sentence-quote resplitter, and a *shared* quote-continuation merger parameterized by
`(closer_re, reporting_clause_re, latin_lowercase_continuation)` that `CJKProcessor` and `en_es_zh` both call.
**Effort M, risk med, reward low.** Callers to keep green: `examples/custom_language_with_processor_hooks.py:25`
and `benchmarks/phase_profile.py:58` both reference `Processor._resplit_segments` by name (keep a thin
delegating method). **Marginal** — do only if S1+S2 leave processor.py still unwieldy.

### S4 — Delete the sentinel escape/restore machinery (the payoff) `[BC: none]`
**Problem.** processor.py:184-438 (~250 LOC) exists only because sentinels are printable codepoints that can
collide with input: `_build_sentinel_escape_tables`, `_absent_noncharacter_delimiter`,
`_iter_delimited_private_use_tokens`, `_scan_noncharacter_delimiter_counts`, `_RESERVED_SENTINELS`, and the
escape/restore in `process()` (:425-437).
**Proposal.** *After* S1 has removed the downstream passes that consume `∯` as IR, move the remaining protect
decisions out-of-band (offset-keyed, carried beside the text) so there is no in-band token that can clash with
input — then the escape/restore machinery and `_RESERVED_SENTINEL_SET` delete outright. **Effort M, risk med,
reward high. Net LOC strongly negative.**
**⚠ Sequencing is load-bearing.** Executed *prematurely* (before EVERY sentinel is out-of-band), `clean=True`
corrupts any input containing a sentinel char and `clean=False` silently drops text via broken span mapping —
exactly the failures the ~12 `tests/regression/test_sentinel_*` cases guard. **This item is gated on S1
(and the second `&X&` punctuation/ellipsis family) being fully out-of-band.** Until then it is a *trap*, not a
quick win. The adversarial review rejected three "just carry offsets" variants for under-scoping precisely
this (see §6).

### S5 — Behavioral data-lint + normalize/dedup the abbreviation lists `[BC: minor]`
**Problem.** The 4 existing data tests (test_languages.py:82-127) validate *storage shape* only (no dups,
trimmed, no single-token trailing dot). None checks *behavior*, so hundreds of entries the engine cannot
enumerate silently rot — and some actively mis-split in realistic carriers (`da` d.å., `de` dipl.-ing.,
`it` cod. proc. civ., `nl` b.&w.). Lists are also only partially sorted and dup-prone; 531/1033 Dutch
internal-dot entries are fully shadowed by `MULTI_PERIOD_ABBREVIATION_REGEX`; Italian builds 245K automaton
transitions (~833 ms).
**Proposal (two coordinated pieces):**
- *Data-lint:* parametrized test rendering each `ABBREVIATIONS` entry in a neutral lowercase-follower carrier,
  asserting the engine keeps it joined ("if it's in the list, it works"). **Must land with a quarantine
  xfail-allowlist** seeded with the ~95 known failures (~80 real mid-token breaks + ~15 single-letter false
  positives) or it reds CI immediately. **Effort M, risk low, reward high.**
- *Normalize:* adopt `sorted(set(...))` as the canonical stored form for all lists (already the pattern in
  `en_legal.py:119` and `en_es_zh.py:79`); one-time script lowercases-dedups-sorts and drops internal-dot
  entries fully covered by the language's MULTI_PERIOD regex (keep load-bearing multi-char-token entries like
  `aanbev.comm`). Add a lint asserting each list equals its canonical form. **Effort M, risk med, reward med.**
  Breaks only `test_specialized_abbreviations_are_registered_abbreviations` (test_languages.py:122) on Italian
  s.a/s.n.c/s.p.a/s.r.l (NUMBER/PREPOSITIVE entries) if done naively — preserve those.

### S6 — Fix the engine gap for non-ASCII / hyphen / multi-token abbreviations `[BC: minor]`
**Problem.** A whole class of declared abbreviations cannot work through the automaton + per-entry `match_re`
path: (a) non-ASCII multi-period (`d.å`, `dipl.-ing`, `c.-à-d`, `o.ä`) because `MULTI_PERIOD_ABBREVIATION_REGEX`
is ASCII-only (common.py:61) and only bg/el/kk override it; (b) hyphenated initialisms; (c) 3+ token and
`&`/`(`/`!`/`/` entries.
**Proposal.** Decide each gap explicitly rather than papering it with dead list entries. Extend the base
MULTI_PERIOD regex to a Unicode letter class (bg/el/kk already prove it's safe) so Danish/German/French stop
needing inert entries. **⚠** Naively copying the bg/el `(?<!\w)` lookbehind into the base **breaks**
`test_chinese.py::test_zh_challenging` for `项目代号是A.I.-7。` (CJK counts as `\w`, lookbehind mis-anchors) —
2 failures; anchor on a non-CJK-aware class instead. **Effort XL, risk med, reward med.** Gated on S5's
data-lint existing first (so the gap is *measured*, not guessed).

### S7 — Make spans the single canonical output; drop `char_span` + the `segment()` union return `[BC: major]`
**Problem.** `segment()` returns `list[str] | list[TextSpan]` depending on the `char_span` *constructor* arg
(segmenter.py:551), so the return type is non-local and un-narrowable; `char_span` is already soft-deprecated
(segmenter.py:114-126).
**Proposal (v2 surface).** Remove `char_span` from `__init__`. `segment(text) -> list[str]` always;
`segment_spans(text) -> list[TextSpan]` always. Delete `_CHAR_SPAN_DEPRECATION_WARNED`,
`_warn_char_span_deprecated`, the attribute, and the clean/char_span validation branch
(segmenter.py:199-214). **Effort L, risk low, reward med.** Deletes
`tests/regression/test_char_span_deprecation.py` entirely; migrates ~61 call sites across 14 files (conftest
span fixtures for en/zh/ja/en_es_zh + dependents). Migration note: `Segmenter(char_span=True).segment(t)` →
`Segmenter().segment_spans(t)`.

### S8 — Unify the lookahead result shape (one generic dataclass) `[BC: minor]`
**Problem.** `segment_with_lookahead()` returns a `SegmentLookahead` dataclass but
`segment_spans_with_lookahead()` returns a bare `tuple[list[TextSpan], bool]` (segmenter.py:599-621) — same
concept, two shapes.
**Proposal.** Make `SegmentLookahead` `Generic[T]`; `segment_with_lookahead -> SegmentLookahead[str]` and the
spans variant `-> SegmentLookahead[TextSpan]`. **Effort S, risk low, reward low.** Breaks
`stream_segmenter.py:280` (tuple-unpack → attribute access) and `test_lookahead.py:117,…` tuple asserts.
**Best done together with S7** (after `char_span` is gone there is exactly one return shape per method).

### S9 — Extract a shared boundary/normalization helper so StreamSegmenter stops reaching into Segmenter privates `[BC: none]`
**Problem.** `stream_segmenter.py:241,258` call `self._segmenter._strip_zero_width(...)` and
`self._segmenter._terminal_punctuation(...)` — a de-facto private contract between two shipped classes.
**Proposal.** Move both into a module-level helper both classes import (e.g. `sentencesplit/_normalize.py`);
Segmenter keeps thin instance wrappers (its own `_wait_for_last_segment` at segmenter.py:361 calls
`_terminal_punctuation`). **Effort S, risk low, reward low. Marginal** — nice hygiene, not load-bearing.

### S10 — Collapse Kazakh's whole-text wrapper passes onto the staged classifier `[BC: minor]`
**Problem.** `KK_POLICY` (kazakh.py:97) uses both `classify_special` and `realize_suffix` only to widen one
follower-class arm for a frozen 39-entry `_KK_WIDE_FOLLOWER_STEMS` set (kazakh.py:32-74) — the most
per-language scaffolding of any v2 policy.
**Proposal.** Express the WIDE-follower stems as a policy *field* (a per-stem follower-class override map or a
second follower_class via `candidate_filter`) so KK_POLICY drops the bespoke pair and rides the base dispatch
like english/en_legal. **Effort L, risk med, reward low. Marginal/defer** — isolated to one language; do after
S1 proves the staging pattern.

### S-decide — Document the spaCy entry point's contract status `[BC: none]`
`spacy_component` is a registered `spacy_factories` entry point (pyproject.toml:68) — effectively public to
spaCy users — but absent from `__all__` and the README "Public API" contract. **Proposal:** a pure doc edit
carving it out (or listing `create_sentencesplit` and stabilizing the signature). **Effort S, risk low,
reward low.** Implement as doc-only to avoid coupling the public surface to spaCy's factory signature.

---

## 4. Test suite & framework improvements

The user emphasized this section. The suite is broad but has specific fragility/coverage gaps.

### T1 — Wire the segment snapshot gate `[BC: none]` — **see QW1.** The single biggest test-infra win; it is
the safety net every structural refactor in §3 leans on. Effort S, reward med. **Do first.**

### T2 — Retire the frozen-snapshot v2 oracle now that the legacy engine is deleted `[BC: none]`
`tests/v2/oracle.py` (174 LOC) + `test_oracle.py` (148 LOC) diff the PeriodClassifier against an 18-entry
*hand-frozen* `_LEGACY_SNAPSHOT` of a deleted engine (oracle.py docstring: "DEBUGGING AID, not a gate";
"legacy engine was deleted at Phase 6"). Delete both; re-express the genuinely valuable English/en_legal
parity assertions (Dr./Sen./No./Vol./Cir.) as `segment()`-level green cases in `corpus_en.py` and the Kazakh
parity (См./рис. unprotected, обл. қала WIDE-follower) into `test_kazakh.py`. **Effort M, risk med, reward
med.** Removes a 322-LOC layer frozen against deleted code. Verify the Kazakh-specific assertion is fully
covered before deleting (it is only *partly* covered by `test_kazakh.py` today).

### T3 — Add core `segment()` property tests (no-crash, idempotence, split_mode monotonicity) `[BC: none]`
Hypothesis is a declared dev dep used in exactly one file (`test_span_roundtrip.py`). Add
`tests/test_properties.py`: (1) no-crash on `st.text()` + dirty-char pool across all 26 codes; (2)
idempotence (`segment(s) == [s]` modulo trailing whitespace for each emitted `s`); (3) split_mode
monotonicity. **Effort S, risk low, reward low.** **⚠ As written it reds on first run** — idempotence fails in
13 languages and monotonicity in en/de/en_legal on `'. ! e.'`. Land it with the known failures quarantined
(xfail/allowlist) so it documents real invariant gaps without blocking CI; promote as they're fixed. Promote
the reusable per-script strategies from `test_span_roundtrip.py:61-113` into `tests/helpers.py` first.

### T4 — Add dedicated unit suites for processor / period_classifier `[BC: none]`
No `tests/test_processor.py` or `tests/test_period_classifier.py` exists; classifier coverage lives only in
`tests/v2/test_classifier_en.py` (English). Add a first-class `test_period_classifier.py` (multi-language
policy coverage of each classify branch + the `pre_stages`/`post_stages` seam once S1 uses it) and a
`test_processor.py` covering the two pipeline phase lists directly. **Effort S, risk low, reward low.**

### T5 — Data-driven per-language test scaffolding `[BC: none]`
23 `GOLDEN_<XX>_RULES` constants, 28 near-identical `test_<xx>_sbd` functions, 38 hand-written conftest
fixtures (tests/conftest.py), inconsistent assertion styles (55 ad-hoc `.strip()` calls; 24/28 modules don't
use the `assert_segments` helper). Introduce `tests/lang/cases/<code>.py` exporting a plain `GOLDEN` list and
a single parametrized driver iterating `LANGUAGE_CODES`. **Effort XL, risk med, reward low. Defer** — large
mechanical churn; **breaks ~30 non-Golden files** that request named fixtures (`<xx>_default_fixture`, etc.)
across the suite. Only worth it after the structural refactors settle, and only if language-add friction
becomes a real bottleneck. Lower-cost down payment: standardize on `assert_segments` everywhere first.

### T6 — Add the data-lint (behavioral) and normalization lint `[BC: minor]` — **see S5.** Belongs to both the
data layer and the test framework; effort M, reward high, but *must* ship with a quarantine allowlist.

---

## 5. Recommended sequence (dependency-ordered)

**Phase 0 — Safety net + cheap hygiene (all S, [BC: none], ~1 sitting):**
1. **QW1 / T1** — wire the 26-language snapshot gate. *Unblocks everything; do literally first.*
2. **QW2 + QW3** — `lang/common/whole_span_abbr.py`, kill bulgarian→slovak import, fix stale comments.
3. **QW4** — guard the empty-param skip (keep the strict-xfail mechanism).
4. **QW5** — promote public exceptions + registry funcs to top-level namespace.
5. **QW6** — index the 6 xfails with stable reasons (do *not* delete #83).
6. **T2** — retire the frozen-against-deleted-code oracle (re-home its real assertions first).

**Phase 1 — Config + completion (M/L, [BC: minor], guarded by Phase 0's snapshot):**
7. **S2** — fold the 13 `self.lang.*` hooks into LanguageProfile (one config channel). *Independent; low risk.*
8. **S5 + T6** — abbreviation data-lint (with quarantine) + canonical-format normalization. *Surfaces the
   real engine gaps as a measured backlog.*
9. **S1** — complete single-pass: downstream per-period decisions → classifier post-stages. *The keystone;
   unblocks S4.*
10. **T4** — add the dedicated processor/period_classifier unit suites (now exercising the staging seam).

**Phase 2 — Payoffs + API v2 (M/L, [BC: none→major], gated on Phase 1):**
11. **S4** — delete the sentinel escape/restore machinery, **only after** S1 + the `&X&` family are out-of-band.
12. **S6** — close the non-ASCII/hyphen/multi-token engine gap (gated on S5's lint).
13. **S7 + S8** — make spans canonical (drop `char_span`/union return) + unify lookahead shape. *One coordinated
    `[BC: major]` API break; do them together.*
14. **S3, S9, S-decide** — extract `boundary_resplit`, share the normalization helper, document spaCy contract.

**Defer / opportunistic:** S10 (Kazakh collapse), T3 (property tests — land quarantined whenever), T5
(per-language scaffolding rewrite — only if language-add friction bites).

**Rationale.** The snapshot gate (1) makes the byte-level blast radius of every later step *visible*, so the
risky single-pass and sentinel work can be done with confidence. Config unification (7) is independent and
low-risk, so it parallelizes. The data-lint (8) must precede the engine-gap fix (12) so the gap is measured
not guessed. Single-pass completion (9) is the keystone that *unlocks* sentinel deletion (11) — attempting 11
before 9 is the documented trap. The API break (13) is deferred to the end so it lands once, against a stable
internal surface.

---

## 6. Considered & dropped

These were proposed and **adversarially rejected** — do not pursue as written:

- **"Replace `∯` with an offset-keyed protected-period set carried beside the text."** Misdiagnoses scope: `∯`
  is load-bearing IR for ~13 downstream passes, not a leaf; the claimed `BC:none/reward:high` is dishonest and
  the design is *strictly worse* than the status quo until single-pass (S1) lands first.
- **"Unify the second `&X&` (punctuation/ellipsis) sentinel family out-of-band in the same change."** The
  family is real (punctuation_replacer.py:5-13, lists_item_replacer.py) but bundling it makes the change
  unbounded; sequence it *after* S1/S4 as a separate step.
- **"Let `Edit` objects flow as the decision carrier instead of flattening to `∯`."** Misidentifies its own
  target; the mechanism it proposes doesn't remove the in-band token.
- **"Replace the `&ᓷ&&ᓷ&` PLACEHOLDER injection with a typed PLACEHOLDER edit, no length-align hack."** The
  length-aligned splice is the *only* length-coupling point; isolating it buys little without S1.
- **"Pull the 4 downstream passes into AbbrPolicy stages"** — *as a standalone, unguarded change.* The
  *intent* is correct and is captured as **S1**, but only with the snapshot gate (QW1) in front of it.
- **"Make the test/benchmark package hermetic — ship `benchmarks/corpus_compare/__init__.py` + pythonpath."**
  Central claims are **factually wrong here**: the corpus_compare test runs **3 passed / 0 skipped**; the
  alleged 1-skip is unrelated (it's QW4). Add the leaf `__init__.py` as cheap hardening if desired, but not
  as "the fix for the skip."
- **"Retire the German/zh/ja/en_es_zh `replace()` overrides by lifting whole-text-mode + CJK post-merge into
  policy fields."** Rests on a false premise about how many languages still override `replace()`; collapses on
  inspection.
- **"Empty `ABBREVIATIONS=[]` for the 10 English-inheritors including ja/zh."** Verified regression: Latin
  abbreviations (Calif., Inc.) appear in real CJK text and `zh`'s tests + the `en_es_zh` combined profile
  (en_es_zh.py:79) depend on the inherited list. The *real* item is the narrower S-class "make each inheritor's
  choice explicit (curated list **or** intentional empty-with-comment) + a lint flagging byte-identical
  English defaults at language-add time" — keep ja/zh non-empty.
