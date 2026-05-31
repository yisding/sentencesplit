export const meta = {
  name: 'parallel-implement-review',
  description: 'Implement N5 (span round-trip + property tests) and N4 (StreamSegmenter) concurrently, each in its own git worktree/branch off the N1+N2 integration base, merge all four items into one branch, then run a multi-dimension adversarial review of ALL the work so far (N1+N2+N5+N4) vs origin/main',
  whenToUse: 'To build N5 and N4 in true parallel (separate worktrees) on top of the existing N1+N2 work, then review everything done so far as a unit. Produces feature branches, an integration branch feat/now-all, and analysis/REVIEW_NOW.md.',
  phases: [
    { title: 'Setup', detail: 'confirm green N1+N2 base, create one git worktree+branch per item off feat/now-integration' },
    { title: 'Implement', detail: 'build N5 and N4 concurrently, each in its worktree: test-first, ruff, full suite + gate + zero-dep + Golden Rules guard, commit or revert' },
    { title: 'Integrate', detail: 'merge the landed N5/N4 branches into feat/now-all (= N1+N2+N5+N4), verify green, remove the temp worktrees' },
    { title: 'Review', detail: 'multi-dimension review of the FULL diff origin/main..feat/now-all across correctness / API-DX / tests / zero-dep+style' },
    { title: 'Verify', detail: 'adversarially verify each finding (refute-by-default); keep only the survivors' },
    { title: 'Report', detail: 'write the review report covering all work so far; list branches' },
  ],
}

const ROOT = '/home/yi/Code/sentencesplit'
const PLAN = `${ROOT}/analysis/LEVEL_UP_PLAN.md`
const BACKLOG = `${ROOT}/analysis/ROADMAP_EXECUTION.md`
const ORIGIN = 'origin/main'
const NOWBASE = 'feat/now-integration' // pre-created: N1 (list_languages + metadata + zero-dep test) + N2 (regression gate)
const ALLBRANCH = 'feat/now-all' // integration of N1+N2+N5+N4, the review target

const SUITE = `uv run pytest -q --ignore=tests/test_spacy_component.py` // spaCy import SIGILLs on this aarch64 box
const GOLDEN = `uv run python -c "import sys; sys.path.insert(0,'benchmarks'); from english_golden_rules import GOLDEN_EN_RULES as G; import sentencesplit as s; seg=s.Segmenter(language='en'); print(sum(1 for t,e in G if [x.strip() for x in seg.segment(t)]==e), len(G))"`

// What "all the work so far" means, for the reviewers.
const MANIFEST = `WORK DONE SO FAR (the cumulative diff ${ORIGIN}..${ALLBRANCH} contains all four):
- N1 — list_languages() discovery + package metadata (Typing::Typed, Development Status, keywords) + a
  zero-dependency import test (tests/test_zero_dependencies.py). Files: sentencesplit/{__init__,languages,
  segmenter}.py, pyproject.toml, README.md, tests/{test_languages,test_segmenter,test_zero_dependencies}.py.
- N2 — hermetic CI regression gate scoring sentencesplit vs committed gold, failing on per-language EM/F1 drops,
  with a reviewed --update-baseline governance flow. Files: tests/regression/gate/* + tests/regression/test_regression_gate.py.
- N5 — byte-for-byte segment_spans() round-trip contract + Hypothesis property tests (dev-only dep) + dirty-input
  fixtures; char_span deprecated in favor of segment_spans(). [implemented this run]
- N4 — StreamSegmenter wrapping segment_with_lookahead()/should_wait_for_more() + latency benchmark + TTS recipe. [implemented this run]
Detailed specs: ${BACKLOG}. Strategy: ${PLAN}.`

const ITEMS = [
  {
    id: 'N5',
    title: 'Span-faithful round-trip contract + property tests',
    branch: 'feat/span-roundtrip',
    wt: '/home/yi/Code/ss-wt-n5',
    spec: `Enforce a CI-gated, byte-for-byte round-trip contract for segment_spans(): every sentence maps to an exact
[start,end) slice of the source, and reassembling all spans reproduces the source verbatim. Add **Hypothesis**
property tests (DEV-ONLY dependency — add to the dev dependency group, NEVER to [project].dependencies; the bare
\`import sentencesplit\` must stay zero-dependency, enforced by tests/test_zero_dependencies.py which is present on
this base) across clean AND dirty inputs (ZWSP U+200B / NBSP U+00A0 / BOM U+FEFF / combining marks / RTL marker
U+202E), spanning the 24 languages + en_es_zh. Make segment_spans() the canonical spans API and *deprecate but
keep* the char_span flag (back-compat). New test file tests/test_span_roundtrip.py. Touch points: segmenter.py,
processor.py, utils.py, tests/conftest.py, tests/test_segmenter.py. Property: all(text[s.start:s.end]==s.sent) AND
text == "".join(s.sent for s in segment_spans(text)); bounds 0<=start<end<=len; no overlaps; no gaps. One in-scope
design call: whether RTL/directional-format chars get stripped from plain segments — decide during implementation
and validate against the suite. Fixing any latent _match_spans()/_strip_zero_width bug Hypothesis reveals is ON the
critical path.`,
  },
  {
    id: 'N4',
    title: 'StreamSegmenter (first-class streaming)',
    branch: 'feat/stream-segmenter',
    wt: '/home/yi/Code/ss-wt-n4',
    spec: `A stateful StreamSegmenter wrapping the existing, tested segment_with_lookahead() / should_wait_for_more()
primitives. Accepts text/token deltas, emits completed sentences once their boundary is stable (via lookahead
probes), buffers the unstable tail, defaults to conservative buffering. ADDITIVE — does not change segment()
output. New module sentencesplit/stream_segmenter.py; export from sentencesplit/__init__.py (note __init__.py also
exports list_languages from N1 — keep both). API: class StreamSegmenter(language="en", clean=False,
char_span=False, split_mode="balanced", buffering_mode="conservative") with feed(delta)->None,
get_completed_sentences()->list, pending_text()->str, is_complete()->bool, flush()->list, reset()->None. Tests
tests/test_stream_segmenter.py: streaming==non-streaming (feed(full)+flush() == segment(full)); abbreviation delays
(Dr.); decimal continuation (GPT 3. vs 3.1); char_span=True returns correct TextSpan offsets (reuse _match_spans);
conservative vs aggressive emit timing; all 24 languages with probes; clean=True disallows char_span (same
constraint as Segmenter); edge cases (empty/None/whitespace/very-long tail). Also benchmarks/
streaming_latency_benchmark.py and examples/streaming_to_tts_recipe.py. Optional max_buffer_size guard for
pathological unbounded tails.`,
  },
]

const GUARD = (it) => `GUARDRAILS (follow exactly):
- Work ENTIRELY inside the worktree at \`${it.wt}\` (branch \`${it.branch}\`, already created off \`${NOWBASE}\`).
  Run every command as \`cd ${it.wt} && <cmd>\`. Do NOT touch ${ROOT} or any other worktree. NEVER push. NEVER touch main.
- The detailed, pre-written spec for ${it.id} is in ${BACKLOG} (section "### ${it.id}"); strategy in ${PLAN}.
  READ the ${it.id} section of ${BACKLOG} first (absolute path — it is not inside the worktree).
- TEST-FIRST: write the test(s) before the implementation; confirm red first where it applies.
- Match surrounding style; ruff line length 127. Run \`uv run ruff format\` + \`uv run ruff check\` on changed files.
- Zero-dependency core is sacred: a bare \`import sentencesplit\` must import NO third-party module. Hypothesis (N5)
  goes in the dev dependency group ONLY. tests/test_zero_dependencies.py is present on this base and MUST stay green.
- First run \`uv sync --group dev\` in the worktree, then the FULL suite must stay green: \`${SUITE}\`.
- The N2 regression gate (tests/regression/test_regression_gate.py) is present and MUST stay green.
- Golden Rules must not regress: \`${GOLDEN}\` (count before vs after — must not decrease).
- COMMIT-OR-REVERT: if suite + gate + zero-dep test stay green AND Golden Rules did not regress, \`git add\` ONLY your
  changed files and commit on \`${it.branch}\` with a Conventional Commit subject. Otherwise revert fully and say so.`

// ── schemas ─────────────────────────────────────────────────────────────────────

const IMPLEMENT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['id', 'status', 'files_changed', 'test_files', 'suite_passed', 'gate_passed', 'golden_rules_before', 'golden_rules_after', 'commit', 'notes'],
  properties: {
    id: { type: 'string' },
    status: { type: 'string', enum: ['implemented', 'partial', 'reverted', 'error'] },
    files_changed: { type: 'array', items: { type: 'string' } },
    test_files: { type: 'array', items: { type: 'string' } },
    suite_passed: { type: 'boolean' },
    gate_passed: { type: 'boolean' },
    golden_rules_before: { type: ['integer', 'null'] },
    golden_rules_after: { type: ['integer', 'null'] },
    commit: { type: 'string' },
    notes: { type: 'string' },
  },
}

const INTEGRATE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['merged_branches', 'conflicts', 'suite_passed', 'gate_passed', 'golden_rules', 'notes'],
  properties: {
    merged_branches: { type: 'array', items: { type: 'string' } },
    conflicts: { type: 'string', description: 'how any merge conflicts were resolved, or "none"' },
    suite_passed: { type: 'boolean' },
    gate_passed: { type: 'boolean' },
    golden_rules: { type: 'string', description: 'e.g. "48/48"' },
    notes: { type: 'string' },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['dimension', 'findings'],
  properties: {
    dimension: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'item', 'severity', 'file', 'detail', 'suggestion'],
        properties: {
          title: { type: 'string' },
          item: { type: 'string', description: 'N1, N2, N5, N4, or cross-cutting' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
          file: { type: 'string', description: 'file:line or path' },
          detail: { type: 'string' },
          suggestion: { type: 'string' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['title', 'real', 'confidence', 'rationale'],
  properties: {
    title: { type: 'string' },
    real: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    rationale: { type: 'string' },
  },
}

// ── Phase 1: Setup ──────────────────────────────────────────────────────────────

phase('Setup')
log(`Worktrees ${ITEMS.map((i) => `${i.id}->${i.branch}`).join(', ')} off ${NOWBASE}`)
const setup = await agent(
  `Prepare isolated git worktrees for parallel implementation. In ${ROOT}:
1. \`git fetch origin\`; confirm branch \`${NOWBASE}\` exists (it carries N1+N2) and the suite is green there: \`${SUITE}\` (report the summary line only).
2. For EACH item, remove any stale worktree/branch of the same name (\`git worktree remove --force <path>\`; \`git branch -D <branch>\` if present), then create a fresh worktree on a NEW branch off \`${NOWBASE}\`:
   - \`git worktree add -b ${ITEMS[0].branch} ${ITEMS[0].wt} ${NOWBASE}\`
   - \`git worktree add -b ${ITEMS[1].branch} ${ITEMS[1].wt} ${NOWBASE}\`
3. Report \`git worktree list\`. Do NOT install deps or commit here. Keep output short.`,
  { label: 'worktree-setup', phase: 'Setup', agentType: 'general-purpose' },
)
log('Setup: ' + String(setup).split('\n').slice(-3).join(' ').slice(0, 220))

// ── Phase 2: Implement (parallel, isolated worktrees) ───────────────────────────

phase('Implement')
const built = await parallel(
  ITEMS.map((it) => () =>
    agent(
      `=== IMPLEMENT ${it.id}: ${it.title} ===\nSPEC (summary; authoritative detail in ${BACKLOG} section "### ${it.id}" — READ it):\n${it.spec}\n\n${GUARD(it)}\n\nImplement ${it.id} now, test-first, fully inside \`${it.wt}\`. Commit on \`${it.branch}\` (or revert) per the guardrails. Report status, files changed, test files, suite_passed, gate_passed, Golden Rules before/after, the commit hash (or ""), and concise notes (incl. any in-scope design call, e.g. N5's RTL-stripping decision).`,
      { label: `implement:${it.id}`, phase: 'Implement', schema: IMPLEMENT_SCHEMA, agentType: 'general-purpose' },
    ).then((r) => (r ? { ...r, id: it.id } : { id: it.id, status: 'error', files_changed: [], test_files: [], suite_passed: false, gate_passed: false, golden_rules_before: null, golden_rules_after: null, commit: '', notes: 'agent returned null' })),
  ),
).then((r) => r.filter(Boolean))

for (const b of built) log(`  [${b.status}] ${b.id} ${b.commit ? `(${b.commit.slice(0, 9)})` : ''} suite=${b.suite_passed} gate=${b.gate_passed}`)
const byId = {}
for (const it of ITEMS) byId[it.id] = it
const landed = built.filter((b) => (b.status === 'implemented' || b.status === 'partial') && b.commit)

// ── Phase 3: Integrate landed items into feat/now-all, then drop worktrees ───────

phase('Integrate')
const landedBranches = landed.map((b) => byId[b.id].branch)
const integrate = await agent(
  `Integrate all the work-so-far onto one branch for review. In ${ROOT}:
1. Recreate the integration branch: \`git branch -D ${ALLBRANCH}\` if it exists, then \`git checkout -b ${ALLBRANCH} ${NOWBASE}\` (so it starts as N1+N2).
2. Merge the landed item branches in: ${landedBranches.length ? landedBranches.map((b) => `\`git merge --no-edit ${b}\``).join(', ') : '(none landed — skip)'}. Resolve any conflict TRIVIALLY and conservatively — e.g. sentencesplit/__init__.py will have both the N1 \`list_languages\` export and the N4 \`StreamSegmenter\` export; keep BOTH. If a conflict is non-trivial, abort that merge, leave it out, and report it.
3. Verify the integration is green: \`${SUITE}\`, the gate (\`uv run pytest tests/regression/test_regression_gate.py -q\`), and Golden Rules (\`${GOLDEN}\`).
4. Remove the temporary worktrees (their branches persist): for each of ${ITEMS.map((i) => i.wt).join(', ')} run \`git worktree remove --force <path>\` then \`git worktree prune\`.
Leave ${ROOT} checked out on \`${ALLBRANCH}\`. Report which branches merged, how conflicts were resolved, suite/gate/golden results.`,
  { label: 'integrate', phase: 'Integrate', schema: INTEGRATE_SCHEMA, agentType: 'general-purpose' },
)
log(`Integrate: merged ${JSON.stringify(integrate.merged_branches)}; suite=${integrate.suite_passed} gate=${integrate.gate_passed} golden=${integrate.golden_rules}; conflicts=${integrate.conflicts}`)

// ── Phase 4: Review ALL work so far (origin/main..feat/now-all) ─────────────────

phase('Review')
const DIMENSIONS = [
  {
    key: 'correctness',
    focus: `Correctness & edge-case bugs across ALL items. N1: does list_languages() reflect the registry and import no
language module? N2: is the gate hermetic, does it actually fail on a per-language drop, are tolerances sane? N5: is
the round-trip ACTUALLY byte-for-byte (no whitespace swallowed/duplicated), do spans tile dirty input
(ZWSP/NBSP/BOM/combining/RTL) with no gaps/overlaps, did char_span deprecation change behavior? N4: does
feed()+flush() exactly equal segment(full)? off-by-one in delta merging / char_span offsets? premature emission?
unbounded buffer? Re-derive a couple of cases or run the relevant tests in ${ROOT} (now on ${ALLBRANCH}).`,
  },
  {
    key: 'api-dx',
    focus: `Public API & DX coherence across the whole surface: list_languages(), segment_spans() (now canonical) +
char_span deprecation, StreamSegmenter signature, keywords/classifiers. Are names/constraints (clean vs char_span)
consistent with Segmenter? Exports in __init__ correct and discoverable? docstrings/type hints/py.typed coherent?
Is the "Coming from pysbd" README accurate against the actual API?`,
  },
  {
    key: 'tests',
    focus: `Test quality across all items. Do the N5 Hypothesis property tests REALLY assert the invariant (not a
tautology) with sensible strategies across scripts + dirty input? Is N4 streaming==non-streaming exercised across
languages? Is the N2 gate's drop-detection meaningfully covered (coverage test present)? Is the N1 zero-dep test
robust? Any trivially-passing/skipped tests? Run suites in ${ROOT} to confirm green AND meaningful.`,
  },
  {
    key: 'zerodep-style',
    focus: `Zero-dependency discipline + style across everything. CONFIRM Hypothesis is dev-group ONLY and a bare
\`import sentencesplit\` imports zero third-party modules (inspect pyproject diff + run tests/test_zero_dependencies.py
in ${ROOT}). ruff clean (format + check) on the full diff, line length 127, naming conventions, no dead code, no
perf footguns (e.g. per-char O(n^2) in StreamSegmenter).`,
  },
]

const reviews = await pipeline(
  DIMENSIONS,
  (d) =>
    agent(
      `You are reviewing ALL the work done so far on the way to the LEVEL_UP_PLAN. Everything is integrated on branch \`${ALLBRANCH}\` in ${ROOT} (currently checked out). Review the cumulative diff vs origin/main.\n\n${MANIFEST}\n\nRead the full diff: \`git -C ${ROOT} diff ${ORIGIN}..${ALLBRANCH}\` (and per-item: \`git -C ${ROOT} diff ${ORIGIN}..<branch>\`). You MAY run tests in ${ROOT} (it's on ${ALLBRANCH} with a synced .venv).\n\n=== YOUR REVIEW LENS: ${d.key} ===\n${d.focus}\n\nReport concrete findings only — each with the item (N1/N2/N5/N4/cross-cutting), severity, file:line, what's wrong + evidence, and a fix. An empty findings list is a valid, good outcome — do not invent issues.`,
      { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS_SCHEMA, agentType: 'general-purpose' },
    ),
  (review, d) =>
    parallel(
      (review.findings || []).map((f) => () =>
        agent(
          `Adversarially verify this code-review finding against the actual code on \`${ALLBRANCH}\` in ${ROOT}. Try to REFUTE it — default real=false if speculative, already handled, a non-issue, or unsupported by the code.\n\nFINDING (${f.severity}, ${f.item}): ${f.title}\nFile: ${f.file}\nDetail: ${f.detail}\nSuggestion: ${f.suggestion}\n\nRead the cited code (run the relevant test if it settles it). Return whether it is a genuine issue that survives scrutiny.`,
          { label: `verify:${d.key}:${(f.title || '').slice(0, 22)}`, phase: 'Verify', schema: VERDICT_SCHEMA, agentType: 'general-purpose' },
        ).then((v) => ({ ...f, dimension: d.key, verdict: v })),
      ),
    ).then((arr) => arr.filter(Boolean)),
)

const allFindings = reviews.flat().filter(Boolean)
const confirmed = allFindings.filter((f) => f.verdict && f.verdict.real)
const sevRank = { blocker: 0, major: 1, minor: 2, nit: 3 }
confirmed.sort((a, b) => (sevRank[a.severity] ?? 9) - (sevRank[b.severity] ?? 9))
log(`Review: ${allFindings.length} raw findings, ${confirmed.length} confirmed (severity: ${confirmed.map((f) => f.severity).join(',') || 'none'})`)

// ── Phase 5: Report ──────────────────────────────────────────────────────────────

phase('Report')
const report = await agent(
  `Write ${ROOT}/analysis/REVIEW_NOW.md — a review of ALL the work done so far toward the LEVEL_UP_PLAN (N1+N2+N5+N4), integrated on branch \`${ALLBRANCH}\` (vs ${ORIGIN}).\n\n${MANIFEST}\n\nImplementation (this run): ${JSON.stringify(built.map((b) => ({ id: b.id, status: b.status, commit: b.commit, branch: byId[b.id].branch, suite: b.suite_passed, gate: b.gate_passed, golden: [b.golden_rules_before, b.golden_rules_after], notes: b.notes })))}\nIntegration: ${JSON.stringify(integrate)}\nConfirmed findings (survived adversarial verification, severity-ordered): ${JSON.stringify(confirmed.map((f) => ({ item: f.item, severity: f.severity, dimension: f.dimension, title: f.title, file: f.file, detail: f.detail, suggestion: f.suggestion, confidence: f.verdict.confidence })))}\nRaw findings raised: ${allFindings.length}; refuted during verification: ${allFindings.length - confirmed.length}.\n\nSections: 1. **Summary** — what is on ${ALLBRANCH} (the four items + commits), integration suite/gate/Golden-Rules status, and the headline verdict (ship / fix-then-ship / blocked). 2. **Confirmed findings** — a table (item | severity | dimension | file | issue | fix), then a sentence each on blockers/majors. 3. **By item** — N1, N2, N5, N4: state + any design calls (e.g. N5 RTL-stripping, N4 buffering). 4. **Adversarial filter** — note that ${allFindings.length - confirmed.length} of ${allFindings.length} raised findings were refuted as non-issues. 5. **Next steps** — per-branch merge recommendation, what to fix first, and the reminder that everything stacks toward ${ALLBRANCH} and nothing is pushed.\n\nReturn a 6-10 line plain-text executive summary.`,
  { label: 'write-review-report', phase: 'Report', agentType: 'general-purpose' },
)
log('Review report written to analysis/REVIEW_NOW.md')

return {
  base: NOWBASE,
  integration_branch: ALLBRANCH,
  implemented: built.map((b) => ({ id: b.id, status: b.status, branch: byId[b.id].branch, commit: b.commit })),
  integration: { merged: integrate.merged_branches, suite_passed: integrate.suite_passed, gate_passed: integrate.gate_passed, golden_rules: integrate.golden_rules },
  review: { raw_findings: allFindings.length, confirmed: confirmed.length, blockers: confirmed.filter((f) => f.severity === 'blocker').length, majors: confirmed.filter((f) => f.severity === 'major').length },
  artifacts: { review: 'analysis/REVIEW_NOW.md' },
  executive_summary: report,
}
