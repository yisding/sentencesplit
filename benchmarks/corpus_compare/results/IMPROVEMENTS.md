# sentencesplit improvement pass — from comparison verdicts

## 1. Summary

- **Branch:** `improve/sbd-from-comparison` (not pushed, not merged)
- **Fix clusters applied:** 11 + 1 follow-up regression fix
- **Clusters skipped as annotation artifacts:** 26
- **Headline objective delta (sentencesplit, before → after):**
  - Exact match: **74.4 → 76.7** (+2.3)
  - Boundary F1: **93.7 → 94.2** (+0.5)
- sentencesplit now leads every other tool on **both** metrics by a clear margin (next best: pysbd 73.3 EM / 93.5 F1).

> **Update (regression resolved):** the boundary-F1 dip originally reported in this pass was a
> single Dutch regression from the period-before-comma fix. It has since been fixed
> (commit `75c7abb`) by excluding the Dutch `,,` opening quote from that rule. The numbers
> above reflect the corrected state; the original (regressed) figures were 75.3 EM / 93.5 F1.

## 2. Fixes applied

| Cluster | Category | Files changed | Test added | Cases fixed | Commit |
|---|---|---|---|---|---|
| trailing-zwsp | Whitespace / zero-width | `processor.py`, `segmenter.py` | `tests/regression/test_issues.py` | 5/5 | `605c11a` |
| abbr-period-before-comma | Abbreviation / punctuation | `processor.py` | `tests/regression/test_issues.py` | 1/1 | `0aba692` |
| greek-abbreviations | Language data (el) | `lang/greek.py` | `tests/regression/test_greek_abbreviations.py` | 2/2 | `94eba6e` |
| russian-abbreviations | Language data (ru) | `lang/russian.py` | `tests/regression/test_issues.py` | 3/3 | `62d7338` |
| multi-bang-terminator | Terminal punctuation | `processor.py` | `tests/regression/test_issues.py` | 2/2 | `86c5a22` |
| german-ordinal-before-noun | List-item / ordinals (de) | `lists_item_replacer.py` | `tests/regression/test_issues.py` | 1/1 | `cae6e6b` |
| chained-initials-before-capital | Abbreviation / initialisms | `abbreviation_replacer.py`, `tests/lang/test_english_challenging.py` | `tests/regression/test_issues.py` | 1/1 | `adb37a8` |
| ellipsis-glued-runon | Ellipsis | `lang/common/standard.py` | `tests/regression/test_issues.py` | 1/1 | `2d6b3da` |
| abbreviation-as-terminal | Abbreviation / terminal | `abbreviation_replacer.py` | `tests/regression/test_issues.py` | 1/2 | `7889d5a` |
| multi-sentence-quotation | Quotation handling | `processor.py` | `tests/regression/test_issues.py` | 1/3 | `28aa88d` |
| **nl-comma-quote-gate** (follow-up) | Regression fix (nl) | `processor.py` | `tests/regression/test_issues.py` | nl recovered | `75c7abb` |

What each fix did:

- **trailing-zwsp:** `str.strip()` does not remove U+200B, so a lone Wikipedia reference marker survived as a phantom final sentence and a mid-text zero-width char was folded onto the next sentence. Added a `_strip_zero_width_chars()` final pass in `split_into_segments()` and skipped zero-width chars in `_match_spans()` so trailing zero-width is absorbed into the preceding span; char-span output stays an exact slice.
- **abbr-period-before-comma:** The trailing period of an unlisted multi-period abbreviation (`N.E.Br.`) fired as a boundary even when the next non-space char is a comma. Added `_PERIOD_BEFORE_COMMA_RE` to rewrite such periods to the protected placeholder before boundary detection (restored to `.` later, so output text is unchanged).
- **greek-abbreviations:** Greek inherited the English abbreviation list and the shared multi-period regex is ASCII-only. Added a Greek `Abbreviation` class that *extends* the Standard list with `μ.χ`, `π.χ`, `ε.ε`, `κ.λπ`, etc., and overrode `MULTI_PERIOD_ABBREVIATION_REGEX` with a Unicode-letter class scoped to Greek.
- **russian-abbreviations:** Added the missing abbreviations (`др`, `ср`, `англ`, `нем`, `фр`, `чуваш`, `рус`, `лат`, `греч`, `итал`, `исп`, `польск`); Russian already suppresses the boundary unconditionally, so the list addition alone fixed all three cases.
- **multi-bang-terminator:** The `{3,}` continuous-punctuation protection rewrote `!!!`/`???` to placeholders, so a terminal cluster before a capital never split. Added a second resplit pass on the Latin path (`_MULTI_TERMINATOR_RESPLIT_RE`) gated by `latin_uppercase_resplit`; clusters before a lowercase follower or at end-of-text stay protected.
- **german-ordinal-before-noun:** Ascending prose ordinals (`des 19. und … 20. Jahrhunderts`) were promoted to a numbered list with injected line breaks. Generalized the line-break guard to suppress list line breaks for any numbered marker followed by a lowercase Latin/German word, while keeping marker periods protected.
- **chained-initials-before-capital:** A 3+ part single-letter initialism (`F.J.G.`) re-added a boundary before a capitalized following word. Added `_is_initials_name()` to treat `Initials + Surname` as a personal name and suppress the boundary, unless the initialism is article-preceded (`the S.A.T.`) or followed by a known sentence starter (`H.B.S. She`).
- **ellipsis-glued-runon:** A four-dot run glued to a lowercase continuation (`slides....they`) left a bare period that split. Added `GluedLowercaseRunOnRule` to protect dots beyond the trailing three only when glued to a lowercase follower; capital-follower and spaced-ellipsis cases still split.
- **abbreviation-as-terminal:** Fixed the all-caps imprint case (`…AND CO. TOOKS COURT, LONDON.`) via a conservative post-pass that keeps a known abbreviation's period non-terminal only when flanked by all-caps multi-letter tokens. The `Washington, D.C. Justices` case was deliberately left unfixed — no reliable lexical signal distinguishes it from the guardrail `D.C. Circuit`.
- **multi-sentence-quotation:** Added `_resplit_multi_sentence_quote()` (Latin path only) to split interior period boundaries inside a self-contained, single-pair multi-sentence quotation (3+ substantial sentences, no interior quotes). Fixed the one "major" target; two cases were left unfixed because they are structurally indistinguishable from existing gold-KEEP cases.

## 3. Skipped / deferred

- **26 clusters skipped as annotation artifacts.** These were dominated by UD colon-boundary annotation conventions (treebanks marking a colon as a sentence boundary, or vice versa) where the "expected" segmentation reflects corpus annotation choices rather than a genuine SBD defect. These were intentionally not chased to avoid overfitting the library to one corpus's conventions.
- **Partially-fixed clusters (cases deliberately left open):**
  - `abbreviation-as-terminal` — `Washington, D.C. Justices…`: splitting here would regress the `D.C. Circuit` guardrail; treated as opt-in/research, not a default.
  - `multi-sentence-quotation` — `case_0106`, `case_0110`: structurally identical to existing gold-KEEP quotation cases in `tests/lang/test_english_clean.py`; forcing a split regresses the existing suite, so no local linguistic rule can separate them.

## 4. Verification

After-scoreboard (n = 348 unless noted):

| Tool | Exact match | Boundary F1 | n |
|---|---|---|---|
| **sentencesplit** | **76.7** | **94.2** | 348 |
| pysbd | 73.3 | 93.5 | 348 |
| pragmatic_segmenter | 73.0 | 93.5 | 348 |
| punkt | 70.4 | 90.4 | 318 |
| syntok | 64.3 | 90.7 | 258 |

Per-language movement (sentencesplit, before → after, EM / F1):

- **de** 63.3 → 70.0 (+6.7) / 92.1 → 94.0 (+1.9) — prose-ordinal + numbered-marker-before-lowercase guard
- **ru** 70.0 → 76.7 (+6.7) / 95.3 → 96.0 (+0.7) — Russian abbreviations
- **el** 63.3 → 66.7 (+3.4) / 88.6 → 89.9 (+1.3) — Greek multi-period abbreviations
- **es** 73.3 → 76.7 (+3.4) / 95.8 → 96.1 (+0.3) — period-before-comma + trailing zero-width drop
- **en** 82.4 → 83.3 (+0.9) / 95.7 → 96.1 (+0.4) — multi-char terminator, chained initials, glued four-dot run-on, multi-sentence quote
- **fr / it / zh** — flat (no change)
- **nl** 63.3 → **66.7** (+3.4) / 91.4 → **91.8** (+0.4) — recovered after the comma-quote gate (commit `75c7abb`); was −13.3 / −7.0 before that follow-up fix

**Regression (adversarial finding — now RESOLVED):** Dutch initially dropped hard and was the sole reason overall boundary F1 fell. Bisected to `_PERIOD_BEFORE_COMMA_RE` (commit `0aba692`): Dutch opens quoted speech with `,,` (two commas, low double opening quote). A legitimate sentence-final period directly before such a quote (`…optimisme. ,,Juist als…`) matched `\.(?=\s*,)`, so the terminal period was rewritten to the placeholder and two sentences merged. The Spanish-targeted fix runs unconditionally in the shared `Processor`, so it leaked into every language. **Fix (commit `75c7abb`):** tightened the lookahead to `\.(?=\s*,(?!,))` so a *doubled* comma (the Dutch opening quote) no longer protects the period; a single comma (`N.E.Br.,`) still does. Dutch recovered to **66.7 EM / 91.8 F1** (above main's 63.3 baseline) with no other language affected.

**Verdict:** `regressions_detected = FALSE` after the follow-up. Overall moved from 74.4/93.7 baseline to **76.7 / 94.2** — net positive on both metrics.

**Test suite:** GREEN. `uv run pytest -q --ignore=tests/test_spacy_component.py` → **993 passed, 8 xfailed**. English Golden Rules unchanged at 47/48 before and after each fix. `tests/test_spacy_component.py` cannot be collected on this aarch64 box — importing torch (via thinc/spaCy) aborts with "Fatal Python error: Illegal instruction"; this is a pre-existing environment/hardware fault reproduced identically on the clean baseline and unrelated to these changes (same root cause as the unavailable blingfire / spacy_sentencizer / stanza segmenters). `ruff format --check` and `ruff check` pass repo-wide.

## 5. Next steps

1. ~~**Fix the Dutch regression.**~~ **DONE** (commit `75c7abb`): tightened `_PERIOD_BEFORE_COMMA_RE` to `\.(?=\s*,(?!,))`, recovering Dutch and flipping overall boundary F1 net-positive (93.7 → 94.2).
2. **Revisit the deferred quotation cases** (`case_0106`, `case_0110`) and the `D.C.`-as-terminal case only if a corpus-independent lexical signal can be found; otherwise leave as opt-in. The multi-sentence-quotation rule remains the highest-risk area for over-/under-splitting.
3. **Review and merge** branch `improve/sbd-from-comparison` — the regression verdict is now clear (suite green, both metrics net-positive). A heavier follow-up would be to add the multilingual comparison-corpus check to the per-fix guardrail so a future single-language regression is caught at fix time, not just in the verify phase.

---

## Executive summary

An improvement pass on branch `improve/sbd-from-comparison` (11 fix clusters + 1 follow-up
regression fix) raised sentencesplit's exact-match score from **74.4 to 76.7 (+2.3)** and
boundary F1 from **93.7 to 94.2 (+0.5)** across the 348-unit comparison corpus, keeping it
ahead of every other segmenter on both metrics (next best: pysbd 73.3 / 93.5). The clusters
applied: zero-width strip, period-before-comma, Greek/Russian abbreviations, multi-bang
terminators, German ordinals, chained initials, glued ellipsis, all-caps imprint, and a
multi-sentence-quote resplit; 26 clusters were skipped as UD colon-boundary annotation
artifacts. Gains landed across de (+6.7 EM), ru (+6.7), nl (+3.4), el (+3.4), es (+3.4), and
en (+0.9). The verify phase initially caught a Dutch regression (the Spanish period-before-comma
rule leaked into Dutch, which uses `,,` to open quotes); it was then fixed (commit `75c7abb`)
by excluding the doubled comma, recovering Dutch and flipping boundary F1 net-positive. The
full library suite is green (993 passed, 8 xfailed; the lone spaCy test is an unrelated
pre-existing ARM/torch crash). Branch is ready for review — not merged, not pushed.
