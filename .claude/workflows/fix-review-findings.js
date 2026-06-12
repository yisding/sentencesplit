export const meta = {
  name: 'fix-review-findings',
  description: 'Fix the adversarially-verified findings from the N1+N2+N5+N4 review on branch feat/now-all: triage into mechanical-fix vs needs-decision, apply each mechanical cluster test-first with a full-suite + N2-gate + zero-dep + Golden-Rules guard (commit-or-revert), then re-verify and report',
  whenToUse: 'After parallel-implement-review writes analysis/REVIEW_NOW.md. Pass args.findings (the confirmed findings array from the review result); if omitted, a triage agent reads REVIEW_NOW.md. Applies fixes on feat/now-all. Never pushes.',
  phases: [
    { title: 'Setup', detail: 'checkout feat/now-all, confirm green baseline (suite + gate + zero-dep + Golden Rules)' },
    { title: 'Triage', detail: 'cluster verified findings by root cause; classify mechanical-fix vs needs-decision; order low-risk first' },
    { title: 'Fix', detail: 'apply each mechanical cluster sequentially: test-first, minimal fix, guard, commit or revert' },
    { title: 'Verify', detail: 'full suite + gate green; confirm each targeted finding resolved; adversarial sanity' },
    { title: 'Report', detail: 'write the fix report: fixed clusters, deferred needs-decision items, branch state' },
  ],
}

const ROOT = process.env.SENTENCESPLIT_ROOT || process.cwd()
const REVIEW = `${ROOT}/analysis/REVIEW_NOW.md`
const BRANCH = 'feat/now-all' // the integration of all work so far; fixes land here

let opts = {}
try {
  opts = typeof args === 'string' ? JSON.parse(args) : args || {}
} catch {
  opts = {}
}
const FINDINGS = Array.isArray(opts.findings) ? opts.findings : Array.isArray(opts) ? opts : null

const SUITE = `uv run pytest -q --ignore=tests/test_spacy_component.py` // spaCy import SIGILLs on this aarch64 box
const GATE = `uv run pytest tests/regression/test_regression_gate.py -q`
const GOLDEN = `uv run python -c "import sys; sys.path.insert(0,'benchmarks'); from english_golden_rules import GOLDEN_EN_RULES as G; import sentencesplit as s; seg=s.Segmenter(language='en'); print(sum(1 for t,e in G if [x.strip() for x in seg.segment(t)]==e), len(G))"`

const CONTEXT = `PROJECT: sentencesplit — rule-based SBD, 24 languages, pure Python, ZERO runtime deps, Python 3.11+. Repo root: ${ROOT}.
Branch \`${BRANCH}\` integrates all work so far: N1 (list_languages + metadata + tests/test_zero_dependencies.py),
N2 (hermetic regression gate at tests/regression/test_regression_gate.py + tests/regression/gate/*), N5
(segment_spans byte-for-byte round-trip + Hypothesis property tests, char_span deprecated), N4
(sentencesplit/stream_segmenter.py StreamSegmenter). Review report: ${REVIEW}. Roadmap: ${ROOT}/analysis/ROADMAP_EXECUTION.md.`

const GUARD = `GUARDRAILS (follow exactly):
- Work in ${ROOT} on the already-checked-out branch \`${BRANCH}\`. NEVER push. NEVER touch main/origin.
- TEST-FIRST for any behavior bug: add/extend a regression test that fails (red) before the fix, then make it pass.
- Match surrounding style; ruff line length 127. Run \`uv run ruff format\` + \`uv run ruff check\` on changed files.
- Zero-dependency core is sacred: a bare \`import sentencesplit\` imports NO third-party module; Hypothesis stays in the
  dev group only. tests/test_zero_dependencies.py MUST stay green.
- FULL SUITE green: \`${SUITE}\`. N2 GATE green: \`${GATE}\`. Golden Rules must not regress: \`${GOLDEN}\`.
- COMMIT-OR-REVERT per cluster: if all guards pass, \`git add\` ONLY the files you changed and commit with a
  Conventional Commit subject (\`fix(...)\`, \`refactor(...)\`, etc.). Otherwise \`git checkout -- <files>\`, delete any
  new files, and report the cluster as skipped.`

// ── schemas ─────────────────────────────────────────────────────────────────────

const CLUSTERS_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['clusters', 'deferred'],
  properties: {
    clusters: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['id', 'title', 'risk', 'root_cause', 'target_files', 'fix_strategy', 'finding_titles'],
        properties: {
          id: { type: 'string', description: 'short kebab id' },
          title: { type: 'string' },
          risk: { type: 'string', enum: ['low', 'medium', 'high'] },
          root_cause: { type: 'string' },
          target_files: { type: 'array', items: { type: 'string' } },
          fix_strategy: { type: 'string' },
          finding_titles: { type: 'array', items: { type: 'string' }, description: 'the verified findings this cluster resolves' },
        },
      },
    },
    deferred: {
      type: 'array',
      description: 'findings that require a product/API judgment call, NOT a mechanical fix',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'why_deferred', 'decision_needed'],
        properties: {
          title: { type: 'string' },
          why_deferred: { type: 'string' },
          decision_needed: { type: 'string', description: 'the specific question for the human' },
        },
      },
    },
  },
}

const FIX_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['id', 'status', 'files_changed', 'test_added', 'suite_passed', 'gate_passed', 'golden_rules', 'commit', 'notes'],
  properties: {
    id: { type: 'string' },
    status: { type: 'string', enum: ['fixed', 'skipped_regressed', 'skipped_no_safe_fix', 'error'] },
    files_changed: { type: 'array', items: { type: 'string' } },
    test_added: { type: 'string' },
    suite_passed: { type: 'boolean' },
    gate_passed: { type: 'boolean' },
    golden_rules: { type: 'string' },
    commit: { type: 'string' },
    notes: { type: 'string' },
  },
}

const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['suite_green', 'gate_green', 'zero_dep_green', 'golden_rules', 'unresolved', 'notes'],
  properties: {
    suite_green: { type: 'boolean' },
    gate_green: { type: 'boolean' },
    zero_dep_green: { type: 'boolean' },
    golden_rules: { type: 'string' },
    unresolved: { type: 'array', items: { type: 'string' }, description: 'targeted findings NOT actually resolved' },
    notes: { type: 'string' },
  },
}

// ── Phase 1: Setup ──────────────────────────────────────────────────────────────

phase('Setup')
const setup = await agent(
  `${CONTEXT}\n\nPrepare to fix review findings. In ${ROOT}:
1. \`git checkout ${BRANCH}\` (it must exist — it's the review integration branch). Report \`git log --oneline -6\`.
2. Confirm a GREEN baseline before any fix: \`${SUITE}\`, then \`${GATE}\`, then Golden Rules \`${GOLDEN}\`.
Report the three results (suite summary line, gate summary line, Golden Rules count). Do NOT change anything.`,
  { label: 'fix-setup', phase: 'Setup', agentType: 'general-purpose' },
)
log('Setup: ' + String(setup).split('\n').slice(-3).join(' ').slice(0, 220))

// ── Phase 2: Triage the verified findings into fix clusters ─────────────────────

phase('Triage')
const findingsBlock = FINDINGS
  ? `The verified findings (passed in) are:\n${JSON.stringify(FINDINGS, null, 2)}`
  : `No findings were passed in — READ ${REVIEW} and extract the CONFIRMED findings table (ignore the refuted ones).`

const triage = await agent(
  `${CONTEXT}\n\n=== TRIAGE ===\n${findingsBlock}\n\nGroup the verified findings into fix CLUSTERS that share a root cause / code area (so each can be fixed and committed without conflicting with another). For each cluster: a short id, title, risk (low/medium/high = chance the fix regresses other behavior), the root_cause (confirm by reading the actual code on \`${BRANCH}\`), the target_files, a concrete fix_strategy, and the finding titles it resolves. Order clusters low-risk first.\n\nSeparately, put any finding that is NOT a mechanical fix — i.e. it needs a product/API judgment call (e.g. "should char_span be removed vs deprecated", "what should the default buffering be") — into \`deferred\` with the specific decision the human must make. Do NOT guess on those.\n\nRead the cited code to confirm each root cause before clustering.`,
  { label: 'triage-findings', phase: 'Triage', schema: CLUSTERS_SCHEMA, agentType: 'general-purpose' },
)

const RISK = { low: 0, medium: 1, high: 2 }
const clusters = (triage.clusters || []).sort((a, b) => (RISK[a.risk] ?? 9) - (RISK[b.risk] ?? 9))
log(`Triage: ${clusters.length} fix clusters; ${(triage.deferred || []).length} deferred (need a decision)`)
if (!clusters.length) {
  phase('Report')
  const note = await agent(
    `${CONTEXT}\n\nNo mechanical fix clusters were produced (deferred: ${JSON.stringify(triage.deferred || [])}). Append a short "## Fix pass" section to ${REVIEW} stating that no mechanical fixes were applied and listing any deferred decisions. Return a 3-5 line summary.`,
    { label: 'report-nothing-to-fix', phase: 'Report', agentType: 'general-purpose' },
  )
  return { branch: BRANCH, fixed: [], deferred: triage.deferred || [], note }
}

// ── Phase 3: Apply each cluster SEQUENTIALLY (single branch/tree → no conflicts) ─

phase('Fix')
const fixes = []
for (const c of clusters) {
  const r = await agent(
    `${CONTEXT}\n\n=== FIX CLUSTER: ${c.title} (id=${c.id}, risk=${c.risk}) ===\nRoot cause: ${c.root_cause}\nTarget files: ${JSON.stringify(c.target_files)}\nStrategy: ${c.fix_strategy}\nResolves findings: ${JSON.stringify(c.finding_titles)}\n\n${GUARD}\n\nApply the MINIMAL fix for this cluster only — do not refactor beyond it. For a behavior bug, add the regression test FIRST (confirm red), then fix. Then run ruff on changed files, the full suite, the gate, and Golden Rules. Commit (or revert) per the guardrails. Report status, files changed, the test added (or ""), suite_passed, gate_passed, golden_rules count, commit hash (or ""), and notes.`,
    { label: `fix:${c.id}`, phase: 'Fix', schema: FIX_SCHEMA, agentType: 'general-purpose' },
  )
  if (r) fixes.push({ ...r, id: c.id })
  log(`  [${r ? r.status : 'null'}] ${c.id} ${c.title}${r && r.commit ? ` (${r.commit.slice(0, 9)})` : ''}`)
}
const applied = fixes.filter((f) => f.status === 'fixed')
log(`Fix: ${applied.length}/${fixes.length} clusters applied`)

// ── Phase 4: Verify the whole thing is still green and findings are resolved ─────

phase('Verify')
const verify = await agent(
  `${CONTEXT}\n\n=== VERIFY (post-fix) ===\nClusters applied: ${JSON.stringify(applied.map((f) => ({ id: f.id, commit: f.commit })))}\nFinding titles that were targeted: ${JSON.stringify(clusters.flatMap((c) => c.finding_titles))}\n\nOn branch \`${BRANCH}\` in ${ROOT}: run the FULL suite \`${SUITE}\`, the gate \`${GATE}\`, the zero-dep test \`uv run pytest tests/regression/test_zero_dependencies.py -q\` (path is tests/test_zero_dependencies.py), and Golden Rules \`${GOLDEN}\`. Then, for each targeted finding, confirm it is ACTUALLY resolved in the current code (read the relevant code). Be adversarial: list any finding that is NOT genuinely resolved in \`unresolved\`. Leave the tree clean.`,
  { label: 'verify-fixes', phase: 'Verify', schema: VERIFY_SCHEMA, agentType: 'general-purpose' },
)
log(`Verify: suite=${verify.suite_green} gate=${verify.gate_green} zero-dep=${verify.zero_dep_green} golden=${verify.golden_rules} unresolved=${(verify.unresolved || []).length}`)

// ── Phase 5: Report ──────────────────────────────────────────────────────────────

phase('Report')
const report = await agent(
  `${CONTEXT}\n\nAppend a "## Fix pass" section to ${REVIEW} (and also write a standalone ${ROOT}/analysis/REVIEW_NOW_FIXES.md with the same content).\n\nData:\n- Branch: ${BRANCH}\n- Fix clusters (per cluster result): ${JSON.stringify(fixes)}\n- Deferred (need a human decision): ${JSON.stringify(triage.deferred || [])}\n- Post-fix verification: ${JSON.stringify(verify)}\n\nSections: 1. **Summary** — clusters applied vs skipped, post-fix suite/gate/zero-dep/Golden-Rules status, and whether any targeted finding is still unresolved. 2. **Fixes applied** — table: cluster | risk | files | test added | commit, then a sentence each. 3. **Skipped** — clusters that regressed or had no safe fix, and why. 4. **Deferred decisions** — the needs-decision findings, each with the specific question for the user (these were NOT auto-fixed). 5. **Next steps** — branch state and the reminder that nothing is pushed. Return a 6-10 line plain-text executive summary.`,
  { label: 'write-fix-report', phase: 'Report', agentType: 'general-purpose' },
)
log('Fix report written to analysis/REVIEW_NOW_FIXES.md (+ appended to REVIEW_NOW.md)')

return {
  branch: BRANCH,
  clusters_total: clusters.length,
  applied: applied.map((f) => ({ id: f.id, commit: f.commit })),
  skipped: fixes.filter((f) => f.status !== 'fixed').map((f) => ({ id: f.id, status: f.status })),
  deferred: triage.deferred || [],
  post_fix: { suite_green: verify.suite_green, gate_green: verify.gate_green, zero_dep_green: verify.zero_dep_green, golden_rules: verify.golden_rules, unresolved: verify.unresolved || [] },
  artifacts: { fix_report: 'analysis/REVIEW_NOW_FIXES.md' },
  executive_summary: report,
}
