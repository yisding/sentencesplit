# sentencesplit Level-Up Roadmap — "The Trusted Sentence Layer"

> **Numbers note.** All in-repo metrics below are read from
> `benchmarks/corpus_compare/results/scoreboard.baseline.json` and `verdicts.json`
> (verified, not from the brief — the earlier draft mis-cited the headline as
> 76.7/94.2; the baseline overall is **74.4 EM / 93.7 F1**). External market figures
> (pysbd downloads, SaT F1, chonkie throughput, framework-PR states) carry a
> **"approximate — verify before publishing"** tag; they were current as of early
> 2025 and have a Jan-2026 knowledge cutoff. Per-UD-corpus numbers are **n=30** and
> are reported with that caveat throughout.

## 1. Executive summary

sentencesplit has already won the hard, defensible part: on its own 348-unit cross-library
harness it is the strongest deterministic, zero-dependency sentence splitter in the Python
ecosystem on punctuated text — **74.4% exact-match / 93.7 boundary-F1**, narrowly ahead of
pysbd (73.3 / 93.5) and the Ruby pragmatic_segmenter (73.0 / 93.5), with statistical Punkt
behind on the languages it covers (70.4 / 90.4, n=318) and syntok last (64.3 / 90.7, n=258).
It is the only strong CJK rule engine (zh **96.7% EM, +10 over pysbd**), ties the rule pack on
English Golden Rules (97.9% EM where Punkt collapses to 56.2%), and ships three primitives its
ancestors lack: non-destructive char-spans, a streaming lookahead API, and a `split_mode`
oversplit/undersplit bias.

**Two honesty caveats up front, because the trust thesis depends on them.** (1) The overall
EM/F1 ranking is **not a like-for-like comparison**: sentencesplit/pysbd/pragmatic are scored
on n=348, Punkt on n=318, syntok on n=258 (each only on the languages it supports), so the
single headline number conflates different unit sets. (2) The adjudicated win lead is a
**statistical tie with the Ruby reference**: 73 wins for sentencesplit, 72 for
pragmatic_segmenter, 68 for pysbd — a one-case margin — and sentencesplit's own self-assessment
on the adjudicated set is 73 correct / 47 incorrect (~61%). "Class leadership on clean
punctuated text" is true and defensible; "won decisively" is not. We lead, but we must publish
the lead with its error bars or the leaderboard undercuts the very trust it is meant to build.

**The thesis:** the remaining gap to mass adoption is **not raw accuracy — it is trust,
friction, and packaging.** We are positioned as a *sentence splitter* while demand has migrated
toward *streaming output and the span-faithful segmentation that feeds RAG pipelines*, served
today by an upstream (pysbd, ~4.1M downloads/month —
*approximate, verify*) that has been frozen since Feb 2021 and that frameworks still name in
open, unmerged integration requests.

**The single biggest bet:** become *the maintained, provably-best, span-faithful, streaming-ready
successor to pysbd* by (a) making the leadership claim externally verifiable and regression-proof
via a CI-gated public leaderboard that reports its own error bars and sample sizes, and
(b) promoting the differentiated functional primitive **no rule competitor has** — a first-class
streaming/lookahead segmenter for live LLM and voice output — to a headline feature, all while the
zero-dependency pure-Python core stays the untouched default install. *(Token-budget chunk assembly
— `chunk(max_tokens=…)` — was considered and explicitly cut; sentence/span output stays our
chunking primitive. See §3.)*

## 2. Where we stand

**Strengths (verified against the repo):**
- **Reproducible class leadership on punctuated text** — 74.4 / 93.7 overall (caveat: mixed
  sample sizes, §1). Ties the rule pack on English Golden Rules (97.9% EM vs Punkt 56.2%),
  best-in-field CJK (zh 96.7% EM, +10 over pysbd, n=30). Confirmed in `gold_scores`.
- **A moat the competition physically cannot enter** — zero runtime dependencies
  (`pyproject.toml: dependencies = []`, verified), pure stdlib, instant cold-start,
  Pyodide/WASM-shippable. blingfire/spaCy/stanza native wheels *crash on the aarch64 dev box*
  (scoreboard `available:false`, `OSError ... libblingfiretokdll.so`, signal-4 on spaCy/stanza).
  Load-bearing and independently observed.
- **Differentiated, already-built features** — streaming lookahead
  (`segment_with_lookahead` / `should_wait_for_more`), non-destructive char-spans,
  `split_mode` bias. No rule competitor offers streaming; syntok/pragmatic *alter text units*
  (harness flags `altered_text_units`), making them unsafe for citation.
- **Already typed** — ships `py.typed` plus inline annotations (only the `Typing :: Typed`
  trove classifier is missing).
- **Engineering hygiene** — ~990 tests across 24 languages + combined/legal profiles,
  regression-test-before-fix discipline, CI on Python 3.11–3.14.

**Gaps (honest):**
- **Evidence is invisible and unverifiable** — the scoreboard lives in a `results/` folder no
  user sees; README claims are qualitative; the cross-library harness is **confirmed absent
  from CI**. A global rule change already silently regressed Dutch during the
  period-before-comma fix, caught only by manual review.
- **DX friction** — no `list_languages()`, no `extra_abbreviations=` (custom abbreviations
  require subclassing — the #1 recurring ask on pysbd's tracker), missing `Typing :: Typed`,
  bare keywords (`["natural-language-processing","nlp"]`, verified).
- **Coverage is European/CJK-skewed with a thin tail** — 8 languages inherit Standard
  unchanged; amharic/armenian/burmese/urdu/marathi/persian carry only a boundary regex +
  punctuation list with **no abbreviation list at all** (verified: ~11-line stubs). Portuguese
  (~250M speakers), Korean, Vietnamese, Thai, Turkish, Indonesian/Malay, Hebrew, and the
  Nordics are entirely absent — and several of those (Hebrew/Arabic-script RTL, Thai
  scriptio-continua) are *distinct failure modes* the span / round-trip contract must account
  for, not just more abbreviation lists.
- **Statistical-abbreviation deficit on noisy mid-resource European prose** — Punkt's learned
  model beats us on UD treebank EM. The widest gaps (n=30, wide CI): **Dutch 63.3 vs Punkt
  90.0** — and note we also **trail pysbd here (63.3 vs 66.7)**; German 63.3 vs 73.3; Italian
  50.0 vs 56.7; Russian 70.0 vs 80.0; French 86.7 vs 90.0. Directionally real, magnitude noisy.
- **Dirty-input / encoding fragility** — trailing zero-width-space fragments were flagged in
  prior benchmarking; there is no systematic hardening against ZWSP/NBSP/BOM/combining-mark/RTL-
  marker artifacts, which is the most common real-world dirty-input footgun and directly
  threatens any byte-round-trip span guarantee.
- **Speed ceiling** — pure Python caps the high-throughput ingestion segment. (The often-cited
  "~4–6 MB/s" figure is *not* substantiated by a quoted run of `bigtext_speed_benchmark.py` in
  the repo — treat it as approximate until that benchmark output is captured.)

## 3. Strategy

**North star:** *Be the sentence layer that LLM/RAG/streaming pipelines reach for first and never
second-guess — sentence-accurate, span-faithful, streaming-ready, and dependency-free by default —
and prove it with a public leaderboard nobody can dispute because it reports its own error bars.*

This builds a trust-and-evaluation backbone (the CI-gated regression gate + a public leaderboard)
and grafts onto it our two differentiated, *already-built* assets — non-destructive char-spans and
the streaming/lookahead API — plus targeted accuracy fixes on genuine bugs (not annotation
artifacts). The streaming API is our most uniquely uncopyable asset and is "built, tested, and
under-advertised," so it is weighted toward promotion and thin wrapping of existing primitives. We
compete on **correctness and span-fidelity, not throughput** — chonkie ships at 100+ GB/s
(*approximate, verify*) and we will neither win on speed nor try to.

**What we explicitly will NOT do:**
- **No neural/ML backend in core, and no torch dependency anywhere that can crash the default.**
  The aarch64 failure is a **SIGSEGV — a signal, not a catchable `ImportError`/`OSError`** — so
  a "catch and fall back to rules" contract cannot honor a never-crash promise. We document a
  punctuation-restoration pre-stage for ASR/lowercased text and scope the unpunctuated frontier
  out of band. SaT/wtpsplit owns that lane; `pip install wtpsplit` is the answer, not a wrapper.
- **No Rust/PyO3 hot-path this cycle.** XL effort, dual-maintenance, in direct tension with the
  Pyodide/WASM story we are selling. Revisit only if profiling proves a sustained ingestion-scale
  demand we are losing on throughput alone *and* the pure-Python path stays default with
  byte-identical output CI-enforced.
- **No structure-aware segmentation threaded into `split_into_segments`.** That function already
  carries a C901 exemption and is the highest-regression-risk surface. Any structure-awareness is
  a *pre-pass* gated behind `doc_type`, regression-tested first — firmly "Later," not now.
- **No chasing UD colon-as-boundary / article-number-as-sentence-start "losses"** — confirmed
  annotation artifacts (REPORT.md lines 312–313), not bugs. This explicitly bounds the Italian
  work below.
- **No *token-budget* chunking (`chunk(max_tokens=…)`, a token-counter abstraction, overlap
  windows).** *(Dropped by decision.)* Sentence/span segmentation *is* a form of chunking — chunking
  at the sentence granularity is exactly what we do, and we lean into it — but we will not get into
  the **token-chunking business**: counting tokens, packing sentences to a token budget, or sliding
  overlap windows. `segment_spans()` hands consumers exact offsets; they group those to their own
  token budget with their own tokenizer. This removes the token-counter fidelity footgun entirely
  and keeps the surface small. chonkie/LangChain/LlamaIndex own the token-chunking layer; we feed it
  clean sentence chunks.
- **No first-party LangChain / LlamaIndex adapters.** *(Dropped by decision.)* We will not own and
  CI-maintain framework-specific glue against fast-moving external APIs. The shipped spaCy
  entry-point stays; beyond it we rely on the stable public API (`segment`, `segment_spans`,
  `StreamSegmenter`) + a "Coming from pysbd" path so framework authors and users can wire it in
  themselves. Distribution becomes organic pull, not adapter maintenance.

## 4. Roadmap

> **Sequencing reality check (bus factor).** This is essentially a one-maintainer program. The
> horizons below are sized for that: **Now is deliberately short** (the two behavior-changing
> items are explicitly co-sequenced), and Next/Later are a backlog ordered by impact-per-effort,
> *not* a promise that all of Next lands inside 9 months. Treat the dates as "soonest plausible
> start," not capacity guarantees.

### Now (0–4 months) — make the lead legible, regression-proof, and frictionless

**N1. DX quick wins (metadata + discovery) — S, high impact.**
Add `Segmenter.list_languages()` (trivial — `LANGUAGE_CODES` registry already exists). Add
`Typing :: Typed` and a `Development Status` trove classifier (we already ship `py.typed` — the
claim is just missing metadata). Expand keywords to
`sentence-boundary-detection, sentence-tokenizer, pysbd, rag, chunking, segmentation,
streaming`. Add a "Migrating from pysbd" README section citing the shared API + Golden Rules
lineage. *Why:* lowest-build, highest-conversion move to capture the abandoned-pysbd pocket.
*Note:* this item is intentionally **metadata + discovery only**; the behavior-changing
`extra_abbreviations` work is split out into N1b because it mutates segmentation output.

**N1b. `extra_abbreviations=` constructor argument — M, high impact. MUST land after N2.**
Make `extra_abbreviations=[...]` a first-class constructor arg instead of requiring a
`Common`/`Standard` subclass, feeding the existing Aho-Corasick automaton without breaking the
precompiled cache. *Why:* custom abbreviations without subclassing is the #1 recurring ask on
pysbd's tracker, and it lets users close their own domain gaps (reducing pressure on N9/N10).
*Sequencing:* this is the **first behavior-changing PR**; it must land *after* the N2 regression
gate exists, and its cache-invalidation path gets dedicated regression tests. Sized M, not S —
the cache-invalidation correctness is the real work.

**N2. CI-gated regression gate (hermetic, self-vs-gold only) — M, transformative. LANDS FIRST.**
Split the harness into two layers. **(a)** A *pure-Python, hermetic* gate that scores **only
sentencesplit against committed gold** on a checked-in corpus subset, diffs against
`scoreboard.baseline.json` (already present), and **fails the PR on per-language EM/F1 drops
beyond a per-language tolerance.** No Ruby, no NLTK downloads, no network, no native wheels —
runs on the aarch64 box. **(b)** The full cross-library comparison stays a *manual/scheduled*
job (needs the Ruby gem + NLTK + network corpora; inherently flaky/licensed). *Why:* directly
fixes the one realized process failure (silent Dutch regression) and is the prerequisite for
every accuracy initiative below.
**Governance — the net-positive-but-locally-negative trade is a first-class feature of N2, not
a footnote.** Raising overall EM across 24 languages will, at n=30 per corpus, almost certainly
cost EM in *some* language on *some* PR. The gate therefore ships from day one with: per-language
tolerances, an explicit `# baseline-update` flow that requires a reviewed diff and a one-line
rationale, and a documented rule that a trade which is net-positive on the union of corpora may
update the baseline. **This governance must be designed and merged before N6 publishes the gate
externally** — otherwise the public gate blocks the accuracy work the roadmap prioritizes.

**N5. Span-faithful citation contract + property-based round-trip invariant — S–M, medium impact.**
Make non-destructive spans a documented, CI-enforced guarantee across `segment_spans()` and
streaming: every emitted unit maps to an exact `[start,end)` slice, and reassembling spans
reproduces the source byte-for-byte. This is the citation-fidelity guarantee downstream consumers
(legal/RAG span alignment) depend on, and — with token-budget chunking out of scope — it is the
primary way we serve token-chunkers: hand them exact offsets they can group themselves. Resolve the
redundant `char_span` flag vs. `segment_spans()` path (one obvious way). **Add Hypothesis property
tests** (dev-only dependency — does not touch the zero-dep core) for the round-trip invariant; this
class of invariant is the textbook case for property-based testing and is more convincing than
example-based regression tests. **Cover dirty input explicitly:** ZWSP/NBSP/BOM/combining-mark/
RTL-marker fixtures, since these are exactly what breaks a byte-for-byte guarantee in the wild.

**N4. Promote streaming as a first-class `StreamSegmenter` — S–M, high impact.**
Wrap the existing, tested `segment_with_lookahead` / `should_wait_for_more` primitives in a
stateful `StreamSegmenter` that accepts token/text deltas, emits completed sentences once their
boundary is stable, and buffers the unstable tail. Add a latency-to-first-stable-sentence
benchmark and a streaming-to-TTS recipe; conservative buffering is the default. *Why:* near-pure
positioning upside — the primitive is already built. Voice agents (Pipecat/LiveKit) flush each
completed sentence to TTS for sub-second latency; the open LiveKit multilingual-SBD request names
pysbd, which offers nothing here (*verify the request is still open before leaning on it in
copy*). *Risk:* premature emit corrupts downstream TTS — validate probe coverage per language,
default conservative, test against probe suites.

### Next (3–12 months) — widen the lead and capture distribution (backlog, impact-ordered)

**N6. Publish the leaderboard with standard metrics — L+ (treat as two M sub-projects), high impact.**
Promote `benchmarks/corpus_compare` into a versioned, public artifact tied to each release tag
(README badge + generated page). **This is under-sized at a single L** — split it:
**(6a)** add char-level boundary-F1 (the WtP/SaT metric) — M; **(6b)** reimplement CoNLL-18 UD
"Sentences" F1 scoring in stdlib (the official `conll18_ud_eval` is the convention; we
reimplement rather than add a dependency, and budget for getting it subtly right) — M;
**(6c)** ship download scripts (never vendor) for Ersatz, GENIA, MultiLegalSBD. *Credibility
discipline (mandatory):* publish **sample sizes and the mixed-n caveat** alongside every overall
number (sentencesplit n=348 / Punkt n=318 / syntok n=258), and report per-UD-corpus deltas as
n=30 with explicit "small-sample" framing. The leaderboard's value is that it is honest; an
over-claimed leaderboard is worse than none. *Risk:* corpus licensing is mixed/non-commercial →
download scripts only, never vendored text.

**N7. Re-scoped: fix the *genuine* Italian sub-bugs only — S–M, medium impact.**
The Italian 50.0 EM floor is **largely shared annotation artifacts, not a sentencesplit defect**:
of 7 adjudicated `ud_it_isdt` cases, 4 are `none_correct` (2 list/article-numbering, 1 colon
"blob" — REPORT.md calls these corpus artifacts — and 1 quotation) and 3 are sentencesplit
*wins*; pysbd and pragmatic sit at the same 50.0 for the same reason. **The earlier draft's
"rule-logic defect, not a data gap" framing is wrong and is corrected here.** So: do **not** chase
the artifact cases, and **drop the "Italian ≥70%" target** — it is unreachable without gaming the
metric against artifacts. Scope N7 to the one genuine sub-bug — the dangling-open-quote
suppression — which is the **same root cause as N11** (interior boundaries suppressed inside an
unclosed quote pair). *Therefore N7 is folded into N11's quotation work* rather than tracked as a
separate Italian initiative; what remains "Italian-specific" is only the regression fixtures.

**N9. Add Portuguese; then close the Dutch/German abbreviation gap — L, high impact.**
Add Portuguese (pt) via the TDD recipe — highest-priority absent language (~250M speakers,
Romance-analogous to es/fr, a MultiLegalSBD benchmark language). Then mine UD divergences for the
specific abbreviations/patterns Punkt catches and we miss in **Dutch (63.3 — where we trail both
Punkt at 90.0 *and* pysbd at 66.7)** and German (63.3 vs 73.3); hand-curate with per-case
regression tests. Where the miss is a shared-rule issue, fix the rule (gated by N2). *Why:*
broadens coverage where it pays and lands us on another benchmark corpus; Dutch trailing *pysbd*
is the most embarrassing single number and the strongest evidence the loss is curatable.
*Risk:* diminishing returns on the last EM points at n=30 — measure per-language ROI after the
first pass and stop where curation cost exceeds gain.

**N10. Lean into the offline/air-gapped legal-RAG niche — M, high impact (newly added).**
The **legal corpus is the single largest source of cross-library disagreement** in the harness
(36 divergences in `divergences_all.json`, vs 24 for Golden Rules and 18 for Italian — verified).
We already ship an `en_legal` profile and char-span output. Position sentencesplit explicitly as
a **deterministic, auditable, offline/air-gapped legal segmentation primitive** where torch-based
tools are non-starters — the exact ethos-aligned wedge NUPunkt's April-2025 result validated
(pure-Python, zero-dep, domain-SOTA on legal text; precision compounds in RAG by reducing context
fragmentation — *approximate external figures, verify*). Concretely: triage the 36 legal
divergences into curatable sub-bugs vs. artifacts, harden `en_legal`, add a legal-specific recipe
(citation-faithful segmentation with exact spans, which downstream callers chunk to their own
token budget), and put it in the leaderboard (N6) so the niche claim is measured, not asserted.

### Later (12 months+) — depth, niche, and deferred bets (backlog)

**N11. Resolve multi-sentence / open-quote boundary suppression (1/3 → 3/3) — M, medium impact.**
Build a more discriminating signal for the open-quote resplit (interior terminal-punctuation
count, capitalization runs inside the quote, quote-pair span length) validated against the
gold-KEEP cases. **This subsumes the genuine Italian sub-bug from N7** (same root cause) and
extends to CJK quote continuations. *Honest caveat:* the prior improve pass closed only 1/3
because the others are "structurally indistinguishable from gold-KEEP" — genuinely hard, hence
"Later."

**N12. Deepen the thin tail + a new-language scaffold — L, medium impact.**
Curate real abbreviation lists for the ~11-line stubs (amharic/armenian/burmese/urdu/marathi/
persian — verified: boundary regex + punctuation only, *no abbreviation list*) **only where
native-speaker or corpus validation is available** — no coverage theater. Ship a
scaffold/generator (test file + lang module + registry entry) and a "good first language"
contributor path tied to the N2 gate, so the maintainer is not the bottleneck. When adding the
absent high-demand languages (Korean, Vietnamese, Thai, Turkish, Indonesian/Malay, Hebrew,
Nordics), **treat RTL (Hebrew/Arabic-script) and scriptio-continua (Thai) as distinct work**:
they break the span/round-trip (N5) assumptions and need their own fixtures
before shipping, not just an abbreviation list.

**N13. Optional structure-aware *pre-pass* for fenced code / lists (gated) — L, medium impact — only if markdown/code-aware demand emerges.**
A pre-segmentation pass that protects fenced/inline code and list markers from triggering
boundaries, behind `doc_type='markdown'`, **never on the default code path.** Deliberately
deprioritized: highest-regression-risk initiative (threads near the C901-exempt
`split_into_segments`). Regression-test before shipping.

**Deferred / not-now:** PyO3 accelerator (XL, ethos-tension with Pyodide); any ML backend (scoped
out per §3).

### Cross-cutting: stability & versioning contract (applies to N1b, N4)

We are adding two new public surfaces (`StreamSegmenter`, `extra_abbreviations=`) at **v0.0.x**,
with no stated commitment about when *output* may change —
and a CI gate that "fails on any EM drop" is in direct tension with shipping accuracy
improvements that by definition change segmentation output. **Resolve this before the public
leaderboard (N6) ships:** publish a short SemVer + stability policy stating (a) which surfaces are
stable vs. experimental, (b) that *segmentation output* may change in minor releases when net
accuracy improves (with the change noted in the changelog), and (c) a deprecation window for API
changes. The N2 governance flow (§N2) is the operational half of this contract; the policy doc is
the public half. Without it, "we never change your output" and "we keep improving accuracy" are
contradictory promises.

## 5. Accuracy & evaluation plan

- **Two-tier harness.** *Tier 1 (CI-gated, hermetic):* sentencesplit vs committed gold on a
  checked-in corpus subset, pure Python, no network/Ruby/native wheels — runs on aarch64, fails
  PRs on per-language regression beyond tolerance, diffed against `scoreboard.baseline.json`, with
  the net-positive-trade governance flow built in (§N2). *Tier 2 (manual/scheduled):* full
  cross-library comparison (pysbd, pragmatic_segmenter/Ruby, Punkt, syntok) over UD + Golden Rules
  + Wikipedia + Gutenberg + legal — kept off the PR path because of its flaky, licensed,
  native-dependent footprint.
- **Property-based invariants (Hypothesis, dev-only).** Span round-trip (byte-for-byte
  reassembly), including dirty-input fixtures (ZWSP/NBSP/BOM/combining marks/RTL markers).
- **Metrics:** keep exact-match; add **character-level boundary-F1** (WtP/SaT format) and
  **CoNLL-18 UD Sentences-F1** (reimplement `conll18_ud_eval` scoring in stdlib).
- **Corpora:** download scripts only (never vendor) for Ersatz, GENIA, MultiLegalSBD — mixed/
  non-commercial licenses make vendoring a legal liability. Reproducible by a third party from
  scripts alone.
- **Credibility discipline (mandatory, this is the whole point):** always publish sample sizes
  and the **mixed-n caveat** (n=348 / 318 / 258 across the field); report per-UD-corpus numbers as
  **n=30** with small-sample framing; report the adjudicated win count *with its one-case margin*;
  keep Golden Rules + gold-KEEP suites as hard CI gates so benchmark-tuning can't regress
  real-world text; treat documented UD annotation artifacts (colon-as-boundary,
  article-number-as-start) as **explicitly out of scope** and say so on the leaderboard.

## 6. Success metrics ("leveled up")

1. **Core integrity preserved** — `pip install sentencesplit` stays zero-dependency; a CI
   assertion confirms a bare `import sentencesplit` loads zero non-stdlib modules; cold-start
   within current bounds on Python 3.11–3.14; `uv_build` extras/entry-points verified across the
   matrix.
2. **Regression gate live & proven** — the Tier-1 hermetic harness gates every PR, with the
   net-positive-trade governance flow documented, and catches ≥1 would-be per-language regression
   before merge within two release cycles. The Dutch-incident class becomes structurally
   impossible to ship.
3. **Leaderboard published & comparable — *with error bars*** — versioned report tied to each
   release tag, char-level boundary-F1 + CoNLL-18 UD-F1, reproducible from download scripts, our
   numbers in the SaT/WtP format, **and every overall figure annotated with its sample size and
   the mixed-n caveat.** Honesty of the leaderboard is itself a success criterion.
4. **Accuracy up where it's genuine** — overall harness EM 74.4 → **≥77%** and boundary-F1
   93.7 → **≥94.5%** (modest, because the field is a near-tie and gains at n=30 are noisy), with
   the lead over pysbd *widening*; **Dutch 63.3 → ≥80%** (the standout fixable gap — and at
   minimum retake the lead over pysbd's 66.7); German 63.3 → ≥73% (match Punkt — the statistical
   ceiling here is 73.3, not 90.0; the German gap is real but smaller than Dutch's). **No Italian EM target** — its
   floor is largely annotation artifacts (see N7); success there is "fixed the open-quote sub-bug,
   did not chase artifacts."
5. **Span fidelity** — 100% span round-trip fidelity (every `segment_spans()` unit is an exact
   `[start,end)` slice; reassembly reproduces the source byte-for-byte) enforced by a
   property-based invariant test across clean + dirty input. This is what lets downstream RAG
   chunkers trust our offsets.
6. **Distribution (organic pull, not adapter-driven)** — sentencesplit referenced or recommended
   as a sentence/text splitter in ≥2 RAG/voice ecosystems (e.g. Haystack, Pipecat, chonkie,
   community write-ups), and users pointed from the pysbd-migration path. Driven by positioning +
   credible numbers, *not* by us shipping framework adapters (explicitly out of scope, see §3).
7. **DX friction eliminated** — `list_languages()`, `extra_abbreviations=`, and `Typing :: Typed`
   shipped; "how do I add abbreviations / what languages are supported" question classes trend
   toward zero.
8. **Adoption signal (attributable, not vanity)** — PyPI download growth is real but
   **un-attributable to a positioning change**, so we do *not* claim it as a causal metric.
   Instead measure proxies we can actually attribute: inbound issues/PRs referencing the
   pysbd-migration path, and GitHub stars/forks after the leaderboard ships. Track total PyPI
   downloads as context, not as a success claim.

## 7. Risks & open questions

- **The gate vs. the accuracy target (governance).** Raising overall EM at n=30 will cost EM
  somewhere on some PR; the "fail on any drop" gate would block the very work we prioritize.
  *Mitigation:* the net-positive-trade governance flow is part of N2's design and **must land
  before N6 publishes the gate externally** (see §N2, §4 cross-cutting). This is the single most
  important sequencing constraint in the plan.
- **Output stability vs. continuous improvement (versioning).** At v0.0.x with two new public
  surfaces, "we never change your output" and "we keep improving accuracy" are contradictory until
  we publish the stability/SemVer policy (§4 cross-cutting). Unresolved = a trust liability.
- **External numbers go stale.** pysbd downloads (~4.1M/mo), SaT F1 (~91.6 / 93.1 LoRA), chonkie
  throughput (100+ GB/s), NUPunkt's legal precision, and the framework-PR states are all
  **approximate, early-2025, Jan-2026 cutoff** — re-verify each before publishing anything that
  cites it. A trust-thesis roadmap that cites stale numbers undermines itself.
- **The "speed ceiling" figure is unsubstantiated in-repo.** The "~4–6 MB/s" claim is not backed
  by a quoted `bigtext_speed_benchmark.py` run. *Action:* capture and cite the actual benchmark
  output before using the number anywhere external; until then, caveat it.
- **Dirty-input / encoding artifacts threaten the span contract.** ZWSP/NBSP/BOM/combining/RTL
  markers are the most common real-world footgun for a byte-round-trip guarantee. *Mitigation:*
  N5's property tests must include them; do not ship the round-trip guarantee without dirty-input
  coverage.
- **Direct same-ethos competitors are un-benchmarked.** NUPunkt (pure-Python, zero-dep, legal-
  SOTA) and CharBoundary (tiny ONNX-without-torch model) are the *closest* threats to the
  "best zero-dep rule engine" claim — closer than the neural SOTA we spend most NOT-doing energy
  on. *Action:* add both to the Tier-2 comparison (N6) where licenses/portability allow; if they
  beat us in the legal niche (N10), that reshapes the niche pitch.
- **Scope creep diluting the core.** *Mitigation (non-negotiable):* every heavy capability behind
  a pip extra or caller-supplied callable with lazy imports; the zero-dependency, Pyodide-
  shippable core is the default install and the project's identity; CI asserts bare-import purity.
- **Maintainer bandwidth (bus factor).** This is a multi-initiative program on essentially one
  maintainer; Next/Later is a **multi-year backlog, not a 9-month plan** (§4). *Mitigation:*
  sequence the cheap high-conversion DX win (N1) and the gate (N2) first so every later step lands
  on a safe base; the new-language scaffold + contributor path (N12) must attract repeat
  contributors before the L-effort items pile up.
- **Conversion is not fully in our control.** Discovery of a v0.0.x package is hard. Positioning
  (N1) + credible numbers (N6) + the pysbd-migration path create inbound pull, but we cannot
  guarantee ecosystem mindshare follows.
- **Open question — structure-awareness (N13):** does the RAG/markdown audience need
  fenced-code/list protection enough to justify touching the most fragile part of the engine, or do
  exact spans (N5) let consumers handle structure themselves? Defer until real `doc_type='markdown'`
  demand emerges; never on the default path.

## Sources

In-repo (verified ground truth for every accuracy/metadata claim above):
- `benchmarks/corpus_compare/results/scoreboard.baseline.json` — overall + per-corpus EM/F1 and
  per-segmenter sample sizes (n=348/318/258).
- `benchmarks/corpus_compare/results/verdicts.json` — adjudicated win tally (73/72/68) and the
  per-language case breakdown (incl. Italian 4 none_correct / 3 wins).
- `benchmarks/corpus_compare/results/divergences_all.json` — divergence counts by corpus (legal 36, largest).
- `benchmarks/corpus_compare/results/REPORT.md` (lines 312–313) — UD colon/article-number annotation-artifact note.
- `pyproject.toml` — `dependencies = []`, `uv_build>=0.11` backend, bare keywords, spaCy entry point, classifiers.
- `sentencesplit/lang/{amharic,armenian,burmese,urdu,marathi,persian}.py` — thin-tail stubs (no abbreviation lists).

External (all **approximate, early-2025 / Jan-2026 cutoff — re-verify before publishing**):
- pysbd download stats and freeze state — https://pypistats.org/packages/pysbd and https://github.com/nipunsadvilkar/pySBD
- SaT / wtpsplit (neural SOTA reference) — https://github.com/segment-any-text/wtpsplit
- NUPunkt (pure-Python zero-dep legal SBD, Apr 2025) — https://github.com/alea-institute/nupunkt
- CharBoundary (tiny ONNX-without-torch model) — https://github.com/alea-institute/charboundary
- chonkie (chunking primitive, throughput claims) — https://github.com/chonkie-inc/chonkie
- LangChain PySBDTextSplitter request — https://github.com/langchain-ai/langchain (search issues/PRs for "PySBD")
- LiveKit multilingual SBD request — https://github.com/livekit/agents (search issues for sentence boundary)
- Universal Dependencies treebanks (UD corpora used in the harness) — https://universaldependencies.org/
- Ersatz multilingual SBD corpus — https://github.com/rewicks/ersatz
- MultiLegalSBD — https://github.com/tobiasbrugger/MultiLegalSBD
- GENIA corpus — http://www.geniaproject.org/
- CoNLL-18 UD evaluation scorer (`conll18_ud_eval`) — https://universaldependencies.org/conll18/evaluation.html
