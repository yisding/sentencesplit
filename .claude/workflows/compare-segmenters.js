export const meta = {
  name: 'compare-segmenters',
  description: 'Benchmark sentencesplit vs punkt/pysbd/pragmatic_segmenter/syntok on public corpora, then have one judge adjudicate each divergence and synthesize a report',
  whenToUse: 'Compare this library against other sentence boundary detection libraries on public corpora and get a winner + rationale for every case where they disagree.',
  phases: [
    { title: 'Benchmark', detail: 'run the deterministic harness: segment all corpus units, score vs gold, emit divergence cases' },
    { title: 'Adjudicate', detail: 'one judge agent per divergence picks a winner and writes a note explaining why' },
    { title: 'Report', detail: 'synthesize the scoreboard + verdicts into a comparison report' },
  ],
}

const ROOT = '/home/yi/Code/sentencesplit'
const CC = `${ROOT}/benchmarks/corpus_compare`
const CAP = (args && args.cap) || 120

// ── schemas ───────────────────────────────────────────────────────────────────

const BENCH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['available', 'excluded', 'scoreboard_overall', 'total_divergences', 'emitted_cases', 'dropped', 'cases'],
  properties: {
    available: { type: 'array', items: { type: 'string' } },
    excluded: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['name', 'reason'],
        properties: { name: { type: 'string' }, reason: { type: 'string' } },
      },
    },
    scoreboard_overall: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['name', 'exact_match', 'boundary_f1', 'n'],
        properties: {
          name: { type: 'string' },
          exact_match: { type: ['number', 'null'] },
          boundary_f1: { type: ['number', 'null'] },
          n: { type: 'integer' },
        },
      },
    },
    total_divergences: { type: 'integer' },
    emitted_cases: { type: 'integer' },
    dropped: { type: 'integer' },
    cases: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['id', 'path', 'corpus', 'language', 'n_distinct', 'has_gold', 'sentencesplit_is_odd_one_out'],
        properties: {
          id: { type: 'string' },
          path: { type: 'string' },
          corpus: { type: 'string' },
          language: { type: 'string' },
          n_distinct: { type: 'integer' },
          has_gold: { type: 'boolean' },
          sentencesplit_is_odd_one_out: { type: 'boolean' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['case_id', 'corpus', 'language', 'winner', 'winners', 'ranking', 'category', 'reason', 'severity', 'confidence', 'sentencesplit_assessment'],
  properties: {
    case_id: { type: 'string' },
    corpus: { type: 'string' },
    language: { type: 'string' },
    winner: { type: 'string', description: 'best segmenter name, or "tie", or "none_correct"' },
    winners: { type: 'array', items: { type: 'string' }, description: 'all segmenters tied for best (the correct segmentation)' },
    ranking: { type: 'array', items: { type: 'string' }, description: 'distinct segmentations best->worst, named by a representative tool' },
    category: {
      type: 'string',
      enum: ['abbreviation', 'decimal_or_number', 'list_item_or_numbering', 'quotation', 'parenthetical', 'ellipsis', 'header_or_title', 'url_or_email', 'initials_or_name', 'over_split', 'under_split', 'whitespace_or_formatting', 'other'],
    },
    reason: { type: 'string', description: 'the NOTE: concrete, specific explanation of why the winner is correct and the losers are wrong (cite the exact token/boundary)' },
    severity: { type: 'string', enum: ['trivial', 'minor', 'major'] },
    confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
    sentencesplit_assessment: { type: 'string', enum: ['correct', 'incorrect', 'tied', 'not_applicable'] },
  },
}

// ── Phase 1: run the deterministic benchmark ───────────────────────────────────

phase('Benchmark')
const bench = await agent(
  `Run the sentence-boundary comparison harness, then report its results.

Steps (run exactly):
1. \`cd ${CC} && uv run python run_compare.py --cap ${CAP}\`  (corpora are cached; this re-segments + re-detects divergences, ~30-60s)
2. Read \`${CC}/results/scoreboard.json\` and \`${CC}/results/divergences.json\`.

Return (via the structured output tool):
- available: the available segmenter names (scoreboard.segmenters where available==true).
- excluded: [{name, reason}] for segmenters where available==false (use unavailable_reason, trimmed).
- scoreboard_overall: one row per available segmenter from gold_scores.overall: {name, exact_match, boundary_f1, n}.
- total_divergences, emitted_cases, dropped: from divergences.json.
- cases: the full divergences.json "cases" array, but rewrite each "path" to an ABSOLUTE path by prefixing "${CC}/".

Do not adjudicate anything — just run and report.`,
  { label: 'run-harness', phase: 'Benchmark', schema: BENCH_SCHEMA },
)

log(`Harness: ${bench.available.length} segmenters available (${bench.available.join(', ')}); ` +
    `${bench.total_divergences} divergences, adjudicating ${bench.cases.length} (dropped ${bench.dropped}).`)
if (bench.excluded.length) {
  log(`Excluded: ${bench.excluded.map(e => e.name).join(', ')} (native/ARM issues).`)
}

// ── Phase 2: one judge per divergence ──────────────────────────────────────────

phase('Adjudicate')
const verdicts = (await parallel(
  bench.cases.map((c) => () =>
    agent(
      `You are an expert linguist adjudicating a sentence-boundary disagreement between segmentation libraries.

Read the case file: ${c.path}

It is JSON with:
- "text": the exact passage that was segmented.
- "outputs": { "<segmenter>": [list of sentences it produced], ... } for each library.
- "gold": the ground-truth sentence list, OR null if this corpus has no gold standard.
- "features", "corpus", "language", etc.

Your job — a careful MANUAL REVIEW:
1. Read the passage and each library's segmentation.
2. Decide the CORRECT segmentation of this passage:
   - If "gold" is non-null, gold is authoritative — the winner(s) are exactly the libraries whose output equals gold (compare as lists; ignore only leading/trailing whitespace). If none match gold, winner = "none_correct".
   - If "gold" is null, use linguistic judgment: a correct boundary ends a complete sentence/utterance; abbreviations (Mr., U.S.C., et al.), decimals (3.14), initials (J. R. R.), list numbering (889.), ellipses, and mid-quotation periods are NOT boundaries.
3. Identify the winner (single best library name), all "winners" tied for best, and a "ranking" of the DISTINCT segmentations best->worst (name each distinct output by one representative library that produced it).
4. Write a "reason" NOTE: be concrete and specific — name the exact token or boundary in dispute and explain why the winner handled it correctly and the loser(s) did not (e.g. 'pysbd split after "[903]." treating the following "889." article number as a new sentence; gold keeps the article number attached, so sentencesplit—which did not split there—wins').
5. Classify the dispute "category", rate "severity" (trivial/minor/major) and your "confidence", and state how THIS library ("sentencesplit") did in "sentencesplit_assessment".

Echo back case_id="${c.id}", corpus="${c.corpus}", language="${c.language}".
Return ONLY the structured verdict.`,
      { label: `judge:${c.id}`, phase: 'Adjudicate', schema: VERDICT_SCHEMA },
    ),
  ),
)).filter(Boolean)

log(`Adjudicated ${verdicts.length}/${bench.cases.length} cases.`)

// Tally in plain JS (no agent needed) so the report has authoritative numbers.
const SEGS = bench.available
const wins = Object.fromEntries(SEGS.map((s) => [s, 0]))
const apps = Object.fromEntries(SEGS.map((s) => [s, 0])) // times the seg participated (case has >1 output anyway)
const ssAssess = { correct: 0, incorrect: 0, tied: 0, not_applicable: 0 }
const byCategory = {}
let noneCorrect = 0
for (const v of verdicts) {
  for (const w of v.winners || []) if (w in wins) wins[w] += 1
  if (v.winner === 'none_correct') noneCorrect += 1
  if (v.sentencesplit_assessment in ssAssess) ssAssess[v.sentencesplit_assessment] += 1
  byCategory[v.category] = (byCategory[v.category] || 0) + 1
}
const tally = { wins, none_correct: noneCorrect, sentencesplit_assessment: ssAssess, by_category: byCategory }

// ── Phase 3: synthesize the report ─────────────────────────────────────────────

phase('Report')
const reportSummary = await agent(
  `Write the final cross-library sentence-boundary comparison report.

Inputs:
- Objective scoreboard JSON: ${CC}/results/scoreboard.json  (READ it — use gold_scores.overall, by_language, by_corpus, segmenter availability + exclusion reasons, and agreement stats).
- Available segmenters: ${JSON.stringify(SEGS)}
- Excluded segmenters: ${JSON.stringify(bench.excluded)}
- Adjudication tallies (authoritative, computed in code): ${JSON.stringify(tally)}
- Divergence totals: total=${bench.total_divergences}, adjudicated=${verdicts.length}, dropped=${bench.dropped} (capped at ${CAP}).
- Full per-case verdicts (JSON array): ${JSON.stringify(verdicts)}

Tasks:
1. Write ${CC}/results/verdicts.json containing {"tally": <the tally object above>, "verdicts": <the verdicts array above>} (pretty-printed, ensure_ascii false). You may use a small python/bash heredoc to write it exactly.
2. Write ${CC}/results/REPORT.md — a thorough but readable Markdown report with these sections:
   - **Methodology**: corpora used (golden rules, Universal Dependencies treebanks across ~9 languages, Wikipedia multi-domain/multilingual, Project Gutenberg literary, legal opinions), segmenters compared, which were excluded and why, and the metric definitions (read metric_notes from scoreboard.json). Note the single-judge adjudication and the ${CAP}-case cap (so ${bench.dropped} divergences were not individually reviewed).
   - **Objective scoreboard**: a Markdown table of exact-match % and boundary-F1 % per segmenter overall, plus a by-language table. State who leads.
   - **Adjudication results**: overall win counts per segmenter (from tally.wins), how often sentencesplit was correct/incorrect/tied, and the distribution by category. A short head-to-head: in how many adjudicated cases sentencesplit was a winner vs not.
   - **Where sentencesplit wins / loses**: 4-8 representative cases EACH, quoting the case's "reason" note and the disputed text. Prioritize 'major' severity and high-confidence verdicts. Pull these from the verdicts array (look up the case files under ${CC}/results/cases/ if you need the exact text).
   - **Patterns & recommendations**: what categories of error are most common for sentencesplit, and concrete suggestions (e.g. specific abbreviation/numbering rules to tighten). Be honest where competitors are better.
   - **Appendix**: a compact table of every adjudicated case: case_id | corpus | language | winner | category | severity | one-line reason.
3. Return a 6-10 line plain-text executive summary (leaderboard, sentencesplit's win rate, top failure category, and the two file paths you wrote).`,
  { label: 'synthesize-report', phase: 'Report' },
)

log('Report written to benchmarks/corpus_compare/results/REPORT.md')

return {
  available: SEGS,
  excluded: bench.excluded,
  total_divergences: bench.total_divergences,
  adjudicated: verdicts.length,
  dropped: bench.dropped,
  tally,
  report: `${CC}/results/REPORT.md`,
  verdicts_file: `${CC}/results/verdicts.json`,
  summary: reportSummary,
}
