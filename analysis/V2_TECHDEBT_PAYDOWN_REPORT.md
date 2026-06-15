# V2 Tech-Debt Paydown — Release-Readiness Report

Branch: `feat/v2-abbreviation-engine` (PR #78).
HEAD at report time: `df8a90555886892aea2dd47fe3094d099d491b46`.
Roadmap executed: `analysis/V2_REFACTOR_ROADMAP.md`.

This report covers the tech-debt paydown that followed the V2 PeriodClassifier abbreviation-engine
cutover. **This is a v2 cycle — backwards compatibility is intentionally broken** (see §3). Each item was
landed under the COMMIT-OR-REVERT discipline: full suite + ruff + zero-dep + the 26-language `segment()`
snapshot all green before commit, else `git reset --hard` to the prior green SHA.

---

## 1. What landed

Dependency-ordered, by roadmap id. LOC deltas are source/test deltas (snapshot-JSON regenerations excluded
from the count). Every behavior-neutral item left `tests/v2/segment_snapshot.json` byte-identical
(`diff() == []`); the one behavior-changing API item (S7+S8) is also segment()-neutral at the output level.

### Phase 0 — safety net + cheap hygiene (all `[BC: none]`)

| id | commit | summary |
|----|--------|---------|
| **QW1 / T1** | `baa65a0` | Wired the orphan 26-language `segment()` snapshot into CI: new `tests/v2/test_segment_snapshot.py` asserts `diff() == []`; the bare-run regenerate footgun is now read-only and the `--update` write path is gated + documented. **This is the safety net every later structural refactor leans on — landed first.** |
| **QW2 + QW3** | `de63148` | Promoted the shared whole-span abbreviation policy to `lang/common/whole_span_abbr.py` (`whole_span_policy()` factory), deleting the only lang→lang private-helper import in the tree (`bulgarian.py → slovak._sk_*`) and fixing the two stale `period_classifier._sk_*` comments. |
| **QW4** | `608b47d` | Guarded the cosmetic empty-param skip on `test_corpus_en_xfail` with `@pytest.mark.skipif(not xfail_cases(), ...)` — strict-xfail promotion mechanism preserved. |
| **QW5** | `71bfded` | Promoted the real public surface — `InvalidConfigurationError`, `UnknownLanguageError`, `register_language`, `unregister_language` — to the top-level namespace (`__init__.py`/`.pyi`/`__all__`). `__all__` is now 11 names. |
| **QW6** | `7e299cc` | Indexed the six standing xfails with stable, discoverable `BACKLOG[xfail-index]: <slug>` reasons (arabic bidi-mark abbr, a.m./P.M.-vs-title boundary, two no-space-after-period OCR, the `Pt.` medical note, issue-83 four-dot ellipsis). #83 xfail kept (NOT deleted) per the adversarial flag. |
| **T2** | `3c5979f` | Retired the frozen-against-deleted-code v2 oracle (`tests/v2/oracle.py` + `test_oracle.py`, ~322 LOC); re-homed its genuinely valuable English/en_legal and Kazakh parity assertions as `segment()`-level green cases first. |

### Phase 1 — config unification + single-pass completion (`[BC: minor]`, internal-only)

| id | commit | summary |
|----|--------|---------|
| **S2** | `a8ae56c` | **Config unification.** Folded the 13 static `self.lang.*` rule hooks the Processor read off the class into resolved `LanguageProfile` fields built once in `_build`. Processor now reads per-language rules through one channel; `self.lang` is no longer the config carrier. |
| **S5 + T6** | `fb32833` | **Abbreviation data layer.** Behavioral data-lint (each `ABBREVIATIONS` entry rendered in a neutral carrier; engine must keep it joined) **landed quarantined** with a seeded xfail-allowlist of the ~known mid-token-break + single-letter false-positive failures, documented as a discoverable backlog — green-with-xfails, never red. Lists normalized to the canonical `sorted(set(...))` stored form with a lint enforcing it. |
| **S1** | `89399fe` | **Single-pass keystone.** The downstream post-period passes (titled-name / initialism / a.m.-p.m. / standalone-I, allcaps imprint) are now **owned by `AbbrPolicy.post_stages`** instead of being free-floating string passes after the classifier. NOTE: this migrated *ownership*, not yet the *representation* — the post-stages still read/write the in-band sentinel IR. (This is the precondition gap that blocked S4; see §2.) |
| **T4** | `652ec5c` | Added the first dedicated `tests/test_processor.py` and `tests/test_period_classifier.py` unit suites (previously classifier coverage existed only for English under `tests/v2/`). |

### Phase 2 — engine gap, API v2, extractions, opportunistic

| id | commit | BC | summary |
|----|--------|----|---------|
| **S6** | `4067267` | minor | Recognise non-ASCII multi-period abbreviations: base `MULTI_PERIOD_ABBREVIATION_REGEX` extended to a Unicode-letter class anchored on a **non-CJK-aware** class (avoids the documented `项目代号是A.I.-7。` CJK-lookbehind trap). Danish/German/French no longer need inert ASCII-only entries. (The full XL S6 scope — hyphenated initialisms, 3+ token, `&`/`(`/`!`/`/` entries — remains partially open; see §2.) |
| **S7 + S8** | `d93816d` | **major** | **API v2 break.** Spans are now the single canonical output and the lookahead result shape is unified. See §3 for the exact migration notes. |
| **S3** | `052b7fb` | minor | Extracted `sentencesplit/boundary_resplit.py` out of processor.py (the resplit regexes, uppercase-boundary splitter, multi-sentence-quote resplitter, and a shared quote-continuation merger that `CJKProcessor` + `en_es_zh` both call). Thin delegating method kept for the two external callers. |
| **S9** | `208b98a` | none | Extracted a shared `sentencesplit/_normalize.py` so `StreamSegmenter` stops reaching into `Segmenter._strip_zero_width` / `_terminal_punctuation` privates; both classes import the module-level helper. |
| **S-decide** | `609574f` | none | Doc-only: clarified the spaCy entry-point contract status. |
| **S10** | `9a490e5` | minor | Collapsed Kazakh's bespoke `classify_special`/`realize_suffix` WIDE-follower scaffolding into a policy *field*; KK_POLICY now rides the base dispatch like english/en_legal. |
| **T3** | `91dcf13` | none | Added core `segment()` property tests (no-crash / idempotence / split_mode monotonicity), **landed quarantined** with the known idempotence (13 langs) + monotonicity (en/de/en_legal) failures xfail-allowlisted — documents real invariant gaps without blocking CI. |
| **T5 (down-payment)** | `df8a905` | none | Standardized the per-language SBD tests on the `assert_segments` helper (the low-cost T5 down-payment; the full per-language scaffolding rewrite remains deferred). |

### Headline structural wins

- **Config unification: DONE** (S2) — one resolved config channel via `LanguageProfile`.
- **Single-pass completion: DONE for ownership** (S1) — downstream per-period decisions are policy-owned
  `post_stages`. **Representation is NOT yet out-of-band**, which is exactly why the sentinel deletion is
  still blocked.
- **Sentinel escape/restore deletion: NOT DONE** (S4 deferred — see §2). The ~250-LOC machinery in
  processor.py still exists because the in-band sentinel IR was not migrated out-of-band.
- **Canonical API: DONE** (S7+S8) — spans canonical, single return shape per method, unified lookahead.
- **Abbreviation data layer: linted + normalized** (S5/T6), with the behavioral gap now *measured*
  (quarantined backlog) rather than guessed.

---

## 2. Deferred / skipped — the remaining backlog

### S4 — Delete the sentinel escape/restore machinery — **DEFERRED (no code changed)**

This is the single most consequential deferral and the reason the dominant architectural smell survives v2.

**Why deferred:** S4's load-bearing precondition is **not met.** The roadmap (§3 S4, §5 step 11, §6) is
explicit that S4 is *gated on S1 having moved the protect decisions out-of-band* — and on the second `&X&`
punctuation/ellipsis sentinel family being out-of-band too. S1 as landed migrated **ownership** of the
post-classifier passes to `AbbrPolicy.post_stages` but did **not** make the decisions out-of-band: the
post-stages still produce/consume the in-band sentinel IR (`abbreviation_replacer.py` documents this in-line:
the post-stages are "owned by the policy now, but not yet out-of-band — S4 deletes the sentinel only once
they are").

The in-band IR is far larger than the period sentinel alone: `lang/common/standard.py`'s SUBS_TABLE maps ~21
distinct sentinels back to punctuation across two families — single-char (period, comma, colon, the four
double-punct marks, both terminal-marker chars, plus ellipsis/list markers) **and** the multi-char `&X&`
family (8 of them). All are produced/consumed by ~13 passes. The escape/restore machinery
(processor.py, ~250 LOC) is the **single** mechanism making *every* in-band sentinel non-destructive when a
user types one; `process()` treats the whole reserved-sentinel set as one unit. The ~14 sentinel
round-trip regression cases (`tests/regression/test_sentinel_*` /
`test_library_review_fixes.py`) require each listed sentinel to survive `clean=False` round-trips and not be
rewritten under `clean=True`, and **must stay green**. There is no bounded subset of "delete the machinery"
that keeps them green: removing it for any sentinel first requires moving that sentinel out-of-band, and the
multi-char `&X&` family is explicitly documented as *not escapable* and *still in-band*.

**Conclusion:** no safe bounded subset exists. The only path is the unbounded full-pipeline IR out-of-band
migration — exactly the under-scoped, net-worse rewrite the roadmap §6 adversarially rejected. Deferred
correctly; tree left at the green baseline, snapshot byte-identical, no revert needed.

**To unblock S4 later:** complete the *representation* half of single-pass — carry the per-period (and `&X&`)
protect decisions out-of-band (offset-keyed, beside the text) so no in-band token can clash with input. Only
then can the escape/restore machinery and the reserved-sentinel set delete outright (net LOC strongly
negative).

### Partial / opportunistic backlog still open

- **S6 (full XL scope)** — non-ASCII multi-period is done; hyphenated initialisms, 3+ token, and
  `&`/`(`/`!`/`/` abbreviation entries remain unaddressed in the engine.
- **S5 data-lint allowlist** — the quarantined behavioral failures (mid-token breaks + single-letter false
  positives) are a seeded backlog to promote to green as the engine gap closes.
- **T3 property-test allowlist** — idempotence failures in 13 languages and split_mode monotonicity failures
  in en/de/en_legal are quarantined invariant gaps to fix and promote.
- **T5 (full)** — only the `assert_segments` down-payment landed; the data-driven per-language scaffolding
  rewrite (`tests/lang/cases/<code>.py` + single parametrized driver) is deferred (large mechanical churn,
  breaks ~30 fixture-requesting files; do only if language-add friction bites).
- **The six standing xfails** — indexed (QW6) but not resolved; notably issue-83 four-dot ellipsis is kept
  intentionally to keep the model consistent with its passing 2-dot/3-dot siblings (re-adjudicate as its own
  scoped task).

---

## 3. BC-breaking changes (CHANGELOG / migration notes)

The one breaking commit is **S7+S8 (`d93816d`, `feat(api)!`)**. For a `BREAKING CHANGE:` CHANGELOG entry:

**1. `char_span` constructor flag removed from `Segmenter`; the union return is gone.**
- `Segmenter.segment(text)` now **always** returns `list[str]`.
- `Segmenter.segment_spans(text)` now **always** returns `list[TextSpan]`.
- Removed: the `char_span=` constructor parameter, the `self.char_span` attribute,
  `_CHAR_SPAN_DEPRECATION_WARNED`, `_warn_char_span_deprecated`, and the clean/char_span validation branch
  (the "PDF requires clean" error message no longer mentions `char_span`).
- **Migration:** `Segmenter(char_span=True).segment(text)` → `Segmenter().segment_spans(text)`.
- `tests/regression/test_char_span_deprecation.py` was deleted (the flag it guarded is gone).
- **Note:** `StreamSegmenter` keeps its own `char_span` output-shape flag; it no longer forwards it to the
  wrapped `Segmenter`. That public surface is unchanged.

**2. Lookahead result shape unified (`SegmentLookahead` is now `Generic[T]`).**
- `segment_with_lookahead(...) -> SegmentLookahead[str]` (unchanged shape; now parameterized).
- `segment_spans_with_lookahead(...) -> SegmentLookahead[TextSpan]` — **previously returned a bare
  `tuple[list[TextSpan], bool]`.**
- **Migration:** replace tuple-unpacking of the spans variant with attribute access:
  `segments, wait = seg.segment_spans_with_lookahead(t)` → `r = seg.segment_spans_with_lookahead(t); r.segments; r.should_wait_for_more`.

**3. Public namespace additions (QW5 — additive, not breaking, but CHANGELOG-worthy):**
- New top-level exports: `InvalidConfigurationError`, `UnknownLanguageError`, `register_language`,
  `unregister_language`. `__all__` grew from 7 to 11 names.

Other `[BC: minor]` items (S1, S2, S6, S3, S10, S5) are **internal-only** — they changed engine internals,
language-profile resolution, or test-helper identity sets, with no public-API or `segment()`-output change.
They do not need a CHANGELOG breaking note, only normal `refactor:`/`feat:`/`fix:`/`test:` changelog grouping.

---

## 4. Version implication

Per `CLAUDE.md`, the release version is **chosen manually** from the `workflow_dispatch` dropdown; conventional
commit types only drive changelog grouping, not the bump level. The person cutting the release must pick the
level by hand.

**This cycle contains a breaking change (S7+S8, `feat(api)!`: `char_span` removal + lookahead shape change).
Therefore this MUST be released as a MAJOR.** Given the pre-existing landed `feat:` work, a minor would be
incorrect — the `char_span`/union-return removal is a hard public-API break that will fail importing callers.

> Reconciliation note: the CLAUDE.md style guide carries an older line stating "the next release must be
> 0.1.0 (minor)" predicated on no breaking change having landed. That precondition is now false — the S7+S8
> API break supersedes it. The correct call for *this* cycle is **MAJOR** (e.g. `1.0.0`). The style-guide
> line should be updated when the release is cut.

---

## 5. Final gate state & release readiness

Authoritative final verification at HEAD `df8a90555886892aea2dd47fe3094d099d491b46`:

- **Full suite** (`uv run pytest tests/ -q`): **10485 passed, 14 skipped, 115 xfailed, 0 failed** (~202s).
  The grown xfail count is the intended quarantine seeding from S5/T6 (data-lint) and T3 (property tests) —
  green-with-xfails, documented as a discoverable backlog, never red.
- **Ruff**: `check` — all checks passed; `format --check` — all files already formatted.
- **Zero-dep** (`tests/test_zero_dependencies.py`): **3 passed** (re-verified in this session).
- **Snapshot**: `diff() == []` and `tests/v2/segment_snapshot.json` is byte-identical between the committed
  tree and the working tree (md5 match, re-verified in this session). No unintended cross-language behavior
  drift.
- **Tree**: clean (only pre-existing untracked `.claude/`, `.codex`, and unrelated `analysis/*.md` remain;
  none touched by the paydown).

**Release-ready: YES**, as a **MAJOR** v2. All hard gates are green. The headline structural wins (config
unification, single-pass ownership, canonical span API, unified lookahead, linted/normalized abbreviation
data) landed. The one consequential deferral — S4 sentinel deletion — is a *cleanly deferred* internal
refactor whose precondition (full out-of-band IR migration) is not yet met; it does not affect correctness or
the public surface and is documented as the top backlog item for a follow-up cycle. No red, no masked
snapshot drift, no broken-tree state.
