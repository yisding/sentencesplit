export const meta = {
  name: 'improve-sentencesplit',
  description: 'Use the cross-library comparison verdicts to fix sentencesplit: triage verified losses into fix clusters, apply each on an isolated branch (regression test first, auto-revert if the suite or Golden Rules regress), then re-benchmark and report the before/after delta',
  whenToUse: 'After running compare-segmenters, to turn the adjudicated losses into actual code fixes (with tests) on a feature branch, guarded against regressions.',
  phases: [
    { title: 'Triage', detail: 'cluster the adjudicated sentencesplit losses into actionable, low->high risk fix groups' },
    { title: 'Setup', detail: 'create the feature branch and snapshot the baseline scoreboard' },
    { title: 'Fix', detail: 'sequentially apply each cluster: regression test first, minimal fix, full suite + Golden Rules guard, commit or revert' },
    { title: 'Verify', detail: 're-run the benchmark and confirm the objective scoreboard improved with no regressions' },
    { title: 'Report', detail: 'summarize fixes, before/after deltas, and the branch left for review' },
  ],
}

const ROOT = process.env.SENTENCESPLIT_ROOT || process.cwd()
const CC = `${ROOT}/benchmarks/corpus_compare`
const RESULTS = `${CC}/results`
// Robust arg parsing (workflow `args` may arrive as a JSON string).
let opts = {}
try { opts = typeof args === 'string' ? JSON.parse(args) : (args || {}) } catch { opts = {} }
const BRANCH = opts.branch || 'improve/sbd-from-comparison'
const MAX_RISK = opts.max_risk || 'high' // include clusters up to this risk
const RISK_ORDER = { low: 0, medium: 1, high: 2 }

// ── schemas ───────────────────────────────────────────────────────────────────

const CLUSTERS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['clusters', 'excluded_as_artifacts'],
  properties: {
    excluded_as_artifacts: {
      type: 'integer',
      description: 'count of incorrect cases deliberately NOT turned into fixes (corpus annotation artifacts, e.g. UD colon-as-boundary)',
    },
    clusters: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'title', 'category', 'risk', 'root_cause', 'target_hint', 'fix_strategy', 'cases'],
        properties: {
          id: { type: 'string', description: 'short kebab id, e.g. "trailing-zwsp"' },
          title: { type: 'string' },
          category: { type: 'string' },
          risk: { type: 'string', enum: ['low', 'medium', 'high'] },
          root_cause: { type: 'string' },
          target_hint: { type: 'string', description: 'likely files/functions to change (e.g. processor.split_into_segments, lang/greek.py abbreviations)' },
          fix_strategy: { type: 'string' },
          cases: {
            type: 'array',
            items: {
              type: 'object',
              additionalProperties: false,
              required: ['case_id', 'language', 'input', 'expected', 'current_output'],
              properties: {
                case_id: { type: 'string' },
                language: { type: 'string' },
                input: { type: 'string', description: 'the exact passage that segmented wrong' },
                expected: { type: 'array', items: { type: 'string' }, description: 'gold (or linguistically-correct) segmentation' },
                current_output: { type: 'array', items: { type: 'string' }, description: 'what sentencesplit currently produces' },
              },
            },
          },
        },
      },
    },
  },
}

const FIX_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['id', 'title', 'status', 'files_changed', 'test_file', 'cases_targeted', 'cases_fixed', 'suite_passed', 'golden_rules_before', 'golden_rules_after', 'commit', 'notes'],
  properties: {
    id: { type: 'string' },
    title: { type: 'string' },
    status: { type: 'string', enum: ['applied', 'skipped_regressed', 'skipped_no_safe_fix', 'error'] },
    files_changed: { type: 'array', items: { type: 'string' } },
    test_file: { type: 'string' },
    cases_targeted: { type: 'integer' },
    cases_fixed: { type: 'integer' },
    suite_passed: { type: 'boolean' },
    golden_rules_before: { type: ['integer', 'null'] },
    golden_rules_after: { type: ['integer', 'null'] },
    commit: { type: 'string', description: 'commit hash if applied, else ""' },
    notes: { type: 'string' },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['scoreboard_after', 'ss_exact_before', 'ss_exact_after', 'ss_bf1_before', 'ss_bf1_after', 'regressions_detected', 'notes'],
  properties: {
    scoreboard_after: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['name', 'exact_match', 'boundary_f1', 'n'],
        properties: { name: { type: 'string' }, exact_match: { type: ['number', 'null'] }, boundary_f1: { type: ['number', 'null'] }, n: { type: 'integer' } },
      },
    },
    ss_exact_before: { type: ['number', 'null'] },
    ss_exact_after: { type: ['number', 'null'] },
    ss_bf1_before: { type: ['number', 'null'] },
    ss_bf1_after: { type: ['number', 'null'] },
    regressions_detected: { type: 'boolean' },
    notes: { type: 'string' },
  },
}

// ── Phase 1: triage the verified losses into fix clusters ──────────────────────

phase('Triage')
const triage = await agent(
  `Triage sentencesplit's adjudicated losses from the cross-library comparison into actionable fix clusters.

Read:
- ${RESULTS}/verdicts.json — find every verdict where "sentencesplit_assessment" == "incorrect".
- For each such verdict, open the matching case file ${RESULTS}/cases/<case_id>.json to get the exact "text", every tool's "outputs", and "gold".
- ${RESULTS}/REPORT.md — the "Where sentencesplit Loses" and "Patterns & Recommendations" sections already analyze these; use them.

Produce fix CLUSTERS, grouping losses that share a single root cause and code fix. For each cluster give a short id, title, category, a risk rating (low/medium/high — how likely a fix is to regress other behavior), the root_cause, a target_hint (which files/functions in sentencesplit/ likely need changing — actually look at the code to confirm), a fix_strategy, and the concrete cases (case_id, language, input text, expected/gold segmentation, current sentencesplit output).

IMPORTANT — do NOT create clusters for corpus *annotation artifacts* that are not real sentence boundaries (e.g. UD treebanks splitting on a colon, or colon-introduced list fragments, or "none_correct" cases where gold itself is questionable). Count those in excluded_as_artifacts instead. Only cluster losses where fixing sentencesplit would genuinely improve real-world segmentation.

Order clusters low-risk first. Expected clusters (from the report) include: trailing zero-width-space phantom fragment; multi-bang (!!!/???) terminator before a capital; missing Greek/Russian abbreviations (m.Ch., p.Ch., E.E., Sr., angl./nem./fr.) and CO.; German ordinal-before-noun; multi-sentence quotation interior splits (highest risk). Confirm/adjust against the actual data and code.`,
  { label: 'triage-losses', phase: 'Triage', schema: CLUSTERS_SCHEMA },
)

let clusters = (triage.clusters || []).filter((c) => RISK_ORDER[c.risk] <= RISK_ORDER[MAX_RISK])
clusters.sort((a, b) => RISK_ORDER[a.risk] - RISK_ORDER[b.risk])
log(`Triage: ${clusters.length} fix clusters (risk<=${MAX_RISK}); ${triage.excluded_as_artifacts} losses skipped as annotation artifacts.`)
if (!clusters.length) {
  return { error: 'no actionable clusters found', triage }
}

// ── Phase 2: create the feature branch + snapshot baseline ─────────────────────

phase('Setup')
const setup = await agent(
  `Prepare an isolated branch for sentencesplit fixes. Run, in ${ROOT}:
1. \`git rev-parse --abbrev-ref HEAD\` to note the current branch.
2. Create and switch to branch \`${BRANCH}\` (if it already exists, check it out and report that). Do NOT commit anything yet. Leave untracked files (the benchmark harness) as-is.
3. Snapshot the baseline scoreboard: \`cp ${RESULTS}/scoreboard.json ${RESULTS}/scoreboard.baseline.json\`.
4. Confirm the test suite is green BEFORE any changes: \`uv run pytest -q\` (report pass/fail summary line only).
Report the starting branch, that ${BRANCH} is checked out, and the baseline pytest result. Keep output short.`,
  { label: 'branch-setup', phase: 'Setup' },
)
log('Setup: ' + setup.split('\n').slice(-3).join(' ').slice(0, 200))

// ── Phase 3: apply each cluster SEQUENTIALLY (avoids file conflicts) ────────────

phase('Fix')
const fixes = []
for (const c of clusters) {
  const r = await agent(
    `Fix one cluster of sentencesplit bugs on branch \`${BRANCH}\` (already checked out). Work in ${ROOT}.

CLUSTER: ${c.title}  (id=${c.id}, risk=${c.risk}, category=${c.category})
Root cause: ${c.root_cause}
Suggested target: ${c.target_hint}
Strategy: ${c.fix_strategy}
Failing cases (input -> expected vs current):
${JSON.stringify(c.cases, null, 2)}

Follow the repo's CONTRIBUTING/CLAUDE.md rules:
1. FIRST write a regression test in tests/regression/ (extend tests/regression/test_issues.py or add a file) that asserts the expected segmentation for these inputs. Confirm it FAILS (red).
2. Make the MINIMAL, targeted code change to fix the root cause. Match surrounding style. Do not over-reach beyond this cluster.
3. Run the new test (should pass), then \`uv run ruff format\` + \`uv run ruff check\` on changed files, then the FULL suite: \`uv run pytest -q\`.
4. GUARDRAIL — measure the English Golden Rules score before/after with:
   \`uv run python -c "import sys; sys.path.insert(0,'benchmarks'); from english_golden_rules import GOLDEN_EN_RULES as G; import sentencesplit as s; seg=s.Segmenter(language='en'); print(sum(1 for t,e in G if [x.strip() for x in seg.segment(t)]==e), len(G))"\`
   (run it on the baseline first if needed via git stash, or reason from the known baseline). The Golden Rules pass count MUST NOT decrease and the full suite MUST stay green.
5. DECISION:
   - If the suite stays green AND Golden Rules did not regress AND at least one target case is fixed: \`git add\` ONLY the files you changed (code + test), commit with a Conventional Commit message (\`fix(<lang/scope>): ...\`), status="applied".
   - If you cannot fix it without regressing the suite or Golden Rules: \`git checkout -- <your changed files>\` and remove any new test file to fully revert, status="skipped_regressed".
   - If there is no safe minimal fix: revert everything, status="skipped_no_safe_fix".

Report cases_targeted, how many of them are now fixed (cases_fixed), suite_passed, golden_rules_before/after counts, the commit hash (or ""), the files changed, and concise notes. NEVER push. NEVER touch main.`,
    { label: `fix:${c.id}`, phase: 'Fix', schema: FIX_SCHEMA },
  )
  if (r) fixes.push(r)
  log(`  [${r ? r.status : 'null'}] ${c.title}` + (r && r.status === 'applied' ? ` (fixed ${r.cases_fixed}/${r.cases_targeted})` : ''))
}

const applied = fixes.filter((f) => f.status === 'applied')
log(`Fix phase: ${applied.length}/${fixes.length} clusters applied.`)

// ── Phase 4: re-benchmark and verify no regression ─────────────────────────────

phase('Verify')
const verify = await agent(
  `Verify the sentencesplit fixes on branch \`${BRANCH}\` improved the objective metrics without regressing.

1. Re-run the comparison harness: \`cd ${CC} && uv run python run_compare.py --cap 1\` (cap low — we only need the recomputed scoreboard, not new cases).
2. Read the NEW ${RESULTS}/scoreboard.json and the BASELINE ${RESULTS}/scoreboard.baseline.json.
3. Compare gold_scores.overall for "sentencesplit": report exact_match and boundary_f1 before vs after, and the full after-scoreboard (one row per available segmenter).
4. Also confirm \`uv run pytest -q\` is still green on the branch.
5. Set regressions_detected=true if sentencesplit's overall exact_match OR boundary_f1 dropped vs baseline, or if any test fails; else false. Explain any movement (which fixes drove the gains, any per-language trade-offs) in notes.

Be adversarial: if a metric went DOWN, say so plainly.`,
  { label: 'verify-improvement', phase: 'Verify', schema: VERIFY_SCHEMA },
)
log(`Verify: sentencesplit exact ${verify.ss_exact_before}->${verify.ss_exact_after}, bF1 ${verify.ss_bf1_before}->${verify.ss_bf1_after}, regressions=${verify.regressions_detected}`)

// ── Phase 5: report ────────────────────────────────────────────────────────────

phase('Report')
const summary = await agent(
  `Write ${RESULTS}/IMPROVEMENTS.md — a concise report of the sentencesplit improvement pass driven by the comparison verdicts.

Data:
- Branch: ${BRANCH}
- Fix results (per cluster): ${JSON.stringify(fixes)}
- Verification (before/after): ${JSON.stringify(verify)}
- Clusters skipped as annotation artifacts: ${triage.excluded_as_artifacts}

Sections:
1. **Summary** — branch name, how many fix clusters applied vs skipped, and the headline objective delta (sentencesplit exact-match and boundary-F1 before->after).
2. **Fixes applied** — a table: cluster | category | files changed | test added | cases fixed | commit. Then 1-3 sentences each on what the fix did.
3. **Skipped / deferred** — clusters that were skipped (regressed or no safe fix) and why; note that UD colon-boundary annotation artifacts were intentionally not chased.
4. **Verification** — the after-scoreboard table, the per-language trade-offs from verify.notes, and confirmation the full test suite is green.
5. **Next steps** — what remains (e.g. the high-risk multi-sentence quotation rework if it was skipped) and the suggestion to review/merge branch ${BRANCH}.

Then return a 6-10 line plain-text executive summary including the metric delta, the applied-fix count, and the branch name. Do NOT merge or push.`,
  { label: 'write-improvements-report', phase: 'Report' },
)
log('Report written to benchmarks/corpus_compare/results/IMPROVEMENTS.md')

return {
  branch: BRANCH,
  clusters_total: clusters.length,
  applied: applied.map((f) => ({ id: f.id, cases_fixed: f.cases_fixed, commit: f.commit })),
  skipped: fixes.filter((f) => f.status !== 'applied').map((f) => ({ id: f.id, status: f.status })),
  metric_delta: {
    exact_match: [verify.ss_exact_before, verify.ss_exact_after],
    boundary_f1: [verify.ss_bf1_before, verify.ss_bf1_after],
    regressions_detected: verify.regressions_detected,
  },
  report: `${RESULTS}/IMPROVEMENTS.md`,
  summary,
}
