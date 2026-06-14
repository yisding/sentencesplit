# V2 Abbreviation Engine — Data + Dead-Code Cleanup Report

Branch: `feat/v2-abbreviation-engine` (NOT pushed; `main` untouched).
HEAD at report time: `c0249cb` (`refactor(abbr): drop dead _classify_number wrapper from PeriodClassifier`).
Phase-0 baseline base: `42e175c` (`test(v2): add 26-language segment() baseline snapshot + diff helper`).

This phase cleans up the abbreviation **data** and the **dead code** the V2 migration
left behind. It is a follow-on to `analysis/V2_IMPLEMENTATION_REPORT.md` (esp. §8 audit)
and `analysis/ABBREVIATION_ENGINE_V2_PLAN.md`.

---

## 1. The dot-convention decision and its rationale

**Decision: CONVERGE single-token abbreviations on the dominant NO-TRAILING-DOT
convention.** Strip exactly one trailing `.` from the single-token entries that carried
one; leave internal-dot initialisms and multi-token (spaced) entries dotted.

### Why (verified root cause)

The Aho-Corasick automaton in `abbreviation_replacer.py:192` keys each abbreviation as

```python
key = stripped_lower if stripped_lower.endswith("i") else stripped_lower + "."
```

i.e. it **appends a period**. An entry that already ends in `.` is therefore keyed
`<abbr>..` (double dot). A `<abbr>..` substring can never occur in real lowered text, so
`PeriodClassifier.enumerate_candidates` (`period_classifier.py:606`, automaton prefilter)
**never sees** that abbreviation and its period is never protected via the main path.
(The Cyrillic letters `и`/`і` do not match the U+0130 `endswith("i")` bare-key exception
@186–192, which is Latin-`i` specific and was preserved verbatim.)

The no-dot convention is **dominant**: 6592 plain single-token entries already follow it
vs. exactly **53 violators** (the "trail1" set). Converging on it lets the classifier own
the work at zero runtime cost.

### Scope: exactly the 53 single-token entries

A trail1 entry satisfies all three of: `s = e.strip()`; `s.endswith(".")`;
`s.count(".") == 1` (no internal dot); `not any(c.isspace() for c in s)` (no whitespace).
This matched **exactly 53** across the whole `LANGUAGE_CODES` registry —
**kk=39, pl=11, ar=2, sk=1** — re-confirmed post-fix to be **0 remaining**.

7 of the 53 collapsed onto a dotless twin that already existed in the same list
(kk: `м.`/`апр.`/`т.`/`мм.`; pl: `itd.`/`np.`; sk: `atď.`) — those dotted lines were
**deleted** (the literal-uniqueness guard `test_language_abbreviations_do_not_repeat_literals`
would otherwise red). The other 46 became genuinely new dotless entries.

### Why internal-dot and multi-token dots were LEFT ALONE

- **Internal-dot initialisms** (interior dot, no space — **1490** kept, e.g. `s.r.o`,
  `p.m.`, `e.g`, `i.e`, `Ph.D`, kk `с.ш.`, ar `ص.ب.`, en_legal `f.2d`/`f.3d`) — handled by
  `MULTI_PERIOD_ABBREVIATION_REGEX` (`common.py` + per-lang variants) or per-language
  `classify_special`, **not** by the automaton. Their interior dot is load-bearing.
- **Multi-token-with-space entries** (any whitespace — **219** kept, e.g. kk `т. б.`,
  `et al`, `sub nom`, `bs. as`) — also `MULTI_PERIOD` territory.

Stripping either class would corrupt downstream matching. Both counts were re-verified at
HEAD: 1490 internal-dot + 219 multi-token preserved untouched.

---

## 2. The enumeration-gap fix + guard

### Fix (source-edit, not a runtime/builder strip)

`builder_change = false`. We did **not** add a defensive `.strip(".")` in
`_AbbreviationData.__init__`. A runtime strip would make the builder silently diverge from
the source data and **mask** the very source mistakes a guard exists to catch — re-creating
a hidden second normalization. Instead the **data** was made to satisfy the documented
`<abbr>.` keying invariant, and a hard, visible test enforces it.

`sentencesplit/abbreviation_replacer.py` was **not touched** (`git diff 42e175c..HEAD` shows
0 lines there); the U+0130 bare-key exception is intact.

### Guard

`tests/test_languages.py::test_single_token_abbreviations_have_no_trailing_dot`
(commit `00df7a7`), parametrized over **every registered language code** (incl. future
additions), asserts no language has a single-token trailing-dot entry:

```python
offenders = [a for a in abbreviations
             if (s := a.strip()).endswith(".") and s.count(".") == 1 and not any(c.isspace() for c in s)]
assert offenders == []
```

It directly catches the exact rot mode (an entry keyed `<abbr>..` and never enumerated) and
reddens CI the instant such an entry is reintroduced anywhere. **Proven to bite**: the
commit notes record transiently re-adding pl `np.` reddened the `[pl]` case, then reverted.
The pre-existing `test_language_abbreviations_do_not_repeat_literals` is a secondary guard
for the dotless-twin duplicates after dedup. `+26` net new parametrized cases
(2069 → 2095 passing).

---

## 3. Adjudicated intended output diffs per language (pl / ar / sk newly protected)

These are **intended correctness improvements**, not regressions. BC was not a constraint.
Verified at `Segmenter(language=…, clean=False).segment(...)`:

| Lang | Input | Before (V1) | After (this phase) | Verdict |
|------|-------|-------------|--------------------|---------|
| pl | `Zrobił to ok. piętnaście minut temu.` | 2 sentences (split after `ok.`) | **1 sentence** | IMPROVEMENT |
| pl | `Patrz rozdz. trzeci, str. 5.` | split at `rozdz.`/`str.` | **1 sentence** | IMPROVEMENT |
| ar | `المسافة 5 كلم. ثم توقف.` | 2 sentences (split after `كلم.`) | **1 sentence** | IMPROVEMENT |
| sk | `Atď. a tak ďalej.` | (sentence-initial; `atď.` now protected via dotless twin) | **1 sentence** | IMPROVEMENT |

**Linguistic rationale.** Polish `ok.` (≈ "approximately"), `rozdz.` (rozdział, "chapter"),
`str.` (strona, "page"), `np.` (na przykład, "for example"), `itd.` (i tak dalej, "etc."),
`tj.` (to jest, "that is"), `wyd.` (wydanie, "edition"), `tłum.` (tłumaczenie), `nb.`, `rys.`,
`t.` (tom, "volume") are standard mid-sentence abbreviations whose period is **never** a
sentence boundary in these collocations; the V1 behavior of splitting after them was simply
wrong and went uncompensated. Arabic `كلم` (kilometre) / `كج` (kilogram) are unit
abbreviations; mid-measurement they do not end a sentence. Slovak `atď` ("etc.") — the
dotted twin was redundant with the already-present dotless `atď`.

These four languages had the **same gap as Kazakh with NO compensation**, so their dotted
abbreviations were simply never protected before this phase. All 53 are REGULAR-branch
(none prepositive/number), so once enumerated they protect via `RE_REGULAR` — for ar/sk
unconditionally via their `classify_special` policies, for pl when the follower is
lower-case (a capital follower still splits, e.g. `Mam np. psa. To wszystko.` correctly
stays 2 sentences — verified). `languages_expecting_diffs: ["pl", "ar"]` per the plan
(sk's only change was a redundant-twin deletion, behavior unchanged for in-corpus cases).

**The 26-language segment() snapshot diff is EMPTY (`live == baseline`).** This is expected:
the snapshot's fixed sample inputs use the dotted abbreviations only before a *capital* /
non-lowercase follower (e.g. `Mam np. psa, kota itd.`), which never split either way; the
intended pl/ar diffs occur on lower-case-follower inputs that are not in the frozen fixture
set. They were adjudicated directly at the `segment()` level (table above) rather than via
the snapshot.

---

## 4. The Kazakh refactor (passes removed, follower-class policy added)

Kazakh was the **only** language that compensated for the enumeration gap, via a whole-text
per-abbreviation `re.sub` pass. Commit `de7677f` (`refactor(kk)`) replaced it atomically:

**Removed (dead once the 39 kk dots are stripped):**
- `replace_single_period_abbreviations()` — the whole-text per-abbreviation `re.sub` pass.
- `replace_period_of_kazakh_abbr()` — its helper (the Cyrillic/Latin lowercase lookahead).
- `_LOWERCASE_CONTINUATION_CHARS = "a-zа-яёәғқңөұүһі"` — the standalone char class.
- the `self.replace_single_period_abbreviations()` call site in `replace()`.

**Added (mandatory same-commit structural replacement):**
- `KK_POLICY = AbbrPolicy(classify_special=_kk_classify_special, realize_suffix=_kk_realize_suffix)`,
  replacing `ABBR_POLICY = BASE_POLICY`.
- `_KK_WIDE_FOLLOWER_STEMS` — the **frozen set of the 39 formerly-dotted stems** (dotless,
  lowercased).
- `_KK_WIDE_FOLLOWER_CLASS = "[a-zа-яёәғқңөұүһі]"` folded from the deleted constant, and
  `_KK_WIDE_REGULAR_RE` (the base REGULAR shape with that wider follower class).

**Why a per-stem policy, not a blanket follower widening.** The base REGULAR branch uses
ASCII `[a-z]`; the retired pass protected before the WIDER Kazakh-Cyrillic + Latin lowercase
class — but only for the formerly-dotted subset. The always-dotless abbreviations (e.g. `см`
in `См. рис.`) were NOT in the pass and rode the ASCII-follower branch. So `_kk_classify_special`
applies the wide follower class ONLY to stems in `_KK_WIDE_FOLLOWER_STEMS`; every other
abbreviation falls through to the base ASCII-follower dispatch — reproducing the legacy
split exactly. A blanket widening would have newly protected `См. рис.` and regressed.

**Kept (cannot collapse into the per-line classifier):**
- the Cyrillic single-uppercase-initial pre-rule (`^`-anchored, whole-text, pre-split);
- `protect_multi_period_abbreviations_before_parenthesis` (matches interior `∯` produced by
  `replace_multi_period_abbreviations`, so it must stay a whole-text post-pass).

**Net-neutral, verified:**
- `Ол обл. орталығында тұрады.` → **1 sentence** (wide Cyrillic follower; `обл.` protected).
- `См. рис. 3 ниже.` → 2 sentences `['См. рис. ', '3 ниже.']` — exactly as legacy left it
  (`см` not in the wide set; digit follower).
- The kk differential-oracle parity test (`tests/v2/test_oracle.py::
  test_classifier_available_and_at_parity_for_kazakh`) holds — frozen legacy positions stay
  `[]`; the comment was updated to explain the KK_POLICY equivalence.
- 26-language segment snapshot unchanged for kk.

**LOC delta (kazakh.py):** `+145 / -86` = **+59 net** (the verbose KK_POLICY helpers + the
frozen-stem set + explanatory comments are larger than the deleted two-method pass; the
trade is clarity and zero-runtime-cost protection for slightly more declarative source).

---

## 5. Cruft swept

- **`PeriodClassifier._classify_number`** (dead wrapper) — removed in `c0249cb`. The V2
  single-pass refactor (`993ff6f`) rewired live dispatch to `_classify_number_with_suffix`,
  orphaning the thin decision-only `_classify_number` wrapper (no callers in `sentencesplit/`
  or `tests/`, no dynamic dispatch). Its sibling `classify` wrapper stays (the oracle calls
  it). `-4 LOC`, behavior-neutral.
- **Kazakh whole-text pass + helper + constant** (see §4) — `replace_single_period_abbreviations`,
  `replace_period_of_kazakh_abbr`, `_LOWERCASE_CONTINUATION_CHARS`, and the stale comment
  block narrating the now-removed `BASE_POLICY`/dotted-data rationale (rewritten to describe
  KK_POLICY).
- **7 redundant dotted-twin entries** deleted (kk `м.`/`апр.`/`т.`/`мм.`, pl `itd.`/`np.`,
  sk `atď.`) — were literal duplicates of an existing dotless form.

---

## 6. Final gates (at HEAD `c0249cb`)

| Gate | Result | Bar |
|------|--------|-----|
| FULL SUITE | **2095 passed, 1 skipped, 6 xfailed, 0 failed** | 0 failed (was 2069 passed at base; +26 from the new parametrized guard) |
| RUFF lint | **All checks passed!** | clean |
| RUFF format | **727 files already formatted** | clean |
| ZERO-DEP | **3 passed** (`tests/test_zero_dependencies.py`) | green |
| SPAN R-TRIP | **329 passed** (`tests/test_span_roundtrip.py`) | green |
| SEGMENT DIFF | **no diffs (live == baseline)** | every change adjudicated (pl/ar/sk diffs are on out-of-fixture inputs, adjudicated in §3) |
| PERF (short, 3× median) | **0.8716 ms/call** (runs 0.8646 / 0.8716 / 0.8730) | ≤ 0.9266; below the 0.8996 reference |

The 6 xfails are pre-existing/unrelated (ar swine-flu, en `a.m.` mega-case, 2
en-challenging adjacent-abbrev, Pt./B.P./Dr. clinical, #83 French char-span); `xfail_strict`
means none flipped.

---

## 7. Honest remaining backlog (high-risk data-quality items LEFT UNTOUCHED)

This phase deliberately scoped to the 53-entry mechanical convergence + the dead code it
unblocked. The following are **not** addressed and remain open:

1. **Messy multi-token / mixed entries in other languages** — Dutch, Italian, and others
   carry inconsistent multi-token and mixed-dot entries that ride `MULTI_PERIOD_ABBREVIATION_REGEX`.
   They were intentionally not touched (the 219 spaced + 1490 internal-dot entries are
   structural), but their internal consistency / correctness was not audited here. A
   dedicated data-quality pass per language is warranted.
2. **Complete the single-pass model** (V2 report §5 #3, still open) — the titled-name and
   a.m./p.m. fixes live in downstream passes, not inside the classifier; the RFC end-state
   (one decision from the original text) is not yet reached.
3. **CI hermeticity** (V2 report §5 #5) — `tests/test_corpus_compare_segmenters.py` needs
   `benchmarks/corpus_compare/__init__.py` committed (or `pythonpath = ["."]`) so a fresh
   clone collects cleanly; this is the 1 skipped test.
4. **vs-pysbd `differential_profile`** — re-run where pysbd installs, to confirm the
   cross-library perf story end-to-end (could not install here per the ARM-native-libs note).
5. **The 6 xfails** — open correctness backlog for a future fix; `xfail_strict` will flip
   them green automatically when fixed.

---

## 8. Commit ledger (this phase, on `feat/v2-abbreviation-engine`)

| SHA | Subject |
|-----|---------|
| `fd37a27` | `fix(abbr): strip trailing dot from ar/pl/sk single-token abbreviations` |
| `de7677f` | `refactor(kk): strip trailing dot from Kazakh abbreviations; retire whole-text pass` |
| `00df7a7` | `test(abbr): guard against single-token abbreviations stored with a trailing dot` |
| `c0249cb` | `refactor(abbr): drop dead _classify_number wrapper from PeriodClassifier` |

Source LOC across the phase: **5 files changed, +156 / −104** (net **+52**).
All work staged by explicit path; `main` untouched; nothing pushed.
