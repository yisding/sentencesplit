export const meta = {
  name: 'execute-roadmap',
  description: 'Execute the LEVEL_UP_PLAN roadmap one item at a time (default N2, the regression gate): design -> implement test-first on a branch -> adversarially verify (incl. planting a regression to prove the gate catches it) -> commit-or-revert, then refresh a dependency-ordered execution backlog for the rest',
  whenToUse: 'After analysis/LEVEL_UP_PLAN.md exists, to actually build the roadmap. Default run implements N2 (the hermetic regression gate). Pass args.items=["N3"] etc. to implement a different item. Always (re)writes analysis/ROADMAP_EXECUTION.md.',
  phases: [
    { title: 'Setup', detail: 'branch off origin/main, confirm a green baseline suite' },
    { title: 'Design', detail: 'read the code + plan, produce a concrete implementation design for the item(s) being built this run' },
    { title: 'Implement', detail: 'sequentially build each item test-first; ruff + full suite + Golden-Rules guard; commit or fully revert' },
    { title: 'Verify', detail: 'adversarially confirm it works (for N2: hermetic + actually fails on a planted regression); one fix attempt if it fails' },
    { title: 'Backlog', detail: 'spec every remaining roadmap item and write a dependency-ordered execution backlog' },
    { title: 'Report', detail: 'summarize what landed, what was reverted, and the branch left for review' },
  ],
}

const ROOT = '/home/yi/Code/sentencesplit'
const CC = `${ROOT}/benchmarks/corpus_compare`
const RESULTS = `${CC}/results`
const PLAN = `${ROOT}/analysis/LEVEL_UP_PLAN.md`

// Robust arg parsing (workflow `args` may arrive as a JSON string).
let opts = {}
try {
  opts = typeof args === 'string' ? JSON.parse(args) : args || {}
} catch {
  opts = {}
}
const SLUGS = { N2: 'regression-gate', N5: 'span-roundtrip', N4: 'stream-segmenter', N1b: 'extra-abbreviations' }

function parseItems(value, fallback) {
  const raw = value === undefined ? fallback : value
  return (Array.isArray(raw) ? raw : [raw]).map((item) => String(item))
}

function validateGitRef(name, label) {
  const ref = String(name)
  if (ref.length === 0 || ref.length > 200) {
    throw new Error(`${label} must be a non-empty Git ref shorter than 201 characters`)
  }
  if (ref.startsWith('-')) {
    throw new Error(`${label} must not start with '-'`)
  }
  if (!/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(ref)) {
    throw new Error(`${label} contains characters outside the safe Git ref allowlist`)
  }
  if (
    ref.includes('..') ||
    ref.includes('@{') ||
    ref.includes('//') ||
    ref.endsWith('/') ||
    ref.endsWith('.') ||
    ref.includes('.lock/')
  ) {
    throw new Error(`${label} is not an allowed Git ref`)
  }
  for (const part of ref.split('/')) {
    if (part === '' || part.startsWith('.') || part.endsWith('.lock')) {
      throw new Error(`${label} contains an invalid Git ref path component`)
    }
  }
  return ref
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`
}

// ── The roadmap, distilled from analysis/LEVEL_UP_PLAN.md (§4). ─────────────────
// kind: infra | dev-tests | additive | additive-api | behavior-change | integration | lang | domain | docs
const ROADMAP = {
  N2: {
    title: 'Hermetic CI regression gate',
    kind: 'infra', effort: 'M', horizon: 'now', depends_on: [], ready: 'ready',
    spec: `A pure-Python, hermetic pytest that scores ONLY sentencesplit against a committed gold corpus
subset (NO Ruby, NO NLTK, NO network, NO native wheels — it MUST run on this aarch64 box), diffs per-language
exact-match and boundary-F1 against a committed gate baseline, and FAILS the PR on a per-language drop beyond a
per-language tolerance. Ships from day one with: (1) per-language tolerances; (2) an explicit, reviewed
\`# baseline-update\` flow — a documented command/flag that regenerates the committed baseline and requires a
one-line rationale; (3) a documented net-positive-trade rule (a change that is net-positive on the union of
corpora may update the baseline even if one language dips). Reuse the EM / boundary-F1 scoring already in
benchmarks/corpus_compare/run_compare.py rather than reinventing it. Vendor a SMALL, license-safe gold subset:
the English Golden Rules are already in-repo (benchmarks/english_golden_rules.py / golden_rules.txt); UD
treebank gold is redistributable — vendor the specific gold units actually used, with attribution. Make it a
normal test under tests/ so CI runs it automatically (no separate CI wiring needed). This directly prevents the
silent per-language regression class (a Dutch regression slipped through once, caught only by manual review).`,
  },
  N5: {
    title: 'Span-faithful round-trip contract + property tests',
    kind: 'dev-tests', effort: 'S-M', horizon: 'now', depends_on: [], ready: 'ready',
    spec: `Make non-destructive spans a CI-enforced guarantee: every unit from segment_spans() maps to an exact
[start,end) slice and reassembling the spans reproduces the source byte-for-byte. Add Hypothesis property tests
(dev-only dependency — must NOT touch the zero-dependency core) for the round-trip invariant; cover dirty input
explicitly (ZWSP / NBSP / BOM / combining marks / RTL markers). Resolve the redundant char_span flag vs
segment_spans() path. The byte-for-byte span round-trip is the citation-fidelity guarantee downstream
consumers (e.g. legal/RAG span alignment) depend on.`,
  },
  N4: {
    title: 'StreamSegmenter (first-class streaming)',
    kind: 'additive', effort: 'S-M', horizon: 'now', depends_on: [], ready: 'ready',
    spec: `A stateful StreamSegmenter wrapping the existing, tested segment_with_lookahead() /
should_wait_for_more() primitives: accept text/token deltas, emit completed sentences once their boundary is
stable, buffer the unstable tail. Conservative buffering by default. Add a latency-to-first-stable-sentence
benchmark and a streaming-to-TTS recipe. Additive — wraps existing primitives, does not change segment() output.`,
  },
  N1b: {
    title: 'extra_abbreviations= constructor argument',
    kind: 'behavior-change', effort: 'M', horizon: 'now', depends_on: ['N2'], ready: 'needs-decision',
    spec: `Make extra_abbreviations=[...] a first-class Segmenter argument instead of requiring a Common/Standard
subclass, feeding the existing Aho-Corasick automaton WITHOUT breaking the precompiled cache. The
cache-invalidation correctness is the real work — give it dedicated regression tests. Behavior-changing but
opt-in: default output is unchanged. This is the first behavior-changing PR and MUST land after N2 so the gate
guards it. It is the #1 recurring ask on pysbd's tracker.`,
  },
  N6: {
    title: 'Public leaderboard with standard metrics',
    kind: 'docs', effort: 'L', horizon: 'next', depends_on: ['N2'], ready: 'needs-decision',
    spec: `Promote benchmarks/corpus_compare into a versioned public artifact tied to each release tag (README
badge + generated page). Split into sub-projects: add char-level boundary-F1 (WtP/SaT metric); reimplement
CoNLL-18 UD Sentences-F1 scoring in stdlib (no dependency); add a chunk-quality metric (mid-sentence-cut rate
vs RecursiveCharacterTextSplitter). Download scripts only (never vendor) for Ersatz / GENIA / MultiLegalSBD.
Publish sample sizes + the mixed-n caveat (n=348 / 318 / 258) and per-UD-corpus n=30 framing with EVERY number.
Needs the N2 governance flow finalized before publishing the gate externally.`,
  },
  N9: {
    title: 'Add Portuguese; close Dutch/German abbreviation gap',
    kind: 'lang', effort: 'L', horizon: 'next', depends_on: ['N2'], ready: 'needs-external',
    spec: `Add pt via the TDD recipe (highest-priority absent language, ~250M speakers, Romance-analogous to
es/fr, a MultiLegalSBD language). Then mine UD divergences for the abbreviations/patterns Punkt catches and we
miss in Dutch (63.3 — trails both Punkt 90.0 AND pysbd 66.7) and German (63.3 vs Punkt 73.3); hand-curate with
per-case regression tests, gated by N2. Where the miss is a shared-rule issue, fix the rule. Needs native /
corpus validation; measure per-language ROI after the first pass and stop where curation cost exceeds gain.`,
  },
  N10: {
    title: 'Offline / air-gapped legal-RAG niche',
    kind: 'domain', effort: 'M', horizon: 'next', depends_on: ['N6'], ready: 'needs-decision',
    spec: `Legal is the single largest cross-library divergence bucket (36, vs 24 Golden Rules, 18 Italian).
Triage the 36 legal divergences into curatable sub-bugs vs artifacts, harden en_legal, add a citation-faithful
legal segmentation recipe (exact spans for citation alignment), and put it on the leaderboard (N6). Position as
a deterministic, auditable, offline/air-gapped legal segmentation primitive where torch-based tools are
non-starters.`,
  },
  N11: {
    title: 'Open-quote / multi-sentence boundary suppression (1/3 -> 3/3)',
    kind: 'behavior-change', effort: 'M', horizon: 'later', depends_on: ['N2'], ready: 'needs-decision',
    spec: `A more discriminating signal for the open-quote resplit (interior terminal-punctuation count,
capitalization runs inside the quote, quote-pair span length), validated against the gold-KEEP cases. Subsumes
the genuine Italian open-quote sub-bug and extends to CJK quote continuations. Genuinely hard — the remaining
cases are structurally indistinguishable from gold-KEEP.`,
  },
  N12: {
    title: 'Deepen the thin-tail languages + new-language scaffold',
    kind: 'lang', effort: 'L', horizon: 'later', depends_on: ['N2'], ready: 'needs-external',
    spec: `Curate real abbreviation lists for the ~11-line stubs (amharic / armenian / burmese / urdu / marathi /
persian — currently boundary regex + punctuation, NO abbreviation list) ONLY where native-speaker or corpus
validation is available (no coverage theater). Ship a scaffold/generator (test + lang module + registry entry)
and a "good first language" contributor path tied to the N2 gate. For absent high-demand languages
(ko/vi/th/tr/id/he/Nordics), treat RTL (Hebrew/Arabic-script) and scriptio-continua (Thai) as DISTINCT work —
they break the N5 span and N3 chunk assumptions and need their own fixtures before shipping.`,
  },
  N13: {
    title: 'Optional structure-aware pre-pass (markdown/code) — gated',
    kind: 'behavior-change', effort: 'L', horizon: 'later', depends_on: [], ready: 'needs-decision',
    spec: `A pre-segmentation pass protecting fenced/inline code and list markers from triggering boundaries,
behind doc_type='markdown', NEVER on the default code path. Highest-regression-risk item (threads near the
C901-exempt split_into_segments). Regression-test before shipping. Only if real demand for markdown/code-aware
segmentation emerges (e.g. doc_type='markdown' requests).`,
  },
}

const ITEMS_THIS_RUN = parseItems(opts.items, opts.item ? [opts.item] : ['N2'])
if (ITEMS_THIS_RUN.length === 0) {
  throw new Error('At least one roadmap item is required')
}
const unknownItems = ITEMS_THIS_RUN.filter((id) => !Object.hasOwn(ROADMAP, id))
if (unknownItems.length > 0) {
  throw new Error(`Unknown roadmap item(s): ${unknownItems.join(', ')}`)
}

const defaultBranch =
  ITEMS_THIS_RUN.length === 1 && SLUGS[ITEMS_THIS_RUN[0]]
    ? `feat/${SLUGS[ITEMS_THIS_RUN[0]]}`
    : `feat/roadmap-${ITEMS_THIS_RUN.map((s) => s.toLowerCase()).join('-')}`
const BRANCH = validateGitRef(opts.branch || defaultBranch, 'branch')
const BASE = validateGitRef(opts.base || 'origin/main', 'base')
const CHECKOUT_COMMAND = `git checkout -b ${shellQuote(BRANCH)} ${shellQuote(BASE)}`

const GUARD = `GUARDRAILS (follow exactly):
- Work in ${ROOT} on the already-checked-out branch \`${BRANCH}\`. NEVER push. NEVER touch main/origin.
- TEST-FIRST: write the test(s) before the implementation and confirm they fail (red) first where applicable.
- Match surrounding style; ruff line length 127. Run \`uv run ruff format\` + \`uv run ruff check\` on changed files.
- The zero-dependency core is sacred: a bare \`import sentencesplit\` must pull in NO third-party module. Any new
  dependency (e.g. Hypothesis for property tests) goes in the [dependency-groups] dev group ONLY, never in
  [project].dependencies. tests/test_zero_dependencies.py enforces this — it must stay green.
- FULL SUITE must stay green (run on this aarch64 box; the spaCy import test crashes the interpreter here, so
  exclude it): \`uv run pytest -q --ignore=tests/test_spacy_component.py\`.
- GOLDEN RULES must not regress. Count them before and after with:
  \`uv run python -c "import sys; sys.path.insert(0,'benchmarks'); from english_golden_rules import GOLDEN_EN_RULES as G; import sentencesplit as s; seg=s.Segmenter(language='en'); print(sum(1 for t,e in G if [x.strip() for x in seg.segment(t)]==e), len(G))"\`
- COMMIT-OR-REVERT: if the suite stays green AND Golden Rules did not regress, \`git add\` ONLY the files you
  changed and commit with a Conventional Commit subject. Otherwise \`git checkout -- <changed files>\` and delete
  any new files to fully revert, and report status accordingly.`

// ── schemas ─────────────────────────────────────────────────────────────────────

const DESIGN_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['item', 'approach', 'files_to_create', 'files_to_modify', 'public_api', 'test_plan', 'risks', 'special_notes'],
  properties: {
    item: { type: 'string' },
    approach: { type: 'string', description: 'concrete step-by-step plan grounded in the actual code read' },
    files_to_create: { type: 'array', items: { type: 'string' } },
    files_to_modify: { type: 'array', items: { type: 'string' } },
    public_api: { type: 'string', description: 'new/changed public surface, or "none"' },
    test_plan: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
    special_notes: { type: 'string', description: 'for N2: how it stays hermetic, what gold is vendored, the baseline-update governance flow' },
  },
}

const IMPLEMENT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['item', 'status', 'files_changed', 'test_files', 'suite_passed', 'golden_rules_before', 'golden_rules_after', 'commit', 'notes'],
  properties: {
    item: { type: 'string' },
    status: { type: 'string', enum: ['implemented', 'partial', 'reverted', 'error'] },
    files_changed: { type: 'array', items: { type: 'string' } },
    test_files: { type: 'array', items: { type: 'string' } },
    suite_passed: { type: 'boolean' },
    golden_rules_before: { type: ['integer', 'null'] },
    golden_rules_after: { type: ['integer', 'null'] },
    commit: { type: 'string', description: 'commit hash if committed, else ""' },
    notes: { type: 'string' },
  },
}

const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['item', 'verdict', 'suite_green', 'runs_on_this_box', 'problems'],
  properties: {
    item: { type: 'string' },
    verdict: { type: 'string', enum: ['pass', 'fail', 'n/a'] },
    suite_green: { type: 'boolean' },
    runs_on_this_box: { type: 'boolean' },
    hermetic: { type: ['boolean', 'null'], description: 'N2 only: gate logic uses no network/Ruby/NLTK/native/3rd-party' },
    catches_planted_regression: { type: ['boolean', 'null'], description: 'N2 only: a deliberately planted per-language regression made the gate fail red' },
    problems: { type: 'array', items: { type: 'string' } },
  },
}

const BACKLOG_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['id', 'title', 'kind', 'effort', 'horizon', 'depends_on', 'ready', 'summary', 'files', 'public_api', 'test_plan', 'risks'],
  properties: {
    id: { type: 'string' }, title: { type: 'string' }, kind: { type: 'string' },
    effort: { type: 'string' }, horizon: { type: 'string' },
    depends_on: { type: 'array', items: { type: 'string' } },
    ready: { type: 'string', enum: ['ready', 'needs-decision', 'needs-external'] },
    summary: { type: 'string', description: 'what to build, in 2-4 sentences, grounded in the real code' },
    files: { type: 'array', items: { type: 'string' }, description: 'concrete files to create/modify' },
    public_api: { type: 'string' },
    test_plan: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
  },
}

const CONTEXT = `PROJECT: sentencesplit — rule-based SBD, 24 languages, pure Python, ZERO runtime deps, Python 3.11+.
Repo root: ${ROOT}. The full roadmap lives at ${PLAN} (read §4 "Roadmap" and §5 "Accuracy & evaluation plan").
N1 (list_languages + metadata + the zero-dependency import test) is ALREADY DONE on a separate branch.
Pipeline: Segmenter (segmenter.py) -> Processor (processor.py) -> sentences. Spans via segment_spans()/_match_spans().
Abbreviations via the Aho-Corasick automaton in abbreviation_replacer.py. Cross-library benchmark harness +
per-corpus baseline in ${CC} (run_compare.py has the EM/boundary-F1 scoring; results/scoreboard.baseline.json
has per-corpus per-language baselines: n=348 overall; UD corpora n=30 each).`

// ── Phase 1: Setup ───────────────────────────────────────────────────────────────

phase('Setup')
log(`Implementing this run: ${ITEMS_THIS_RUN.join(', ')} on branch ${BRANCH} (base ${BASE})`)
const setup = await agent(
  `${CONTEXT}\n\nPrepare an isolated branch. In ${ROOT}:
1. \`git fetch origin\` then \`git rev-parse --abbrev-ref HEAD\` (note the current branch).
2. Create and switch to branch \`${BRANCH}\` based on \`${BASE}\`: \`${CHECKOUT_COMMAND}\` (if it already exists, check it out and report that — do NOT reset it). Untracked files (analysis/, benchmark harness) will follow; leave them.
3. Confirm a GREEN baseline before any change (exclude the spaCy test, which crashes this aarch64 box):
   \`uv run pytest -q --ignore=tests/test_spacy_component.py\` — report only the final summary line.
4. Capture the Golden Rules baseline count with the one-liner from the guardrails.
Report: starting branch, that ${BRANCH} is checked out off ${BASE}, the pytest summary line, and the Golden Rules count. Keep it short. Do NOT commit anything.`,
  { label: 'branch-setup', phase: 'Setup', agentType: 'general-purpose' },
)
log('Setup: ' + String(setup).split('\n').slice(-4).join(' ').slice(0, 240))

// ── Phase 2: Design (parallel, read-only) ────────────────────────────────────────

phase('Design')
const designs = await parallel(
  ITEMS_THIS_RUN.map((id) => () => {
    const it = ROADMAP[id]
    if (!it) return Promise.resolve(null)
    return agent(
      `${CONTEXT}\n\n=== DESIGN ${id}: ${it.title} ===\nSPEC:\n${it.spec}\n\nProduce a CONCRETE implementation design. READ the actual code first — for ${id} that means${
        id === 'N2'
          ? ` ${PLAN} (§N2 + §5 + the cross-cutting governance), ${CC}/run_compare.py (reuse its EM/boundary-F1 scoring), ${CC}/corpora.py (gold structure + licenses), ${CC}/segmenters.py (availability probes), ${RESULTS}/scoreboard.baseline.json (the per-language baseline to diff against), ${ROOT}/benchmarks/english_golden_rules.py + benchmarks/golden_rules.txt (gold already in-repo), and the tests/ + .github/ layout. Decide EXACTLY: which license-safe gold to vendor and where (tests/data/?), how to reuse run_compare scoring without importing Ruby/NLTK/native, the committed gate-baseline format + path, the per-language tolerance values, and the reviewed \`# baseline-update\` command/flag + the net-positive-trade rule.`
          : ` the relevant modules under sentencesplit/ and existing tests.`
      }\nBe specific: exact file paths, exact public API signatures, and a test plan that the implementer can follow directly.`,
      { label: `design:${id}`, phase: 'Design', schema: DESIGN_SCHEMA, agentType: 'Explore' },
    )
  }),
).then((r) => r.filter(Boolean))

const designById = {}
for (const d of designs) designById[d.item] = d
log(`Designs ready: ${designs.map((d) => d.item).join(', ')}`)

// ── Phase 3: Implement (SEQUENTIAL — avoids working-tree conflicts) ──────────────

phase('Implement')
const built = []
for (const id of ITEMS_THIS_RUN) {
  const it = ROADMAP[id]
  if (!it) {
    log(`  skip ${id}: not a known roadmap item`)
    continue
  }
  const design = designById[id]
  const r = await agent(
    `${CONTEXT}\n\n=== IMPLEMENT ${id}: ${it.title} ===\nSPEC:\n${it.spec}\n\nDESIGN TO FOLLOW (from the design phase):\n${JSON.stringify(design)}\n\n${GUARD}\n\nImplement ${id} per the design, test-first. ${
      id === 'N2'
        ? 'Make the gate a normal pytest under tests/ so CI runs it automatically. Commit the vendored gold, the gate test, the committed gate baseline, and the governance doc. After committing, the working tree must be clean.'
        : ''
    }\nWhen done, commit (or fully revert) per the guardrails with a Conventional Commit message (e.g. \`feat(...)\`, \`test(...)\`, \`build(...)\`). Report status, files changed, test files, suite_passed, golden_rules before/after, the commit hash (or ""), and concise notes (including anything you deferred).`,
    { label: `implement:${id}`, phase: 'Implement', schema: IMPLEMENT_SCHEMA, agentType: 'general-purpose' },
  )
  // Force the canonical roadmap id (don't trust the agent-returned `item`, which
  // may come back as the title/slug and break downstream ROADMAP[id] lookups).
  if (r) built.push({ ...r, item: id })
  log(`  [${r ? r.status : 'null'}] ${id} ${it.title}${r && r.commit ? ` (${r.commit.slice(0, 9)})` : ''}`)
}

// ── Phase 4: Verify (adversarial). For N2: hermetic + catches a planted regression ─

phase('Verify')
let verifications = await parallel(
  built.map((b) => () => {
    const id = b.item
    if (b.status === 'reverted' || b.status === 'error') {
      return Promise.resolve({ item: id, verdict: 'n/a', suite_green: false, runs_on_this_box: false, hermetic: null, catches_planted_regression: null, problems: [`not implemented (status=${b.status})`] })
    }
    const n2Extra =
      id === 'N2'
        ? `\nThis is the regression gate — be especially adversarial:
1. HERMETIC: read the gate test + any helper module it imports. Confirm it pulls in NO network, NO subprocess-to-Ruby, NO NLTK, NO spaCy/stanza/blingfire, NO third-party module — only stdlib + sentencesplit + the committed gold/baseline. (Sanity check: the relevant scoring import path runs under \`uv run python -I\`.)
2. CATCHES A REAL REGRESSION: introduce a SMALL deliberate, UNCOMMITTED segmentation regression for at least one gated language (e.g. a one-line edit to a rule in sentencesplit/ that worsens that language's output). Run the gate; CONFIRM it FAILS red and names the regressed language. Then \`git checkout -- <the edited file>\` to FULLY revert the plant, and confirm the gate is GREEN again. Set catches_planted_regression accordingly and describe what you planted.
3. Confirm the \`# baseline-update\` flow exists and is documented.`
        : `\nConfirm the new behavior/tests actually exercise the feature, the public API matches the design, and the zero-dependency import test (tests/test_zero_dependencies.py) is still green.`
    return agent(
      `${CONTEXT}\n\n=== VERIFY ${id}: ${ROADMAP[id]?.title || id} ===\nImplementation report: ${JSON.stringify(b)}\n\nVerify it on branch \`${BRANCH}\` in ${ROOT}. Run the full suite (\`uv run pytest -q --ignore=tests/test_spacy_component.py\`) and confirm it is green and runs on this aarch64 box.${n2Extra}\n\nLEAVE THE TREE CLEAN: revert any temporary plant/edit you made (\`git status\` must be clean at the end, with the committed work intact). Report verdict (pass only if everything checks out), suite_green, runs_on_this_box, hermetic + catches_planted_regression (N2; null for others), and any problems.`,
      { label: `verify:${id}`, phase: 'Verify', schema: VERIFY_SCHEMA, agentType: 'general-purpose' },
    )
  }),
).then((r) => r.filter(Boolean))

// One fix attempt for any item that failed verification.
const failed = verifications.filter((v) => v.verdict === 'fail')
if (failed.length) {
  log(`Verify: ${failed.length} item(s) failed — attempting one fix pass each`)
  for (const v of failed) {
    const id = v.item
    const meta = ROADMAP[id]
    if (!meta) {
      log(`  fix: skipping unknown item ${id}`)
      continue
    }
    await agent(
      `${CONTEXT}\n\n=== FIX ${id}: ${meta.title} (failed verification) ===\nProblems found:\n${JSON.stringify(v.problems)}\n\nSPEC:\n${meta.spec}\n\n${GUARD}\n\nFix the problems on branch \`${BRANCH}\`. If you cannot fix them safely, fully revert ${id}'s commit (\`git revert\` or reset the specific files) and say so. Amend/add a follow-up commit. Report what you changed.`,
      { label: `fix:${id}`, phase: 'Verify', agentType: 'general-purpose' },
    )
  }
  // Re-verify the previously-failed items.
  const reverified = await parallel(
    failed.map((v) => () =>
      agent(
        `${CONTEXT}\n\nRe-verify ${v.item} (${ROADMAP[v.item]?.title || v.item}) on branch \`${BRANCH}\` after the fix pass. Run \`uv run pytest -q --ignore=tests/test_spacy_component.py\`.${v.item === 'N2' ? ' Re-confirm the gate is hermetic and still catches a planted per-language regression (plant, confirm red, revert, confirm green).' : ''} Leave the tree clean. Report the same fields.`,
        { label: `reverify:${v.item}`, phase: 'Verify', schema: VERIFY_SCHEMA, agentType: 'general-purpose' },
      ),
    ),
  ).then((r) => r.filter(Boolean))
  const byItem = {}
  for (const v of reverified) byItem[v.item] = v
  verifications = verifications.map((v) => byItem[v.item] || v)
}
log(`Verify: ${verifications.map((v) => `${v.item}=${v.verdict}`).join(', ')}`)

// ── Phase 5: Backlog — spec every NOT-yet-implemented item (parallel, read-only) ──

phase('Backlog')
const implementedOk = new Set(built.filter((b) => b.status === 'implemented' || b.status === 'partial').map((b) => b.item))
const remaining = Object.keys(ROADMAP).filter((id) => !implementedOk.has(id))
const backlog = await parallel(
  remaining.map((id) => () => {
    const it = ROADMAP[id]
    return agent(
      `${CONTEXT}\n\n=== SPEC ${id}: ${it.title} (kind=${it.kind}, effort=${it.effort}, horizon=${it.horizon}, depends_on=${JSON.stringify(it.depends_on)}, ready=${it.ready}) ===\nROADMAP SPEC:\n${it.spec}\n\nProduce a concrete, ready-to-implement backlog entry. READ the actual code that this would touch under sentencesplit/ (and relevant tests/benchmarks) so the file list and API are real, not guessed. Carry through id/title/kind/effort/horizon/depends_on/ready as given.`,
      { label: `spec:${id}`, phase: 'Backlog', schema: BACKLOG_SCHEMA, agentType: 'Explore' },
    )
  }),
).then((r) => r.filter(Boolean))

// dependency-order the backlog (topological-ish: fewer unmet deps first, then horizon)
const horizonRank = { now: 0, next: 1, later: 2 }
const doneOrImpl = new Set([...implementedOk, 'N1'])
const ordered = [...backlog].sort((a, b) => {
  const ua = a.depends_on.filter((d) => !doneOrImpl.has(d)).length
  const ub = b.depends_on.filter((d) => !doneOrImpl.has(d)).length
  if (ua !== ub) return ua - ub
  return (horizonRank[a.horizon] ?? 9) - (horizonRank[b.horizon] ?? 9)
})

const backlogDoc = await agent(
  `${CONTEXT}\n\n=== YOUR TASK ===\nWrite ${ROOT}/analysis/ROADMAP_EXECUTION.md — the living execution backlog for the LEVEL_UP_PLAN roadmap.\n\nThis run implemented: ${JSON.stringify(built.map((b) => ({ item: b.item, status: b.status, commit: b.commit })))}\nVerification: ${JSON.stringify(verifications)}\nBranch left for review: ${BRANCH}\n\nRemaining items (already dependency-ordered, with grounded specs):\n${JSON.stringify(ordered)}\n\nWrite these sections:\n1. **Status** — what is DONE (N1; plus anything implemented this run, with commit + verify verdict) and on which branch.\n2. **Execution order** — a checklist of the remaining items in the given order, each line: \`[ ] <id> — <title> (effort, horizon, ready) — depends on: <deps>\`. Group by horizon (Now / Next / Later).\n3. **Per-item specs** — for each remaining item, a subsection with: summary, files to create/modify, public API, test plan, risks, and dependency/readiness notes (ready / needs-decision / needs-external — say what decision or external input is needed).\n4. **How to run the next item** — note that \`Workflow({name:"execute-roadmap", args:{items:["<id>"]}})\` implements one item end-to-end with the same guardrails, and that N2's gate now guards behavior-changing items.\n5. **Cross-cutting** — the SemVer/stability contract reminder from the plan (new public surfaces at v0.0.x; "we never change output" vs "we keep improving accuracy" must be reconciled before the public leaderboard).\n\nReturn a 6-10 line plain-text executive summary.`,
  { label: 'write-backlog', phase: 'Backlog', agentType: 'general-purpose' },
)
log('Backlog written to analysis/ROADMAP_EXECUTION.md')

// ── Phase 6: Report ──────────────────────────────────────────────────────────────

phase('Report')
return {
  branch: BRANCH,
  base: BASE,
  implemented: built.map((b) => ({ item: b.item, status: b.status, commit: b.commit, suite_passed: b.suite_passed })),
  verification: verifications.map((v) => ({ item: v.item, verdict: v.verdict, hermetic: v.hermetic, catches_planted_regression: v.catches_planted_regression, problems: v.problems })),
  backlog_items: ordered.map((b) => ({ id: b.id, ready: b.ready, depends_on: b.depends_on })),
  artifacts: { backlog: 'analysis/ROADMAP_EXECUTION.md' },
  executive_summary: backlogDoc,
}
