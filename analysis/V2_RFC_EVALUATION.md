# Evaluation: RFC — Single-pass period classifier for abbreviation boundary detection

**Target:** `analysis/ABBREVIATION_ENGINE_V2_RFC.md`
**Frame:** Backwards-compat is **NOT** a constraint. Goal = high correctness + high performance.
**Method:** Adversarial; every claim opened against source and re-measured with the repo's profilers.

---

## 1. Verdict

The RFC's *descriptive* analysis of the existing engine is excellent — its structural model
("segmentation as a sequence of global `re.sub` rewrites, one per abbreviation, carried in-band
via `∯`"), its cited line numbers, and its per-language suffix-pattern table are all accurate to
the source. Its *quantitative* analysis is the weak part: the headline §2 cost figures
(`~240 re.sub/call` normal, `~1,800` legal, `~19%/~28%` phase shares) are **not reproducible** from
the cited benchmarks and overstate the per-call sub count by ~3-10x; `~240` is in fact **pysbd's**
number, not ours. The genuine, empirically-grounded ceiling for the work the classifier targets is
**~10-13% of total call time on the densest realistic legal input, and ~0 on normal prose** — and a
real classifier captures less than that because it still pays the Aho-Corasick discovery scan it
keeps. So the RFC's own §10 instinct ("(a) leave it; the real win is maintainability, not speed") is
**correct**, but for a reason it buries: the perf prize was never large.

**Given BC is not a constraint, the recommendation sharpens to: adopt-with-changes, reframed as a
correctness+maintainability refactor — not a perf project.** Removing byte-identity collapses most of
the RFC's "very high risk" (the differential-oracle byte-fight, the bug-for-bug reproduction of
German's unescaped lookbehind and the `&ᓷ&&ᓷ&` placeholder injection). It does **not** flip the
default to "(b) for speed," because the speed delta is single-digit-percent at best. It *does* make
(b) more attractive on its true merits: deleting order-dependence (a documented bug class), collapsing
**9** override modules into one classifier + policy hooks, and making per-language decisions
unit-testable. Pursue it English-first, gate on the 785 Golden Rules + a curated correctness corpus
(NOT the legacy engine as oracle), and let it *fix* the load-bearing quirks rather than preserve them.

---

## 2. RFC accuracy scorecard

| Section | Rating | Key evidence |
|---|---|---|
| §1 TL;DR / §2 perf claims | **overstated** | Measured whole-pipeline `re.Pattern.sub`/call = **66 (short) / 80 (medium)**, not ~240; abbr-phase-attributable ≈ **7/call**. `~240` matches **pysbd** (`differential_profile.py --size medium` → pysbd `sub=243.0`). No legal corpus exists in any of the 3 named profilers (`differential_profile.py:36` `_SAMPLES` = short/medium/large, all one prose string), so `~1,800`/`~28%` is unreproducible. `~1,800` is only reached on multi-KB text. |
| §2 cost model ("O(distinct-abbr × text-length)") | **has-gaps** | Per-abbreviation `re.sub` is **per-line** (`abbreviation_replacer.py:365-368` splits on `splitlines(True)`), not whole-text (German is the one whole-text exception, `deutsch.py:222`). And `search_for_abbreviations_in_string` **dedups** occurrences (`:609` `dict.fromkeys`, comment: "keep work linear"): 16× text → only 3.5× subs. So it is O(distinct (abbr, follower-char) variants × line-length), sub-linear in occurrences — not the implied quadratic. |
| §5.1 base pipeline order | **accurate** | `replace()` order matches the source pass-for-pass (`abbreviation_replacer.py:359-399`). |
| §5.2 suffix-decision table (regexes) | **accurate (rows) / has-gaps (header)** | Every per-language regex row verified verbatim. BUT the framing header "All emit `∯`; boundary prefix is `(?<=[{boundary}]{escaped})`" is **false for 6/7 overrides + the `??` row**: russian uses capture-group `(^\|\s)(abbr)\.` (no lookbehind, `russian.py:179`); slovak uses **no regex** (`txt.replace(abbr+".", ...)`, `slovak.py:40-41`); bulgarian/german interpolate **unescaped** `abbr`/`am` (`bulgarian.py:101`, `deutsch.py:233`); the `??` row emits `&ᓷ&&ᓷ&`, not `∯` (`abbreviation_replacer.py:628`). Self-contradicts its own table. |
| §5.3 class-level flags | **accurate apart from one error** | Flag inventory matches code. **Error:** lists `dutch` under `CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE` — dutch never sets it (only `UPPERCASE_INITIALISM_SPLIT_MIN_RANK=2`, `dutch.py:8-12`). The combined `TWO_/UPPERCASE_INITIALISM_SPLIT_MIN_RANK (dutch=2)` also overstates — dutch raises only the UPPERCASE one. |
| §5 as a reimplementation spec | **has-gaps** | Missing load-bearing data/behavior: Russian `SENTENCE_FINAL_ABBREVIATIONS` (12-member set, `russian.py:104-117`) + `_is_embedded_occurrence`; en_es_zh follower class `[^\W\d_]` (any Unicode letter) vs base/zh/ja `[a-z]` (`en_es_zh.py:91`); kazakh's 3 extra passes (`kazakh.py:331-368`); the automaton `<abbr>.` prefilter reachability gate (`:190`). Slovak/Bulgarian/Russian override **only the regular branch** and inherit base prepositive + number-abbr dispatch — the table implies total override. |
| §4 design (single-pass classifier) | **sound but order-dependence is overstated as "disappears"** | The trichotomy PROTECT/BOUNDARY/PLACEHOLDER is right. But §4.3 "order-dependence disappears" is **overstated**: followers are read from *mutated* text (`mpa_replace` reads `self.text` after the protect-sentinel was inserted, `abbreviation_replacer.py:497-554`); the initialism walk-left (`:123`, `:268-291`) only matches the post-mpa sentinel form; Bulgarian's interior-period sub is keyed on its own trailing sentinel (`bulgarian.py:99-113`). Order-dependence must be **re-encoded** (rebuild chains/followers from original periods), not removed. Achievable single-pass, but it is re-derivation, not deletion. |
| §6 byte-identity ("base-class can be byte-identical") | **optimistic** | Credible for trailing-period suffixes, but byte-identity also requires the mpa-vs-email interior split (across **3** passes, one running *after* the replacer, `processor.py:477-484`), the sentinel-walk chain rebuild, the all-caps imprint pass (`:423`), and ampm passes that run on mutated text. **Moot now** — drop byte-identity as a goal. |
| §10/§12 recommendation | **mixed (right call, wrong reason; misframes the cost driver)** | Default "(a) leave it / real win is maintainability" is correct. But §10's "the AC scan dominates normal prose" is **false** (AC scan = 7% on no-abbr prose; always-on per-segment `apply_rules` boundary passes dominate). §12's "byte-identity changes cost by an order of magnitude" is the right axis but frames the unlock backwards: dropping byte-identity removes risk, it does not reveal a speed prize. |
| §11 rejected alternatives | **unverifiable** | "3-5× slower alternation" and "~6% slower `str.translate`" have **no benchmark in the repo** (grep of `benchmarks/`, git log: nothing). `abbr_scan_compare.py` compares AC vs a plain `in`-loop — a different comparison — and AC actually **loses** on large/huge (ratio 0.75-0.88). |

---

## 3. Performance reality (the empirically-grounded ceiling)

**Realistic Amdahl ceiling for the classifier's target work: ~10-13%, and that is the *theoretical*
ceiling (drive per-occurrence protection `re.sub` time to 0); a real classifier achieves less.**

Reproduced via cProfile caller-attribution (re-wrapper + proportional C-level `Pattern.sub` time)
over `segment()`:

| input | winnable / total | ceiling |
|---|---|---|
| en SHORT (87c) | 211.6 / 2043.8 µs | **10.4%** |
| en MEDIUM (198c) | 425.3 / 3853.9 µs | **11.0%** |
| en_legal DENSE x4 (~3060c) | 3928 / 29926 µs | **13.1%** |
| en_legal DENSE x10 | 10826 / 79592 µs | **13.6%** |

Stronger test — **stub out 100%** of `scan_for_replacements` per-occurrence `re.sub`: dense legal
(3060c) `24348 → 22463 µs` = **7.7% saved**; short prose (87c) = **−4.3%** (net-negative noise). And
the classifier *cannot even capture that 7.7%*: it still runs (1) one O(text) rebuild pass and (2) the
unremovable Aho-Corasick discovery scan — `abbreviation_replacer.py:96` `search`, `5542 µs/call cum`
≈ **36%** of the abbr-string phase on legal — which the classifier keeps verbatim (§4.1: "using the
same `_AbbreviationData`"). On large inputs that AC scan is itself a **net loss** vs a plain `in`-loop
(`abbr_scan_compare.py`: ratio 0.75-0.88 at 4k/40k).

**Where the time actually goes** (no-abbr 283c prose): `split_into_segments` 26.5%,
`replace_abbreviations` 26.1% (of which the classifier-targetable AC scan is only **7.1%**),
`_mark_list_item_boundaries` 24.0%. On legal text `apply_rules` is `372 µs/call tottime` / `2395 cum`,
83 calls/call, driven by `split_into_segments` (40×) and `post_process_segments` (12×) — i.e.
**per-segment boundary rules and the list-item phase each rival or exceed the entire
abbreviation-protection cost, run unconditionally, and the classifier touches none of them.**

**Verdict on the perf case:** it does **not** justify the rewrite. The library is already 0.74× pysbd
on medium and 0.25× on large (faster than pysbd) — there is no competitive-perf pressure. The honest
driver is **maintainability + correctness**, exactly as §10 says — so lead with that, state the
~10-13% ceiling quantitatively, and if a perf project is wanted, target the always-on
`split_into_segments` / list-item-boundary phases (lower risk, larger common-case win) first.

---

## 4. Correctness hazards & preservation-spec gaps a reimplementer MUST handle

**Fatal-if-ignored (would ship wrong output):**

- **Russian sentence-final set** — `russian.py:104-117` `SENTENCE_FINAL_ABBREVIATIONS` (12 members);
  `:171-177` *keeps* the period as a boundary before a Cyrillic capital for these (verified:
  `рус. Большой` splits). Absent from §5; a classifier following only the spec would **protect**
  `рус./нем./фр.` and lose those boundaries. Add as a first-class data table + `_is_embedded_occurrence`
  (`:135-142`) as a bounded-lookbehind callback.
- **dutch `CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`** (§5.3) — dutch does **not** set it. Enabling it for
  dutch flips the entire dispatch path (boundary-vs-protect before a capital). Remove dutch from the list.
- **en_es_zh follower class** — `[^\W\d_]` (any Unicode letter incl. uppercase/non-ASCII É, ñ),
  `en_es_zh.py:91`, where base/zh/ja use `[a-z]` (`abbreviation_replacer.py:574`, `chinese.py:26`,
  `japanese.py:55`). Reusing "base suffix" for en_es_zh fails to protect abbrs before non-ASCII letters.

**Fixable (real coupling the classifier must re-encode, single-pass-achievable):**

- **Order-dependence is re-encoded, not removed** — followers read mutated text (`mpa_replace`
  `:497-554` reads `self.text` post-sentinel; `_normalize_follower_token` `:464` doesn't strip it).
  Classifier must rebuild follower class + initialism chains from **original** periods
  (`_initials_chain_start` `:268-291` walks `X∯X∯X`); oracle/comparison must use original-context positions.
- **Interior-period protection is split across 3 passes**, one (`WithMultiplePeriodsAndEmailRule`,
  `standard.py:332` via `processor.py:477-484`) running **after** the replacer. `e.g.` → `e.g∯` (interior
  `.` still literal) → later `e∮g∯`. Classifier must subsume this or leave exactly what the email-rule catches.
- **Bulgarian intra-method order-dependence** — `bulgarian.py:99-113`: sub#1 protects trailing period,
  sub#2 keyed on that sentinel converts interior periods (verified: forward order protects both, reversed
  leaves interior `.`). `AbbrPolicy` must classify the **whole span at once** (span-returning).
- **Per-branch override (not whole-method)** — Slovak/Bulgarian/Russian override **only** the regular
  branch (`replace_period_of_abbr`); their prepositive/number-abbr abbrs flow through base
  `_replace_with_escape`/`_replace_number_abbr` (Slovak `PREPOSITIVE`/`NUMBER` non-empty, `slovak.py:247-248`).
  `AbbrPolicy` must let a language override one branch and inherit the other two — a staged pipeline
  descriptor (pre/classify/post), not three flat methods (kazakh adds rules before+after `super().replace()`,
  `kazakh.py:327-368`; deutsch reorders `replace()`, `:207-234`).
- **Automaton `<abbr>.` prefilter** (`:190`) + occurrence-dedup (`:609`) + period-less skip (`:601`) is
  the **reachability gate** that makes the unescaped/wildcard override regexes (bulgarian/german/arabic)
  safe — they only run when a literal `<abbr>.` exists. The classifier's candidate enumeration must
  reproduce "only periods completing a known `<abbr>.` at a word boundary," not "every period whose
  prev_token is in the set," or those languages diverge on adversarial inputs.
- **Kazakh's 3 passes** (`kazakh.py:331-368`): upstream Cyrillic single-letter rules; trailing-dot
  iteration with bespoke `_LOWERCASE_CONTINUATION_CHARS='a-zа-яёәғқңөұүһі'`; `protect_..._before_parenthesis`
  running **after** `super()`. A spec following only §5.2's one-line kazakh row omits all three.

**Moot now that BC is not required (DELETE rather than reproduce):**

- **German/Bulgarian unescaped `am`** (`deutsch.py:232-234` interpolates raw `am` into `(?<={am})\.`,
  no `re.escape`) — works only by accident of the list. Under correctness-first, **escape everything**.
- **`&ᓷ&&ᓷ&` placeholder injection** (`abbreviation_replacer.py:244,628`) — in-band token injection the
  RFC itself calls "the clearest symptom." Replace with a clean PROTECT-at-index decision.
- **Byte-identity of pathological adjacency cases** (§6) — drop entirely; adjudicate diffs on linguistic
  correctness against Golden Rules.

---

## 5. Sharpened recommendation (re-deciding §10 under the user's constraints)

**ADOPT-WITH-CHANGES — reframed as a correctness+maintainability refactor, English-first, explicitly
NOT a perf project.**

The RFC's default is "(a) leave it, unless speed or maintenance burden becomes a priority." Under the
user's actual constraints this **partially flips**, and the mechanism matters:

1. **Removing byte-identity is what unlocks (b)** — but by *collapsing risk*, not revealing reward.
   The RFC's "very high risk" rating is ~90% the byte-identity differential-oracle fight plus
   bug-for-bug reproduction of cruft (§5.4: unescaped-`am`, placeholder, order-dependent tie-breaks).
   Delete byte-identity and those costs evaporate; the classifier can *fix* the quirks instead of
   re-deriving them, shrinking scope.
2. **The default does NOT flip on perf grounds.** The measured ceiling (7.7% removable on the densest
   legal input, ~0 on prose, <7.7% realized) is too small to justify the work as a speed play. Anyone
   pitching this for speed should be redirected to `split_into_segments` / list-item boundaries.
3. **The real, now-stronger carry is maintainability + correctness.** Override sprawl is **under-counted**
   by the RFC ("six divergent re-implementations" → actually **9 modules / ~13 method overrides / 14
   `AbbreviationReplacer` subclasses"). Order-dependence is a *documented* bug class
   (`abbreviation_replacer.py:605-608` comment describes a real "case heuristic read from the wrong
   position" bug). Collapsing 9 overrides into one classifier + per-language policy hooks, and making
   each decision unit-testable in isolation, is the durable win — and the user's "correctness" mandate
   is precisely what funds it.

**Two non-negotiable changes to the plan (§7/§8):**

- **Demote the differential oracle (§8.1) from PRIMARY gate to a DEBUGGING aid.** A position-level
  legacy-vs-new equality oracle **is byte-identity in disguise** — it re-imports the exact constraint
  the user removed and hard-codes today's occasionally-buggy behavior as the spec. **Promote the 785
  Golden Rules + a NEW curated correctness corpus** (hand-labeled boundary decisions, including cases
  the legacy engine gets wrong) to the primary gate. Use the oracle only to *locate* `new != old` and
  adjudicate each diff as correct/incorrect — never to require equality.
- **Set the English-prototype acceptance to clarity/correctness, not the speed delta.** `english.py`
  and `en_legal.py` override **zero** scan methods, so the base classifier covers en/en_legal directly
  — highest value, lowest risk. Acceptance = (1) passes all English Golden Rules (reviewed
  correctness-improving diffs allowed), (2) demonstrably simpler (LOC, no order-dependence),
  (3) regresses no benchmark beyond noise. **Do not require a speed improvement.** If the prototype is
  not clearly cleaner, abandon (b) and stay at (a).

**Single most important next step:** Build the **throwaway English-only prototype** (RFC §10's
instinct is right and cheap), gated on the English Golden Rules + a curated correctness corpus, with
the explicit deliverable being *order-independent, unit-testable decision logic that fixes the
documented quirks* — not a speedup. Use it to decide go/no-go on the full 24-language effort.

---

## 6. Corrections the RFC text needs (from confirmed errors)

1. **§1/§2 sub-counts.** Replace `~240 re.sub/call` (normal) and `~1,800` (legal) with measured
   figures: **~66-80 total `re.Pattern.sub`/call** on the cited short/medium inputs, **~7 abbr-protection
   subs/call**. State that `~240` is **pysbd's** number. `~1,800` requires multi-KB text — cite the exact
   corpus and check it into `benchmarks/` or retract.
2. **§2 phase shares.** `~19%/~28%` are sample-dependent and ambiguous. The project's own short sample
   shows `replace_abbreviations` at **38.8%** (`phase_profile.py --size short`); dense legal measures
   **~56-61%**, not 28%. Pin each % to a named profiler row (`search_in_string` vs whole
   `replace_abbreviations`) and a committed corpus.
3. **§2 cost model.** Soften "each scans the entire text" → "the line" (per-line via `splitlines(True)`;
   German is the whole-text exception); add that occurrences are **deduped** (`dict.fromkeys`, `:609`),
   so cost is O(distinct (abbr, follower-char) variants × line-length), sub-linear in occurrences.
4. **§5.2 header.** "All emit `∯`; boundary prefix is `(?<=[{boundary}]{escaped})`" applies **only to
   base-class languages.** Note that russian (capture-group), slovak (literal `str.replace`), and
   bulgarian/german (unescaped) each replace the prefix entirely; the `??` row emits `&ᓷ&&ᓷ&`, not `∯`.
5. **§5.3 dutch.** Remove dutch from `CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE` (only 5 languages set it:
   english/en_legal/danish/greek/en_es_zh). Write the rank flag as `UPPERCASE_INITIALISM_SPLIT_MIN_RANK
   (dutch=2)` — dutch does **not** override `TWO_LETTER_INITIALISM_SPLIT_MIN_RANK`. Audit the trailing
   "…" — it implies more languages than actually set the flag.
6. **§10.** "the AC scan and always-on rule passes dominate normal prose" — the AC-scan half is **false**
   (7% on no-abbr prose). Correct to: the always-on per-segment `apply_rules` pipeline
   (`split_into_segments` / `post_process_segments`) and the list-item-boundary phase dominate
   normal-prose latency, and the classifier leaves them untouched.
7. **§11.** Cite the script/commit producing "3-5× alternation" and "~6% `str.translate`", or mark them
   as recollection — neither is reproducible in the repo.
8. **§4.3.** Change "order-dependence disappears" → "order-dependence is re-encoded as
   classify-from-original-text"; followers/initialism-chains are currently read from mutated text and
   must be rebuilt from original periods.
9. **"six divergent re-implementations"** → **9 modules / ~13 method overrides / 14 subclasses**.
