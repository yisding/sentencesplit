# Revised Plan: V2 single-pass period classifier (correctness + maintainability refactor)

**Supersedes** the recommendation framing of `ABBREVIATION_ENGINE_V2_RFC.md`, incorporating the
findings of `V2_RFC_EVALUATION.md`. The RFC's *design* (a single-pass per-period classifier) is
adopted; its *justification* and *gates* are revised.

## 0. Frame (decided)

- **Backwards-compat is NOT a constraint.** Byte-identical output across languages is **not** a goal.
- **This is a correctness + maintainability refactor, NOT a perf project.** The measured Amdahl
  ceiling for the classifier's target work is ~10–13% on the densest legal input and ~0 on normal
  prose; a real classifier captures less (it keeps the Aho-Corasick discovery scan). Do **not** sell
  or gate this on speed. The win is: delete order-dependence (a documented bug class), collapse
  **9 override modules / ~13 method overrides / 14 `AbbreviationReplacer` subclasses** into one
  classifier + small per-language policy hooks, and make each per-period decision unit-testable.
- **The classifier may FIX load-bearing quirks rather than reproduce them** (German/Bulgarian
  unescaped `am` → escape everything; the `&ᓷ&&ᓷ&` placeholder → clean PROTECT/PLACEHOLDER decision).
  Any resulting output change must be a *reviewed, Golden-Rule-anchored* diff judged on linguistic
  correctness — never silent.

## 1. Gates (revised — this is the acceptance contract)

Primary gate (must stay green at every commit):
1. **Full test suite** — `uv run pytest tests/` (all `tests/lang/*`, `tests/regression/*`,
   `tests/test_*`). The ~376-line English Golden Rules and every language's Golden Rules are here.
2. **Curated correctness corpus** (new, Phase 0) — hand-labeled boundary decisions, *including cases
   the legacy engine gets wrong*, so the gate rewards correctness, not legacy-mimicry.
3. **Zero-dependency import** (`tests/test_zero_dependencies.py`) + **ruff** check & format.
4. **Span round-trip** (`tests/test_span_roundtrip.py`) exact; **no crash** on the fuzz corpus.

Debugging aid (NOT a gate — demoted from the RFC's §8.1 "primary"):
5. **Differential oracle** — `legacy_protect_positions(text, lang)` vs `classifier_protect_positions`.
   A position-level legacy==new equality check *is byte-identity in disguise*; it re-imports the
   constraint we dropped and freezes today's buggy behavior. Use it only to **locate** `new != old`
   and **adjudicate** each diff as correct/incorrect against the Golden Rules — never to require
   equality. (Exception: in Phase 2 we *target* oracle-equality for English as a fast proof of
   faithfulness, because English's legacy output is known-good; we relax it for the override
   languages where legacy has quirks worth fixing.)

## 2. Design (the target the implementation builds)

A new `PeriodClassifier` replaces the **per-line abbreviation-protection step** inside
`AbbreviationReplacer.search_for_abbreviations_in_string` (`abbreviation_replacer.py:582`). Everything
around it in `replace()` (`:358`) is unchanged initially: the upstream single-letter/possessive rules,
`replace_multi_period_abbreviations`, the compact-ampm / uppercase-initialism / allcaps-imprint /
ampm / standalone-I passes all stay. The classifier is a drop-in for one step that emits the same
`∯` sentinels at the chosen positions.

**Core abstraction — classify each candidate period once, against ORIGINAL text, then rebuild once:**

```
enumerate_candidates(line, data):   # reproduce the reachability gate, not "every period"
    # a period that completes a known "<abbr>." at a word boundary (AC prefilter @:190,
    # occurrence semantics @:599-604, dedup @:609). NOT "every period whose prev token is in the set".
classify(site, data, policy, split_mode, flags) -> PROTECT | BOUNDARY | PLACEHOLDER(repl)
    # reads only bounded local context, from the ORIGINAL line (no sentinel from a prior decision)
    # three branches preserved from scan_for_replacements (:644):
    #   regular     -> replace_period_of_abbr suffix  (:568/574)
    #   prepositive -> _replace_with_escape `\.(?=(\s|:\d+))`  (+ starter-aware en_legal callback :631)
    #   number      -> _replace_number_abbr (:613), incl. lower/upper/Roman/?? cases
rebuild(line, decisions): single pass applying all PROTECT(∯)/PLACEHOLDER edits by position.
```

**Order-dependence is re-encoded, not deleted** (per evaluation §4): the legacy follower class and
initialism chains are read from *mutated* text. The classifier rebuilds them from the **original**
periods — `_initials_chain_start` (`:268-291`) becomes "walk left over `X.X.X` in the original line";
`mpa_replace` follower reads use original offsets. The chain/whole-span must be classified together so
`U.S.A.`, `p. No.`, and adjacent abbreviation runs decide consistently from one context.

**Per-language specialization = a policy object, not a method override:**

```
class AbbrPolicy:
    follower_classes()            # which followers PROTECT (base [a-z]; en_es_zh [^\W\d_]; CJK/kana; Cyrillic)
    boundary_chars()              # \s + elision ' ’ for fr/it (data-driven from ELISION_CHARACTERS)
    candidate_filter()            # reachability gate variant
    classify_special(site, ...)   # german "before whitespace", slovak literal-span, arabic bare \.,
                                  # russian compare-phrase + SENTENCE_FINAL set, bulgarian interior-period
    stages()                      # pre/classify/post descriptor: kazakh adds rules before+after;
                                  # deutsch reorders replace(); russian/kazakh upstream Cyrillic single-letter
```

A language may override **one branch** and inherit the other two (slovak/bulgarian/russian override
only the regular branch — evaluation §4). The policy is a staged descriptor, not three flat methods.

## 3. Preservation spec — the load-bearing items the evaluation flagged (do NOT under-scope)

Fatal-if-ignored (would ship wrong output):
- **Russian `SENTENCE_FINAL_ABBREVIATIONS`** (`russian.py:104-117`, 12 members) + `_is_embedded_occurrence`
  (`:135-142`): period stays a BOUNDARY before a Cyrillic capital for these (`рус. Большой` splits).
  Model as a first-class data table + bounded-lookbehind callback.
- **dutch does NOT set `CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`** — only the 5 (english/en_legal/danish/
  greek/en_es_zh) do. Do not enable it for dutch.
- **en_es_zh follower class `[^\W\d_]`** (any Unicode letter), not base `[a-z]`.

Fixable coupling the classifier must re-encode (single-pass-achievable):
- Interior-period protection spans 3 passes, one (`WithMultiplePeriodsAndEmailRule`) running *after*
  the replacer (`processor.py:477-484`). Classifier must subsume it or leave exactly what the email
  rule catches; re-validate `replace_multi_period_abbreviations` interaction (it sees literal `.`).
- Bulgarian intra-method order-dependence (`bulgarian.py:99-113`): classify the whole span at once.
- The automaton `<abbr>.` prefilter (`:190`) + occurrence-dedup (`:609`) + period-less skip (`:601`)
  is the reachability gate that makes the wildcard override regexes (bulgarian/german/arabic) safe.
- Kazakh's 3 passes (`kazakh.py:331-368`); its `_LOWERCASE_CONTINUATION_CHARS`.

Quirks to FIX (BC not required — delete, don't reproduce), each as a reviewed Golden-Rule-anchored diff:
- German/Bulgarian unescaped `am` (`deutsch.py:232-234`) → `re.escape` everything.
- `&ᓷ&&ᓷ&` placeholder injection → clean `PLACEHOLDER` decision type (still consumed by the same
  downstream restore, but modeled explicitly). Preserve downstream contract in Phase 2; clean up with
  a test in a later phase.

## 4. Phased rollout (each phase commit-or-revert; a failed hard gate never advances)

- **Phase 0 — Harness.** Branch `feat/v2-abbreviation-engine`. Build: the differential oracle
  (instrument legacy `scan_for_replacements` to record `∯` positions; `legacy_protect_positions`);
  the curated English correctness corpus; capture the green baseline (full suite + benchmarks). Gate:
  harness runs, baseline captured.
- **Phase 1 — Design.** Independent design proposals → judged → one winning design spec for
  `PeriodClassifier` + `AbbrPolicy` (module layout, candidate enumeration, the 3 branches, chain
  rebuild-from-original, policy interface). No engine code yet.
- **Phase 2 — English classifier (the go/no-go prototype).** Implement `PeriodClassifier` for the
  base class (covers `en`/`en_legal`, which override 0 scan methods). Gate: full suite green +
  English Golden Rules green + correctness corpus green + zero-dep + ruff + span round-trip; oracle
  **targeted to equality on the English corpus** (fast faithfulness proof) with any intended diff
  reviewed. Acceptance is **clarity + correctness + no order-dependence**, explicitly **not** a speed
  delta — but it must regress no benchmark beyond noise. Commit if green; abort the whole effort if
  the prototype is not clearly cleaner (per evaluation §5).
- **Phase 3 — Go/no-go review.** Adversarial multi-lens review of the English classifier
  (correctness vs legacy, order-independence proof, design/LOC simplicity, perf no-regression).
  Synthesis decides GO or NO-GO. NO-GO ⇒ stop, keep legacy, report.
- **Phase 4 — Base-class languages.** spanish, danish, greek, dutch, italian, french (elision),
  polish, hindi, marathi, tagalog, armenian, amharic, burmese, urdu — most inherit the base classifier
  with only flags/elision. Validate each language's tests + oracle-adjudication + per-language
  `segment()` diff vs main; fix the few needing a flag/elision hook. Per-language commit-or-revert.
- **Phase 5 — Override languages, one at a time** (risky; sequential), each as a policy object:
  en_es_zh, german, russian, slovak, bulgarian, arabic/persian, chinese, japanese, kazakh. Gate:
  that language's tests + oracle-adjudicated diffs (reviewed, Golden-Rule-anchored) + full suite.
  Per-language commit-or-revert; a language that can't pass its gate is **deferred** (left on legacy),
  not forced.
- **Phase 6 — Cutover & report.** Once every shipped language passes, delete the legacy per-line
  protection path + the sentinel-injection cruft it required. Final full suite + all-language
  `segment()` diff + fuzz + perf delta. Write `analysis/V2_IMPLEMENTATION_REPORT.md`: what landed,
  what was deferred and why, every adjudicated output diff with its linguistic rationale.

## 5. Non-negotiables (from the evaluation)

1. The differential oracle is a **debugging aid**, not the gate. The gate is Golden Rules + correctness
   corpus + full suite.
2. No phase advances on a red hard gate. Commit-or-revert per stage / per language.
3. Output changes are allowed but must be **reviewed, Golden-Rule-anchored, and logged** — never silent.
4. Perf is a *no-regression* check, never an acceptance driver.
5. Never push; all work on `feat/v2-abbreviation-engine`.
