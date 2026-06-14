# RFC: A single-pass period classifier for abbreviation boundary detection

**Status:** Proposal / design exploration. No code changes — this is the plan an
implementer would execute (or decide not to).

**Author note / honesty:** this came out of a performance investigation that
already landed a measured **+21.7%** (period pre-filter, Aho-Corasick DFA, phase
guards — all byte-identical). Those were the cheap, safe wins. This RFC is about
the *next* lever, which is **not** cheap or safe: it is an architectural change
to the heart of the segmenter. The recommendation up front is deliberately
conservative — read §10 before §7.

---

## 1. TL;DR

The abbreviation engine inherits pySBD's model: *segmentation as a sequence of
global `re.sub` rewrites*, with decisions carried in-band as sentinel characters
(`∯`, `&ᓷ&`, …). The linguistically-essential task — deciding whether a given
period is a sentence boundary — is an inherently **local, per-period
classification**. Modeling it as repeated global string rewrites turns that into:

- **O(distinct-abbreviations × text-length)** work (a global `re.sub` per
  abbreviation); ~19% of a normal-prose call, ~28% (≈1,800 `re.sub`/call) of
  abbreviation-dense legal text;
- **order-dependence** (each rewrite sees the `∯` the previous one inserted) —
  bug-prone, and the single biggest obstacle to optimizing the current code;
- **six divergent re-implementations** of the same decision across languages.

A **single-pass period classifier** — visit each candidate boundary once, decide
locally, batch-apply — would be O(text-length), eliminate order-dependence, and
collapse the six per-language rewrites into one classifier + small per-language
hooks. It is the architecturally-correct design.

The catch: the current quirks (down to German's *unescaped* lookbehind and the
exact order-dependent tie-breaks) are now the **product spec** — they are the
historically-tuned golden output. So this is not "refactor the engine," it is
"re-derive every golden behavior in a new paradigm." That is a multi-week,
high-risk project. **Recommended only as a deliberate v2 effort**, English-first,
gated by a differential oracle, and shipped as a major version that *explicitly
permits* tiny output changes rather than fighting for byte-identity across 24
languages.

---

## 2. Problem statement (measured)

`Processor.replace_abbreviations` → `AbbreviationReplacer.search_for_abbreviations_in_string`
(`abbreviation_replacer.py:582`) → per matched abbreviation, `scan_for_replacements`
(`:644`) runs a **global** `re.sub` over the whole line to protect that
abbreviation's periods (via `_replace_with_escape` / `replace_period_of_abbr` /
`_replace_number_abbr`). Profiling (`benchmarks/differential_profile.py`,
`phase_profile.py`):

| input | abbr phase | `re.Pattern.sub`/call |
|-------|-----------:|----------------------:|
| normal English prose | ~19% | ~240 |
| abbreviation-dense legal | ~28% | ~1,800 |

The dominant term is the per-occurrence global `re.sub`: each scans the entire
text to protect one abbreviation's periods, so cost scales with
*distinct-abbreviations × text-length*.

The cheap wins are already taken (the `<abbr>.` pre-filter removed the
false-positive `finditer` re-scans; the DFA halved the scan). What remains is
structural and cannot be removed without changing how decisions are made.

---

## 3. Essential vs. accidental complexity

**Essential (the linguistics — must be preserved in any design):**
- the abbreviation lists and the prepositive / number-abbr distinctions;
- follower classification: capital vs lowercase vs digit vs CJK ideograph vs
  another abbreviation vs `(`/`:`;
- the split-mode bias on genuinely ambiguous cases;
- multi-period abbreviations (`U.S.A.`), a.m./p.m., standalone `I`, all-caps
  initialisms, all-caps imprints;
- language-specific follower rules (CJK followers, Cyrillic capitals, French/
  Italian elision, German date handling, Kazakh/Cyrillic lowercase classes).

Every one of these is a **local decision about one period with bounded
lookahead/​lookbehind.** None fundamentally needs global state or another
period's decision.

**Accidental (consequences of the global-rewrite model — candidates for removal):**
- the per-occurrence global `re.sub` (the perf cost);
- order-dependence between abbreviation rewrites;
- the `finditer`-then-global-`re.sub` redundancy (find the position, then re-find
  it globally);
- the six divergent `scan_for_replacements` / `replace_period_of_abbr` rewrites
  (same essential decision, six idioms);
- in-band sentinel mutation as the *only* state model for abbreviation decisions
  (the `&ᓷ&&ᓷ&` placeholder injection is the clearest symptom).

---

## 4. Proposed design — single-pass period classifier

### 4.1 Core abstraction

Replace "mutate the string per abbreviation" with "classify each candidate period
once, then apply all decisions in one pass."

```text
# One pass over the line:
for each candidate site (a '.' or language terminator, with the token before it):
    decision = classify(prev_token, site_index, text, ctx)
        -> PROTECT  (period is intra-abbreviation; becomes ∯)
        -> BOUNDARY (period ends a sentence; stays '.')
        -> PLACEHOLDER(...)  (the rare number-abbr "??" -> &ᓷ&&ᓷ& case)
# Then a single rebuild applies all PROTECT/PLACEHOLDER edits by position.
```

- `prev_token` lookup against the abbreviation/prepositive/number sets is O(1)
  (hash), using the same `_AbbreviationData` already built per language.
- `classify` reads only **local** context (a bounded window after the period, a
  bounded window before for initialism chains). It returns a decision, it does
  not mutate.
- The single rebuild is the only string allocation — O(text-length) total.

This keeps the rest of the pipeline (which is also sentinel-based: quotes, lists,
numbers) unchanged: the classifier still emits `∯` at the chosen positions, so it
is a drop-in for `replace_abbreviations`'s output, not a whole-pipeline rewrite.

### 4.2 Language specialization becomes a hook, not a rewrite

The six divergent overrides collapse to a small interface, e.g.:

```text
class AbbrPolicy:
    def follower_classes(self) -> ...        # which followers protect (CJK, Cyrillic, latin)
    def boundary_chars(self) -> set[str]     # \s, plus elision ' ’ for fr/it
    def classify_special(self, ...) -> ...   # German "before whitespace", Slovak literal,
                                             # Russian compare-phrase, Arabic "always"
```

German's "protect any `<abbr>.` before whitespace," Slovak's "literal
all-periods replace," Arabic's "bare `\.`", Russian's compare-phrase callback —
each becomes a few lines in a policy object instead of a re-implemented global
sub. The classifier core is shared; the per-language *decision* is isolated and
testable.

### 4.3 Why order-dependence disappears

All decisions are computed against the **original** (un-mutated) text, together,
then applied once. `U.S.A.` is classified as one span; adjacent abbreviation
chains (`p. No.`) are each classified from the original context, so there is no
"did the previous `∯` change my boundary char" hazard. This is a *correctness*
improvement, not just speed — but it is also exactly why output can differ from
today in edge cases (see §6).

---

## 5. The preservation spec (what the classifier must reproduce)

Distilled from a full survey of every `lang/` module. An implementer must treat
this as the acceptance surface.

### 5.1 Base pipeline order (`AbbreviationReplacer.replace`, `:358`)
`PossessiveAbbreviationRule`, `KommanditgesellschaftRule`, `SingleLetterAbbreviationRules`
→ per-line abbreviation protection → `replace_multi_period_abbreviations` →
`_COMPACT_AMPM_RE` → `_UPPERCASE_INITIALISM_BOUNDARY_RE` (callback) →
`protect_allcaps_imprint_abbreviations` → `apply_ampm_boundary_rules`
(→ `restore_non_ascii_ampm_boundaries`) → `restore_standalone_i_boundaries`.
The classifier replaces only the **per-line abbreviation protection** step; the
surrounding passes stay (initially).

### 5.2 The suffix-decision patterns (the classifier's decision table)
All emit `∯`; boundary prefix is `(?<=[{boundary}]{escaped})`:

| rule | suffix lookahead after the period |
|---|---|
| regular (`replace_period_of_abbr`) | `(?=((\.\|\:\|-\|\?\|,)\|(\s([a-z]\|I\s\|I'm\|I'll\|\d\|\())))` |
| prepositive | `(?=(\s\|:\d+))` |
| starter-aware prepositive (en_legal only) | `(?=(\s\|:\d+))` + callback (`:`→protect, sentence-start→boundary, else protect) |
| number, lowercase follower | `(?=(\s\d\|\s+\(\|\s\?\?(?!\?)\|\s[IVXLCDM]+\b))` |
| number, upper, conservative | `(?=\s[^\W\d_])` |
| number, upper, non-conservative | `(?=\s(?:[IVXLCDM]{2,}\|[VXLCDM])\b)` |
| number `??` placeholder | `(?<=…∯)\s\?\?(?!\?)` → ` &ᓷ&&ᓷ&` |
| chinese / japanese | base suffix + CJK/kana branch |
| en_es_zh | base suffix + `[㐀-鿿]` branches; ASCII-upper + heuristic-set gate |
| kazakh | base suffix with Cyrillic+Kazakh lowercase class |
| german | `(?=\s)`, `am` **not escaped**, whole-text (not per-line) |
| arabic/persian | bare `\.` (any follower), `am` escaped |
| russian | `(^\|\s)(abbr)\.` + Cyrillic-capital / `ср` compare-phrase callback |
| slovak | literal `abbr+"."` → all interior periods + trailing → `∯` |
| bulgarian | `(?<=\s abbr)\.` / `(?<=^abbr)\.` (unescaped) + interior-period sub |

### 5.3 Class-level flags that steer the decision (must be honored)
`CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE` (en/en_legal/danish/greek/dutch…),
`PROTECT_ALLCAPS_IMPRINT_SUFFIXES`, `RESTORE_STANDALONE_I_BOUNDARIES`,
`NON_LATIN_CAPITAL_STARTS_SENTENCE` (greek), `STARTER_AWARE_PREPOSITIVE`
(en_legal only), `AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST={"st"}`,
`TWO_/UPPERCASE_INITIALISM_SPLIT_MIN_RANK` (dutch=2), the 14-tuple
`ALWAYS_JOIN_TWO_LETTER_INITIALISM_PHRASES`, and the data-driven `elision_chars`
(fr/it) → `boundary_class`.

### 5.4 The genuinely hard parts (do not under-scope these)
1. **Context-reading callbacks**: `restore_uppercase_initialism_boundary`
   (walks left over `X∯X∯X`, reads split-mode, downstream follower),
   `mpa_replace` (scans up to N normalized downstream words for the
   ALWAYS_JOIN phrases), starter-aware, Russian compare-phrase, standalone-I,
   non-ASCII a.m./p.m. — each must be reproduced as bounded-lookahead in the
   classifier.
2. **`replace_multi_period_abbreviations`** runs *after* protection and only
   sees literal `.` (not `∯`); bulgarian/kazakh add extra passes precisely
   because the shared machinery misses Cyrillic interior periods; greek swaps
   the regex. The classifier changes *when* periods become `∯`, so this
   interaction must be re-validated, not assumed.
3. **The `&ᓷ&&ᓷ&` placeholder insertion** is a token injection, not a
   protect-at-index — the decision type `PLACEHOLDER` must model it.
4. **`am` not escaped (german, bulgarian)** — relied-upon (quirky) semantics;
   reproduce exactly or accept a diff.
5. **`replace()`-level divergence**: german/kazakh override the whole pipeline
   order; russian/kazakh add upstream Cyrillic single-letter rules. The policy
   object must let a language add/remove whole stages.

---

## 6. Will it be byte-identical? (be honest)

For the **base-class** languages, a faithful classifier *can* be byte-identical
— each decision is a deterministic function of local context, and the suffix
patterns translate to position-anchored `pattern.match(text, period_index+1)`
checks. The risk concentrates in (a) order-dependence edge cases (adjacent
abbreviation chains), (b) the multi-period interaction, (c) the unescaped-`am`
languages.

Realistically, expect a **handful of intentional, reviewed diffs** in pathological
adjacency cases. That is why the recommended framing is a **major version that
permits small, reviewed output changes**, with the Golden Rules as the
acceptance anchor — not an all-or-nothing byte-identity fight.

---

## 7. Implementation plan (phased, English-first)

**Phase 0 — Acceptance harness (before any engine code).**
- A differential oracle: `assert classifier_protect_positions(text) == legacy_protect_positions(text)` for a large corpus, derived by instrumenting the current `scan_for_replacements` to record which periods it turns into `∯`.
- Wire the existing gates: full suite + Golden Rules; the all-26-language
  `segment()` corpus diff (the harness from the +21.7% work); the 13k-input
  fuzz (crashes + span round-trip); `differential_profile.py` for the perf delta.

**Phase 1 — English classifier behind a flag.**
- Implement the classifier for `en`/`en_legal` only, selected by an env/opt-in
  flag, with the legacy path as default and reference.
- A/B every Golden Rule + a multi-KB English corpus diff; iterate to zero
  *unintended* diffs; record any intended diffs with rationale.
- Measure: must show the expected O(text) win on abbreviation-dense input with
  no regression elsewhere (CodSpeed).

**Phase 2 — base-class languages.** Spanish, polish, danish, greek, dutch,
italian, french (elision), and the Indic/other base inheritors. Each gets the
shared classifier + its flags/elision; per-language corpus diff.

**Phase 3 — the override languages**, one at a time, each as a policy object:
en_es_zh, german, russian, slovak, bulgarian, arabic/persian, chinese, japanese,
kazakh. These are the risky ones; do them last, each behind the oracle.

**Phase 4 — cutover.** Flip the default once every language passes its gate;
keep the legacy path one release behind the flag; then delete it and the
sentinel-injection cruft it required.

---

## 8. Guardrails

1. **Differential oracle (primary).** Position-level equality of protected
   periods, legacy vs new, over a large multilingual corpus — caught at the
   abbreviation layer, not just final output, so a regression is localized.
2. **Golden Rules as the spec anchor.** `tests/lang/*` must stay green; any
   intended change is a reviewed Golden-Rule edit with rationale, never silent.
3. **All-26-language `segment()` diff** (branch vs `main`) on real KB-scale text
   per language — the leg that caught the U+0130 `İ` bug that English-only
   verification missed. Thin-coverage languages (amharic, burmese, greek,
   hindi, urdu) get hand-built abbreviation stressors.
4. **Fuzz** (13k adversarial inputs × 26 languages): zero crashes, zero span
   round-trip violations, `clean=True` robust, streaming feed-at-once contract.
5. **CodSpeed perf gate**: the change must *improve* the abbreviation benchmarks
   and regress nothing; add an abbreviation-dense benchmark input.
6. **Feature flag + parallel paths** through Phases 1–3 so production never runs
   the unproven path and any divergence is A/B-debuggable.
7. **Unicode/casing stressors** baked into the corpus (İ, ı, ß, ligatures,
   full-width digits, combining marks) — the casing seam that already bit us.
8. **Concurrency**: the classifier and any new caches keep the existing
   publish-after-build-under-lock discipline (see the documented invariants in
   `_evict_profile` / `AhoCorasickAutomaton`).

---

## 9. How to check the work (acceptance criteria)

A phase is "done" when, for its languages:
- the differential oracle reports zero unintended protected-period diffs over the
  corpus (intended diffs enumerated + Golden-Rule-anchored);
- `tests/lang/*` + `tests/regression/*` green; new regression tests for every
  behavior the survey flagged as hard (§5.4);
- the all-language `segment()` diff is empty (or a reviewed allowlist);
- fuzz clean; span round-trip exact;
- CodSpeed shows the abbreviation phase faster with no other regression.

---

## 10. Risk / reward and the recommendation

**Reward:** O(text) abbreviation handling (meaningful on abbreviation-dense /
legal / academic text; modest on normal prose, where the AC scan and always-on
rule passes dominate), **plus** a markedly simpler, order-independent engine that
collapses six divergent rewrites into one classifier — the larger long-term win
is maintainability and correctness robustness, not raw speed.

**Risk:** very high. It rewrites the core decision logic that produces the
historically-tuned golden output, across 26 languages with six bespoke overrides,
context-reading callbacks, and load-bearing quirks. The byte-identical bar is the
expensive part.

**Recommendation:** **Do not undertake this as an incremental optimization.** The
honest options are:
- **(a) Leave it.** The library is already +21.7% and competitive with pySBD; the
  cruft is contained and tested. This is the default recommendation.
- **(b) A deliberate v2 engine**, only if abbreviation-engine speed or the
  six-way maintenance burden becomes a real priority — executed as above,
  English-first, shipped in a major version that permits small reviewed diffs.

Start (b), if at all, with a **throwaway English-only prototype** measured
against the English Golden Rules + a branch-vs-`main` diff, to prove the paradigm
and quantify the real speed/clarity delta *before* committing to all 24 languages.

---

## 11. Alternatives considered

- **Incremental window optimization** (cap each global `re.sub`'s scan to a
  window around known occurrence positions, base-class only): smaller blast
  radius but still order-dependence-risky, narrow reward, and leaves the six
  overrides slow. Not recommended — most of the risk, little of the architectural
  benefit.
- **Compiled-alternation discovery** instead of the automaton: measured *slower*
  (3–5×) for ~200 short patterns; rejected during the +21.7% work.
- **`str.translate` for the punctuation callback**: measured ~6% *slower*;
  rejected.

## 12. Open questions

- Is a small, reviewed set of output diffs acceptable for a major version, or is
  strict byte-identity a hard product requirement? (This single answer changes
  the project's cost by an order of magnitude.)
- Do downstream users depend on the exact current segmentation of abbreviation
  edge cases (i.e., is the golden output a contract or a default)?
- Is the abbreviation-dense / legal use case important enough to justify (b)?
  (`en_legal` ships, so there is at least one first-class consumer.)
