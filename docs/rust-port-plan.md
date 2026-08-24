# Rust port plan

Status: **proposal** — no code written yet. Branch: `feat/rust-port`.

## 1. Goal

Reimplement the sentencesplit engine in Rust and ship it as:

* a **PyPI** distribution (PyO3 + maturin) that is a drop-in replacement for today's
  pure-Python `Segmenter` / `StreamSegmenter`, and
* an **npm** distribution (WebAssembly) usable from Node, browsers, Deno, Bun and
  edge runtimes.

The bar for "done" is **bit-identical output** against the current Python engine on
every frozen corpus in this repo, for every language, in every `split_mode`.

### Non-goals

* Changing segmentation behavior. The port is a rewrite of *how*, never *what*. Any
  behavioral difference found during the port is a **bug in the port** until a
  maintainer explicitly adjudicates it as an intended fix (and then it lands in the
  Python engine *first*, so the two stay in lockstep).
* Retiring the Python implementation. It stays as the reference oracle, the Pyodide
  path, and the extension point for `register_language`.
* A new accuracy model. No statistical/ML boundary detection; this is a port.
* **Third-party language registration in the Rust core.** v1 ships the built-in languages
  only; custom registered languages transparently fall back to the Python engine (§3.3).

## 2. What is actually being ported

| Area | Size | Notes |
|---|---|---|
| Engine (`processor`, `segmenter`, `abbreviation_replacer`, `period_classifier`, `boundary_resplit`, `cleaner`, …) | ~5,000 LOC | The real work. Sentinel-substitution pipeline over strings. |
| Language profiles (`lang/`, 26 codes incl. `en_es_zh`, `en_legal`) | ~8,000 LOC | Overwhelmingly **data** (abbreviation lists, regex literals, flags) wearing a class costume. |
| Tests | ~13,400 LOC | Not ported. Reused as the differential oracle. |
| `spacy_component.py` | small | Stays Python. Wraps whichever core is installed. |

Frozen artifacts that become the port's acceptance corpus:

* `tests/regression/segment_snapshot.json` — 117 KB, every registered language × its own
  Golden-Rule inputs. Exact-output oracle.
* `tests/regression/gate/gold/ud_gold_subset.json` — 439 KB UD gold, scored by `boundary_f1`
  against `gate/baseline.json`.
* `benchmarks/english_golden_rules.py` — the English Golden Rules.
* `tests/contract/test_properties.py` — Hypothesis strategies, reusable to fuzz the Rust core
  against the Python oracle.

## 3. The three hard problems

Everything else is mechanical. These three decide whether the port succeeds. The first two are
engineering problems to be solved; the third (§3.3) is resolved by scoping it out of v1.

### 3.1 Regex: lookaround is not optional here

The engine uses **73 lookbehind** and **115 lookahead** constructs, plus possessive
quantifiers, atomic groups, named groups and two backreferences, across ~96 compiled
patterns. Rust's `regex` crate supports **none** of lookaround or backreferences — by
design, since it guarantees linear time.

**Decision: use `fancy-regex`** for the port. It layers a backtracking engine over
`regex`, supports lookaround / backrefs / atomic groups / possessive quantifiers, and
delegates lookaround-free subpatterns to the linear `regex` fast path automatically.

One thing works in our favor: **Python's `re` already rejects variable-width lookbehind**
("look-behind requires fixed-width pattern"), so all 73 lookbehinds in the codebase are
constant-width by construction — which is exactly the constraint `fancy-regex` imposes.

Residual risks, each with a mitigation:

* **Semantic drift in character classes.** Rust's `\w`, `\b`, `\d`, `\s` and case-folding
  follow UTS#18 definitions that differ subtly from CPython's. *Mitigation:* a
  pattern-level differential harness (§5) that compiles every pattern in both engines and
  compares match spans over a corpus, run before any pattern is trusted.
* **Backtracking blowup.** `fancy-regex` has a configurable backtrack limit; a pathological
  input that Python's engine merely runs slowly on could hard-*error* in Rust.
  *Mitigation:* set a generous limit, treat any limit hit as a test failure, and fuzz for it.
* **Perf.** Patterns that fall off the linear fast path are the likely hot spots.
  *Mitigation:* Phase 5 replaces the measured-hot lookaround patterns with hand-written
  scanners. Do this **after** parity, guarded by the differential harness — never before.

The `re.escape`-built dynamic patterns (13 sites) and the Aho-Corasick abbreviation
automaton are easier: the `aho-corasick` crate is the same algorithm, faster, and can be
built once per language profile and cached in a `OnceLock`.

### 3.2 String indexing: three languages, three units

`TextSpan.start/end` are **Python `str` indices = Unicode codepoints**. Rust slices by
**UTF-8 bytes**. JavaScript indexes by **UTF-16 code units**. For any text containing an
astral-plane character (emoji, CJK ext-B, many historic scripts) all three disagree.

**Decision:** the core computes and returns **byte offsets**; each binding converts at the
boundary to the unit its host expects:

* PyO3 → codepoint offsets (preserves today's `TextSpan` contract exactly).
* wasm → UTF-16 offsets (matches `String.prototype.slice`).
* Rust API → byte offsets, natively.

Conversion is one O(n) pass over the input with a cached prefix table, done once per
`segment_spans()` call. Cheap relative to segmentation. Every binding gets a dedicated
astral-plane span round-trip test; `tests/contract/test_span_roundtrip.py` already exists
to be extended.

### 3.3 Custom languages: deferred, with a transparent fallback

`register_language(code, language_cls)` takes a **Python class**. `LanguageProfile._build()`
reduces it to a frozen dataclass, but three of the ~30 attributes it reads are *class objects*
it will later instantiate (`AbbreviationReplacer`, `BetweenPunctuation`, `ListItemReplacer`),
and `Segmenter.__init__` grabs `Processor` and `Cleaner` the same way. So the contract is not
"a bag of data" — it is "a bag of data **and** up to five classes whose methods we will call."

An AST scan of the 26 built-ins shows what registered classes actually do:

| Tier | Overrides | Built-ins | Expressible as data? |
|---|---|---|---|
| 1 | Attributes only — abbreviation lists, flags | **19 of 26** | Yes |
| 2 | `Rule` tables (regex + replacement): `Numbers` in de/da/sk | subset of above | Yes — a `Rule` is a serializable pair |
| 3 | Methods on `Processor` / `AbbreviationReplacer` / `BetweenPunctuation` / `Cleaner` / `ListItemReplacer` | 7 (zh, ja, de, sk, kk, en_es_zh) | No |
| 4 | `AbbrPolicy.classify_special` — a callable handed the live `PeriodClassifier` and `Candidate` | 2 (de, ru) | No |

**Decision: the Rust core ships the built-in languages only. Third-party language
registration is deferred past v1**, in any form — no `LanguageSpec`, no declarative
registration API. Designing an extension vocabulary is a large, speculative surface, and
scoping it out keeps Phases 1–3 aimed squarely at parity on the languages that ship.

#### Routing rule

The Rust backend handles a language code **only when the registry still holds the canonical
built-in class for it**, compared by object identity:

```python
_rust_ok = LANGUAGE_CODES.get(code) is _CANONICAL_BUILTIN.get(code)
```

Identity, not a data-only heuristic. `register_language("zz", CustomEn)` where
`class CustomEn(English): Abbreviation = CustomAbbr` is Tier 1 — pure data — but it is still
a different class object, and honoring it would mean shipping the very spec-extraction
machinery this section defers. Everything that is not the untouched built-in class routes to
the pure-Python engine, which is always present. Consequences, all of them correct:

* An unknown code, a custom class, *or a subclass of a built-in* → Python engine. Never an error.
* `register_language("en", CustomEn)` → `"en"` silently moves to Python for the rest of the process.
* `unregister_language("en")` → resolution fails in the existing Python registry before the
  backend question is ever asked, so `UnknownLanguageError` is raised exactly as today.
* `tests/meta/test_language_reregistration.py` (stale-automaton rebuild on re-registration)
  keeps passing untouched, because re-registration always lands on the Python path.

Add `sentencesplit.backend(language=...)` so routing is introspectable rather than mysterious.

#### The seven hook-carrying built-ins are port work, not extension work

zh, ja, de, sk, kk, en_es_zh and ru carry Tier 3/4 method overrides, but they **ship with the
library** — Rust reimplements each behavior natively in Phase 2. The overrides are narrower
than "arbitrary code" suggests: extra number/date rules (de, sk), CJK quote-continuation
merging (zh, ja, en_es_zh), protect-abbreviation-before-parenthesis (kk), a Slovak list-item
line break, a Japanese newline-in-word cleaner, a Cyrillic-uppercase sentence-start check (ru),
and a German capital-noun exception (de). Roughly seven named behaviors.

Making those hooks *declarative* — which would shrink the Python-fallback set once custom
languages are picked back up — is deliberately **not** in this plan. If it happens it should
land in the Python engine on its own merits first, under the §1 rule that behavior changes
never originate in the port.

#### Why Python callbacks over FFI are not the escape hatch

PyO3 can call back into Python. It is still the wrong answer:

1. **npm has no Python.** A callback design serves only the PyPI target, so it can never be
   *the* answer — at best a PyPI-only concession that leaves wasm behind.
2. **The perf math inverts.** `classify_special` runs per period candidate;
   `_is_likely_sentence_start` runs per abbreviation occurrence. Crossing FFI at that
   frequency, with GIL acquisition and object construction each time, could make the Rust
   build *slower than pure Python* for exactly the languages that use hooks.
3. **It freezes the internals as public API.** `classify_special(pc, line, c)` hands the
   callback the live classifier. Supporting it from Rust means exposing a Python-visible
   mirror of `PeriodClassifier` and `Candidate`, locking the Rust engine into today's Python
   internal structure permanently — forfeiting much of the reason to port.
4. **Free-threading.** The core is meant to be `Send + Sync` with no global mutable state;
   running arbitrary user Python inside it drags the GIL and reentrancy back in.

#### Registry shape (separate from the port)

`register_language` mutates a process-global registry. The code does lock it
(`_LANGUAGE_LOCK`, an `RLock`), though README:~290 still describes the registry as
"non-thread-safe" — stale relative to the docstring at `languages.py:250`, worth fixing
independently. For wasm a global mutable registry across workers is worse than in Python, so
whenever custom languages are revisited, a per-`Segmenter` immutable registry is the shape to
offer.

## 4. Language data becomes shared data, not duplicated code

The single highest-leverage step, and the one that prevents the two implementations from
silently diverging six months from now.

Add `data/lang/<code>.json` — abbreviation lists, prepositive/number-only sets, boundary
regex source, CJK flags, `LATIN_UPPERCASE_RESPLIT`, punctuation tables. It is **generated**
from the Python source by `tools/dump_language_data.py`, committed to the repo, and:

* Python keeps reading its classes (unchanged), and a **CI drift check** re-runs the dumper
  and fails if the committed JSON differs. Adding an abbreviation in Python therefore cannot
  land without regenerating the shared data.
* Rust's `sentencesplit-data` crate consumes the JSON in `build.rs` and emits static tables
  (perfect-hash sets, prebuilt Aho-Corasick automata) so there is **zero parse cost at
  runtime and no data file to ship alongside the binary**.

A later, optional step is to invert this — make the JSON the source of truth and have Python
read it — but that is a separate change and not required for the port.

## 5. The differential harness is the spine of this project

Nothing is merged without it. Built in Phase 0, before any engine code.

```
tools/difftest/
  corpus.jsonl          # {lang, text, opts} — snapshot ∪ golden rules ∪ UD gold ∪ fuzz
  run_python.py         # oracle: emits {segments, spans} per case
  (rust) sentencesplit-cli difftest   # same stdin/stdout contract
  compare.py            # exact diff, per-language report, non-zero exit on any mismatch
```

Four layers, all wired into CI:

1. **Pattern-level.** Every regex compiled in both engines, matched over the corpus,
   match spans compared. Catches §3.1 drift at the smallest possible granularity.
2. **Segment-level.** Exact `segment()` / `segment_spans()` equality across the frozen
   corpora. **100% required** — no tolerance, no allowlist.
3. **Score-level.** The Rust engine runs the existing `gate_scoring.boundary_f1` against
   `gate/baseline.json` and must meet the same thresholds. This is the safety net for
   corpora not in the snapshot.
4. **Fuzz.** `cargo-fuzz` over the Rust core for panics/limit-hits, plus a Hypothesis-driven
   differential fuzzer that shells to both engines. Any divergence is a corpus addition.

## 6. Repository and crate layout

**Recommendation: monorepo.** The drift check (§4) and the differential harness (§5) are
only cheap if both implementations sit in one tree with one CI run. A split repo makes the
oracle a version-pinned dependency and invites exactly the drift this plan is designed to
prevent.

```
sentencesplit/            # existing pure-Python package — unchanged
data/lang/*.json          # generated, drift-checked shared language data
rust/
  Cargo.toml              # workspace
  crates/
    sentencesplit-core/   # engine. no bindings, no I/O. the only place logic lives
    sentencesplit-data/   # build.rs codegen from data/lang/*.json
    sentencesplit-py/     # PyO3 + maturin  -> PyPI
    sentencesplit-wasm/   # wasm-bindgen    -> npm
    sentencesplit-cli/    # dev tool: difftest, bench, repl
  fuzz/
npm/                      # TypeScript wrapper + package.json around the .wasm artifact
tools/
  dump_language_data.py
  difftest/
```

`sentencesplit-core` must stay binding-free and `Send + Sync`, with no global mutable state —
that is what makes free-threaded Python and multi-worker Node safe by construction.

## 7. Distribution

### 7.1 PyPI

* **PyO3 + maturin**, `abi3-py311` → one wheel per (OS, arch) covering 3.11 through future
  3.x. Matrix: manylinux + musllinux (x86_64, aarch64), macOS (arm64, x86_64), Windows
  (x64, arm64). Built with `PyO3/maturin-action`, published via the existing Trusted
  Publishing setup in `.github/workflows/publish.yml`.
* **Free-threaded builds need separate wheels.** The stable ABI does not currently cover
  `Py_GIL_DISABLED`, so `cp313t` / `cp314t` get their own non-abi3 wheels. The extension must
  declare `gil_used = false` and be genuinely thread-safe. This repo already has
  `tests/regression/test_free_threading.py` — that test must pass against the Rust core too,
  and CI must keep the free-threaded job.
* **Pyodide is the trap.** `package.json` here pins Pyodide for a browser CI smoke test, and
  `tests/pyodide/` exists — today's pure-Python wheel just works in the browser. A compiled
  extension does not, unless we also build an `emscripten` wheel pinned to Pyodide's ABI.
  Mitigating this is the main reason for the packaging recommendation below.

**Packaging recommendation:** keep `sentencesplit` as the name users install, and make it a
thin dispatcher that prefers a compiled core and falls back to pure Python.

```python
def Segmenter(language="en", **kw):
    if _rust is not None and LANGUAGE_CODES.get(language) is _CANONICAL_BUILTIN.get(language):
        return _rust.Segmenter(language, **kw)       # sentencesplit-core-rs, optional
    return _py.Segmenter(language, **kw)             # always present
```

Routing is **per language**, not per install (§3.3): a process can serve `en` from Rust and a
custom registered `demo` from Python simultaneously.

* `pip install sentencesplit` → unchanged today: pure Python, zero dependencies, works on
  Pyodide, PyPy, and any platform including ones we never build wheels for.
* `pip install sentencesplit[fast]` → pulls `sentencesplit-core-rs`, the compiled wheel.
* Installation can never hard-fail on a missing Rust toolchain, and the Pyodide smoke test
  keeps passing untouched.
* Add `sentencesplit.backend(language=...)` returning `"rust"` / `"python"` so users can
  assert which engine a given code resolved to, and an env var
  (`SENTENCESPLIT_BACKEND=python`) to force the fallback globally for debugging.

The alternative — make `sentencesplit` itself the compiled package — buys a simpler story at
the cost of the zero-dependency promise, the Pyodide path, and PyPy support. Not recommended,
but it is the maintainer's call (§8).

### 7.2 npm

**Recommendation: WebAssembly only for v1**, published as `sentencesplit` on npm.

`wasm-bindgen` + `wasm-pack`, wrapped in a hand-written TypeScript layer under `npm/`.
Rationale: one artifact runs on Node, browsers, Deno, Bun, Cloudflare Workers and Vercel
Edge, with no per-platform binaries, no `postinstall` script, no native toolchain, and no
supply-chain surface from optional platform packages. For a text-processing library with no
syscalls, wasm's ~1.5–2× penalty against native is dwarfed by the ~10× it gains over a pure
JS reimplementation.

Details that need doing properly:

* **Init ergonomics.** Browsers need async instantiation. Ship `await init()` for
  ESM/browser, and a Node entry point that reads the `.wasm` synchronously so Node users get
  a plain synchronous `segment()` with no await. Both from one package via conditional
  `exports`.
* **String marshalling.** Crossing the wasm boundary copies the string in and the results
  out. For a `StreamSegmenter` this happens per chunk. Benchmark it early; if it dominates,
  return offsets rather than substrings and let JS slice.
* **Bundle size is the real risk.** 26 languages of abbreviation data plus compiled regex
  tables could be large. Budget: **< 1.5 MB gzipped** for the all-languages build. Levers:
  `opt-level="z"`, `lto="fat"`, `panic="abort"`, `wasm-opt -Oz`, and — if still over — split
  language data behind subpath exports (`sentencesplit/lang/zh`) so a monolingual app pays
  only for its language. Measure in Phase 4 before committing to a shape.
* **No fallback exists here.** With no Python in the browser, the wasm build supports the
  built-in languages and nothing else; an unknown code throws a clear, named error rather than
  degrading. This is the one place §3.3's deferral is user-visible, and it is honest.
* **API shape.** Idiomatic JS/TS, not a transliterated Python API:
  `segment(text, {language, splitMode})`, `segmentSpans(...)` returning
  `{text, start, end}` with **UTF-16** offsets, and a `StreamSegmenter` class. Full `.d.ts`,
  hand-written rather than generated, so the types read well.

A native `napi-rs` addon (`@sentencesplit/node`) stays on the table for later — but only if
Phase 4 benchmarks show wasm is the bottleneck for a real workload. Do not build both up front.

## 8. Phases

Each phase has a hard exit criterion. No phase starts before the previous one's criterion is met.

### Phase 0 — Foundations (no engine code)
Extract `data/lang/*.json` + drift check; build the differential harness (all four layers);
stand up the Cargo workspace and CI skeleton; port and verify **every regex pattern** in
isolation against the Python oracle.
**Exit:** pattern-level differential passes 100%; a red-team commit that edits a Python
abbreviation list without regenerating the data fails CI.

### Phase 1 — Core engine, English only
`sentencesplit-core` with the full processing + boundary pipeline, `segment()` and
`segment_spans()`, all three `split_mode`s, `clean=False`. English only.
**Exit:** 100% exact match on the English slice of the snapshot, the English Golden Rules,
and `en_legal`; UD `en_ewt` + `en_gum` F1 ≥ baseline.

### Phase 2 — All 26 languages
Remaining language profiles, CJK boundary handling, Arabic-script and Cyrillic rules,
`en_es_zh`. Includes native Rust reimplementations of the seven hook-carrying built-ins
(§3.3) — zh, ja, de, sk, kk, en_es_zh, ru.
**Exit:** 100% exact match on the *entire* `segment_snapshot.json`; every language's UD gold
score ≥ `gate/baseline.json`.

### Phase 3 — Full API surface
`Cleaner` (`clean=True`, `doc_type="pdf"`), lookahead (`segment_with_lookahead`,
`should_wait_for_more`), `StreamSegmenter`, exceptions, and the identity-based
built-in-vs-custom routing rule (§3.3).
**Exit:** the entire `tests/contract/` suite passes against the Rust core via the harness,
including `test_stream_segmenter.py` (584 lines) and `test_lookahead.py`; every
`register_language` test in `tests/unit/`, `tests/meta/` and `tests/regression/` passes
unmodified with the Rust backend installed, by routing to Python.

### Phase 4 — Bindings and publishing
PyO3 crate + abi3 and free-threaded wheel matrix; the `sentencesplit[fast]` dispatcher;
wasm crate + TS wrapper + npm packaging; release workflows for both registries; docs.
**Exit:** the *existing* Python test suite passes unmodified against the Rust backend
(including `test_free_threading.py`); a Node + browser + Deno smoke test passes on the npm
package; both publish jobs succeed against TestPyPI and an npm dist-tag.

### Phase 5 — Performance
Only now. Profile with the existing CodSpeed setup, replace measured-hot `fancy-regex`
patterns with hand-written scanners, reduce allocation in the sentinel pipeline, cut wasm
bundle size. Every change gated by the differential harness.
**Exit:** documented, reproducible benchmarks vs. the Python engine — with real numbers, not
estimates. No speedup is claimed publicly before this phase produces them.

**Rough effort:** Phase 0 ~1–2 weeks, Phase 1 ~3–4, Phase 2 ~3–4, Phase 3 ~2–3, Phase 4 ~2–3,
Phase 5 open-ended. Call it **3–4 months** of focused work. Phases 1–2 dominate and are the
least compressible; Phase 0 is the one that must not be rushed.

## 9. Decisions needed from the maintainer

These change the work materially and should be settled before Phase 0 ends:

1. **PyPI packaging shape** — dispatcher + `[fast]` extra (recommended, preserves Pyodide /
   PyPy / zero-dep), or `sentencesplit` becomes the compiled package outright?
2. ~~**`register_language` gap**~~ — **settled: deferred past v1.** The Rust core ships
   built-in languages only; anything else routes to Python by object identity (§3.3). Revisit
   only if third-party demand appears.
3. **npm package name** — `sentencesplit` (is it available?) or a scoped `@sentencesplit/…`?
4. **Monorepo vs. separate repo** — the plan assumes monorepo; a split repo is workable but
   costs the cheap drift check.
5. **Version coupling** — do the Rust and Python packages share a version number and release
   cadence, or version independently? Shared is simpler to reason about; independent is
   kinder to the release workflow's manual bump dropdown.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Regex semantic drift between CPython `re` and `fancy-regex` | Silent wrong output | Pattern-level differential in Phase 0, before any engine code |
| Backtracking blowup on adversarial input | Hard error where Python was merely slow | Backtrack limit + fuzzing; Phase 5 scanner replacement |
| Compiled extension breaks Pyodide | Loses browser Python support | Dispatcher keeps the pure-Python fallback; wasm covers browsers anyway |
| Two engines drift after launch | The port becomes a liability | Shared data + CI drift check + differential harness on every PR, forever |
| wasm bundle too large | npm package unusable for web | Size budget enforced in CI; per-language subpath exports as the escape hatch |
| Scope creep into "fix behavior while porting" | Parity becomes unmeasurable | Non-goal stated in §1; fixes land in Python first, always |
| Custom-language users silently get no speedup | Surprise, not breakage | `backend(language=...)` makes routing introspectable; documented in §3.3 |
| wasm users need a custom language | Hard blocker, no fallback | Accepted for v1 and stated plainly in the npm docs |
