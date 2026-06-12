export const meta = {
  name: 'library-review',
  description: 'Thorough multi-agent review of the sentencesplit library: gaps, inconsistencies, architecture, improvements',
  phases: [
    { title: 'Survey', detail: 'one deep reader per subsystem/dimension produces structured findings' },
    { title: 'Verify', detail: 'independent skeptic re-reads the cited code to confirm or refute each finding' },
    { title: 'Synthesize', detail: 'dedupe, group by theme, prioritize into a report' },
    { title: 'Critique', detail: 'completeness critic flags missed areas and weak findings' },
  ],
}

// ---------------------------------------------------------------------------
// Shared grounding context handed to every agent.
// ---------------------------------------------------------------------------
const ROOT = process.env.SENTENCESPLIT_ROOT || process.cwd()

const ARCH = `
PROJECT: sentencesplit — a rule-based sentence boundary detection library (derived from pySBD /
Pragmatic Segmenter) supporting 24 languages. Pure Python, ZERO runtime dependencies (only the
stdlib \`re\` module). Python 3.11+. Repo root: ${ROOT}.

PIPELINE: Segmenter -> Processor -> sentence list.
- sentencesplit/segmenter.py: public API. Params: language (ISO 639-1), clean, doc_type, char_span,
  split_mode. Methods: segment(), segment_spans(), segment_clean(), segment_with_lookahead(),
  should_wait_for_more(). Maps processed sentences back to original-text spans via _match_spans()
  and drives lookahead probing.
- sentencesplit/processor.py: core logic. Two explicit pipelines: _text_processing_phases() and
  _boundary_processing_phases(). split_into_segments() post-processes, restores placeholders,
  re-splits at Latin ".) Capital" or CJK quote boundaries, merges orphan fragments. Reads split_mode
  ("conservative" | "aggressive"). C901 (complexity) is ignored for this file in ruff config.
- sentencesplit/language_profile.py: LanguageProfile frozen dataclass, resolved per-language via
  LanguageProfile.from_language(lang). Centralizes all language-specific hooks the Processor needs.
- sentencesplit/cleaner.py: text normalization (HTML, PDF, escaped chars, newlines). Subclassable.
- sentencesplit/abbreviation_replacer.py: Aho-Corasick automaton for multi-pattern abbreviation
  matching with pre-compiled caching; split_mode-dependent logic.
- sentencesplit/between_punctuation.py, lists_item_replacer.py, punctuation_replacer.py,
  exclamation_words.py: rule modules invoked from processor phases.
- sentencesplit/languages.py: LANGUAGE_CODES lazy dict mapping ISO 639-1 -> language classes
  (imported on first access). 24 natural languages + combined "en_es_zh" + domain "en_legal".
- sentencesplit/utils.py: shared types (Rule, TextSpan, SegmentLookahead) and helpers (apply_rules,
  ensure_compiled, Latin-uppercase detection).
- sentencesplit/spacy_component.py: optional spaCy pipeline factory (entry point in pyproject.toml).
- sentencesplit/lang/common/{common.py,standard.py,cjk.py}: base classes. Languages inherit
  Common + Standard, optionally mix in CJKBoundaryProfile. cjk.py has CJKProcessor + reporting-clause
  merge logic used by zh/ja and en_es_zh.

STYLE: ruff is the sole linter/formatter, line length 127. Conventional Commits (semantic-release
parses them). Bug fixes get a regression test in tests/regression/ BEFORE the fix.

The codebase is small and self-contained. You can and should read the actual source files.
`.trim()

// ---------------------------------------------------------------------------
// Review dimensions — each owns a subsystem and a focus.
// ---------------------------------------------------------------------------
const DIMENSIONS = [
  {
    key: 'api',
    label: 'Public API & streaming',
    scope: 'sentencesplit/segmenter.py, sentencesplit/__init__.py, sentencesplit/about.py, sentencesplit/utils.py (TextSpan/SegmentLookahead/Rule). Cross-check against tests/test_segmenter.py.',
    focus: `The public surface. Look for: correctness bugs in span mapping (_match_spans) — off-by-one,
      duplicate-substring matching, spans that don't tile the original text or overlap; lookahead
      (segment_with_lookahead / should_wait_for_more) edge cases — empty input, no boundary, probe-stem
      selection per script; inconsistent return types or flags (char_span constructor flag vs
      segment_spans always returning TextSpan); parameter validation (unknown language, bad split_mode/
      doc_type); thread-safety / shared mutable state on the Segmenter; docstring vs actual behavior
      mismatches; missing edge-case handling (empty string, whitespace-only, no terminal punctuation).`,
  },
  {
    key: 'processor',
    label: 'Processor core pipeline',
    scope: 'sentencesplit/processor.py. Cross-reference language_profile.py for the hooks it consumes.',
    focus: `The heart of the engine. Look for: phase-ordering bugs (a phase that depends on another running
      first / placeholder restored too early or late); the Latin ".) Capital" and CJK-quote resplit and
      orphan-merge logic — cases it mis-splits or fails to split; regex correctness (catastrophic
      backtracking, missing anchors, unintended greedy matches); placeholder collision risk (could real
      text contain a placeholder sentinel?); split_mode conservative-vs-aggressive divergence and whether
      both branches are coherent; excessive complexity that hides bugs (C901 is suppressed here — is the
      function decomposable?); dead branches or unreachable rules.`,
  },
  {
    key: 'abbrev',
    label: 'Abbreviation & punctuation replacement',
    scope: 'sentencesplit/abbreviation_replacer.py, sentencesplit/punctuation_replacer.py, sentencesplit/exclamation_words.py. Cross-check tests/test_abbreviation_replacer.py, tests/test_punctuation_replacer.py.',
    focus: `The Aho-Corasick abbreviation subsystem. Look for: correctness of the automaton build and match
      (overlapping matches, longest-match vs first-match, case sensitivity, word-boundary handling);
      caching correctness (is the cache key complete? could two different abbreviation sets collide? is
      the cache unbounded / a memory leak? thread-safety of the shared cache); split_mode-dependent
      abbreviation logic correctness; Unicode handling (combining marks, non-Latin abbreviations);
      punctuation placeholder substitution round-trip safety; exclamation-word exception coverage.`,
  },
  {
    key: 'between_lists',
    label: 'Between-punctuation & list items',
    scope: 'sentencesplit/between_punctuation.py, sentencesplit/lists_item_replacer.py.',
    focus: `Quote/paren protection and list-item marker insertion. Look for: nested or unbalanced
      quote/paren handling bugs; quote-character coverage gaps (curly quotes, guillemets, CJK brackets,
      mixed/locale quotes); list-item detection false positives/negatives (alphabetic, roman, numeric,
      multi-level lists); regex robustness; interactions with the processor resplit logic; cases where
      protection leaks placeholders into output.`,
  },
  {
    key: 'profile_registry',
    label: 'Language profile & registry architecture',
    scope: 'sentencesplit/language_profile.py, sentencesplit/languages.py, sentencesplit/lang/common/common.py, sentencesplit/lang/common/standard.py. Cross-check tests/test_language_profile.py, tests/test_languages.py.',
    focus: `The core abstraction. This is the most important ARCHITECTURE dimension. Look for: leaky
      abstractions (does Processor still reach into language classes via getattr instead of through the
      profile? are there hooks that bypass LanguageProfile?); the lazy-loading registry (LANGUAGE_CODES /
      LazyLanguageCodes) — thread-safety, error handling for unknown codes, mutation API soundness;
      whether the frozen-dataclass resolution is complete and consistent across all languages; missing or
      asymmetric hooks (a hook some languages need but can't express); coupling between common.py and
      standard.py; whether the Common+Standard inheritance + optional mixins is the right shape or should
      be composition; default-value correctness for languages that don't override a hook.`,
  },
  {
    key: 'cjk',
    label: 'CJK handling',
    scope: 'sentencesplit/lang/common/cjk.py, sentencesplit/lang/chinese.py, sentencesplit/lang/japanese.py, sentencesplit/lang/en_es_zh.py. Cross-check tests/lang/test_chinese.py, test_japanese.py, test_en_es_zh.py.',
    focus: `CJK boundary detection. Look for: CJK terminal-punctuation coverage gaps (fullwidth vs halfwidth,
      ！？。．、；, closing quotes/brackets 」』）】 etc.); CJKProcessor reporting-clause merge ("…" 他说。)
      false merges or missed merges; LATIN_UPPERCASE_RESPLIT=False interaction with mixed-script text;
      en_es_zh combined-profile correctness (does merging abbreviation lists from multiple languages cause
      cross-language false positives?); whitespace assumptions that hold for English but not CJK (CJK has
      no inter-word spaces); duplicated CJK logic across chinese/japanese that has drifted.`,
  },
  {
    key: 'cleaner',
    label: 'Cleaner / text normalization',
    scope: 'sentencesplit/cleaner.py and any per-language Cleaner overrides (grep for "class Cleaner" under sentencesplit/lang/). Cross-check tests/test_cleaner.py.',
    focus: `Text normalization (HTML, PDF, escaped chars, newlines). Look for: regexes that corrupt valid
      text (over-aggressive newline collapsing, HTML stripping that eats angle-bracket content, PDF
      de-hyphenation joining words that shouldn't join); idempotency (clean(clean(x)) == clean(x)?);
      order-dependence of cleaning steps; whether cleaning shifts character offsets in a way that breaks
      span mapping when clean=True; coverage gaps vs documented capabilities; unused/dead cleaning rules.`,
  },
  {
    key: 'lang_consistency',
    label: 'Cross-language consistency sweep',
    scope: 'ALL 24 language modules under sentencesplit/lang/ (amharic, arabic, armenian, bulgarian, burmese, danish, deutsch, dutch, english, en_legal, french, greek, hindi, italian, japanese, kazakh, marathi, persian, polish, russian, slovak, spanish, tagalog, urdu). Use grep/glob to compare structure across files rather than reading every line.',
    focus: `Consistency ACROSS languages (not deep per-language correctness — that is another agent's job).
      Look for: structural inconsistencies (some langs define X, peers that should don't); divergent copies
      of logic that should be shared (e.g. abbreviation-handling boilerplate duplicated and drifted);
      naming inconsistencies; languages registered in languages.py but missing tests or vice versa;
      languages that should mix in CJKBoundaryProfile or set LATIN_UPPERCASE_RESPLIT but don't (or do
      wrongly); abbreviation lists with obvious errors (duplicates, wrong-language entries, missing
      common abbreviations, encoding issues); no-op overrides that add nothing; the registry vs the actual
      module set (24 claimed — verify the count and that the README/CLAUDE.md list matches reality).`,
  },
  {
    key: 'lang_big',
    label: 'Large / complex language modules',
    scope: 'sentencesplit/lang/italian.py (~2280 lines), sentencesplit/lang/dutch.py (~1597), sentencesplit/lang/danish.py (~527), sentencesplit/lang/kazakh.py (~340), sentencesplit/lang/slovak.py (~311), sentencesplit/lang/deutsch.py (~251).',
    focus: `Deep review of the biggest modules — they likely hold the most divergence and dead weight.
      Look for: enormous abbreviation lists with duplicates, mis-encoded entries, or entries that never
      match; copy-pasted logic that has drifted from the common base or from each other; whether these
      huge lists should be data files instead of inline Python; regex/override bugs unique to these
      languages; complexity that could be folded back into Standard/Common; anything that looks
      machine-generated and unverified.`,
  },
  {
    key: 'tests',
    label: 'Test coverage & quality',
    scope: 'tests/ (all). You MAY run: `cd ${ROOT} && uv run pytest --cov=sentencesplit --cov-report=term-missing tests/ -q` to get real coverage numbers. There is also a stale .coverage file you can ignore.',
    focus: `Test discipline. Look for: modules/branches with low or zero coverage (report file + missing
      lines from the coverage run); public API behaviors that are documented but untested (lookahead,
      split_mode, spans, clean, doc_type); regression-test discipline (does tests/regression/test_issues.py
      cover real past bugs? are there bug-shaped code paths with no regression test?); golden-rule gaps per
      language; flaky/over-broad assertions; tests that assert current-but-wrong behavior (would mask the
      bugs other agents find); missing edge-case tests (empty/whitespace/no-boundary/very-long input).
      Actually run the suite if you can; report pass/fail and coverage %.`,
  },
  {
    key: 'perf',
    label: 'Performance & hot paths',
    scope: 'sentencesplit/processor.py, abbreviation_replacer.py, between_punctuation.py, utils.py (ensure_compiled), language_profile.py, segmenter.py. Look at benchmarks/ for context on what is measured.',
    focus: `Performance of the rule engine. Look for: regexes compiled on every call instead of cached;
      O(n^2) or worse passes over the text; repeated full-text scans that could be fused; the Aho-Corasick
      build cost and whether it's cached per-language; per-call profile resolution / object construction
      that could be memoized; placeholder substitution doing many sequential .replace() passes; large
      structures rebuilt unnecessarily; any accidental quadratic behavior on long inputs. Distinguish
      real, measurable wins from micro-optimizations; mark severity accordingly.`,
  },
  {
    key: 'docs',
    label: 'Docs / packaging consistency',
    scope: 'README.md, CLAUDE.md, AGENTS.md, CONTRIBUTING.md, CHANGELOG.md, pyproject.toml, sentencesplit/about.py, examples/, .github/ workflows.',
    focus: `Docs vs reality. Look for: README/CLAUDE.md claims that don't match the code (language count,
      method names, parameter names, behavior, "zero dependencies"); example snippets in README that would
      not produce the shown output (verify a few against the actual API); about.py / version / pyproject
      metadata inconsistencies; CHANGELOG drift; CONTRIBUTING instructions that are stale; CI matrix
      (Python versions) vs pyproject classifiers; spaCy entry point correctness; AGENTS.md vs CLAUDE.md
      divergence. Where feasible, actually run a README snippet to confirm.`,
  },
]

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------
const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    summary: { type: 'string', description: 'One-paragraph overall impression of this subsystem.' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          title: { type: 'string', description: 'Short, specific title.' },
          category: {
            type: 'string',
            enum: ['gap', 'inconsistency', 'architecture', 'correctness', 'performance', 'docs', 'test', 'style'],
          },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          location: { type: 'string', description: 'file:line (or file) — must be a real, citable location.' },
          description: { type: 'string', description: 'What is wrong and why it matters.' },
          evidence: { type: 'string', description: 'Concrete code excerpt / fact substantiating the claim.' },
          suggestion: { type: 'string', description: 'Concrete, actionable fix.' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['title', 'category', 'severity', 'location', 'description', 'suggestion', 'confidence'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
    adjusted_severity: { type: 'string', enum: ['high', 'medium', 'low'] },
    reasoning: { type: 'string', description: 'What you found when you re-read the cited code.' },
    correction: { type: 'string', description: 'Corrected location / suggestion if the original was off, else empty.' },
  },
  required: ['verdict', 'reasoning'],
}

// ---------------------------------------------------------------------------
// Prompt builders
// ---------------------------------------------------------------------------
function finderPrompt(d) {
  return `${ARCH}

You are reviewing ONE dimension of this library: "${d.label}".

SCOPE (read these — use Read/Grep/Glob/Bash freely):
${d.scope}

WHAT TO LOOK FOR:
${d.focus}

GROUND RULES:
- Read the ACTUAL source. Every finding must cite a real file:line you have verified by reading it.
- Categories: gap, inconsistency, architecture, correctness, performance, docs, test, style.
- Report substantive issues. Style nits are allowed but mark them severity=low.
- Prefer fewer, well-substantiated findings over a long list of speculation. If you are unsure a
  problem is real, either verify it harder or mark confidence=low and say what you'd need to confirm.
- Do NOT propose rewriting working code for taste. Architecture findings must name a concrete defect
  (coupling that causes bugs, an abstraction that can't express a real case, duplicated logic that has
  drifted), not just "this could be cleaner".
- Include a concrete, actionable suggestion for each finding.

Return the structured findings object.`
}

function verifyPrompt(f, dimKey) {
  return `${ARCH}

A reviewer examining the "${dimKey}" dimension produced the finding below. Your job is to ADVERSARIALLY
verify it by re-reading the actual code. Try to REFUTE it. Default to "uncertain" (not "confirmed") if
you cannot substantiate it by reading the cited location yourself.

FINDING:
- Title: ${f.title}
- Category: ${f.category}
- Claimed severity: ${f.severity}
- Location: ${f.location}
- Description: ${f.description}
- Evidence claimed: ${f.evidence || '(none provided)'}
- Suggested fix: ${f.suggestion}

STEPS:
1. Open the cited file/line. Does the code actually say/do what the finding claims?
2. Is the problem real, or is it already handled elsewhere (another phase, a default, a test, a guard)?
3. If real, is the claimed severity right? Adjust it.
4. If the location or suggestion is wrong but the underlying issue is real, set verdict=confirmed and
   put the correction in "correction".
5. Verdict: "confirmed" (real, substantiated), "refuted" (not real / already handled / based on a
   misreading), or "uncertain" (plausible but you could not confirm from the code).

Be rigorous and skeptical. A confirmed finding must be something you personally verified in the source.
Return the verdict object.`
}

// ---------------------------------------------------------------------------
// Phase 1+2: Survey then Verify, pipelined per dimension.
// ---------------------------------------------------------------------------
log(`Surveying ${DIMENSIONS.length} review dimensions; each finding will be adversarially verified.`)

const dimResults = await pipeline(
  DIMENSIONS,
  // Stage 1 — deep reader for this dimension.
  (d) => agent(finderPrompt(d), { label: `survey:${d.key}`, phase: 'Survey', schema: FINDINGS_SCHEMA }),
  // Stage 2 — verify each finding from this dimension as soon as the survey returns.
  (review, dim) => {
    const items = (review && review.findings) || []
    if (!items.length) return Promise.resolve({ key: dim.key, label: dim.label, summary: (review && review.summary) || '', findings: [] })
    return parallel(
      items.map((f, i) => () =>
        agent(verifyPrompt(f, dim.key), { label: `verify:${dim.key}#${i + 1}`, phase: 'Verify', schema: VERDICT_SCHEMA })
          .then((v) => ({ ...f, dimension: dim.key, verify: v || { verdict: 'uncertain', reasoning: 'verifier returned null' } })),
      ),
    ).then((arr) => ({ key: dim.key, label: dim.label, summary: (review && review.summary) || '', findings: arr.filter(Boolean) }))
  },
)

const dims = dimResults.filter(Boolean)
const allFindings = dims.flatMap((d) => d.findings)
const confirmed = allFindings.filter((f) => f.verify && f.verify.verdict === 'confirmed')
const uncertain = allFindings.filter((f) => f.verify && f.verify.verdict === 'uncertain')
const refuted = allFindings.filter((f) => f.verify && f.verify.verdict === 'refuted')

log(`Surveyed: ${allFindings.length} raw findings -> ${confirmed.length} confirmed, ${uncertain.length} uncertain, ${refuted.length} refuted.`)

// Compact, ordered view for the synthesizer (confirmed + uncertain; refuted dropped).
function effSeverity(f) {
  return (f.verify && f.verify.adjusted_severity) || f.severity
}
const sevRank = { high: 0, medium: 1, low: 2 }
const forReport = confirmed
  .concat(uncertain)
  .map((f) => ({
    dimension: f.dimension,
    title: f.title,
    category: f.category,
    severity: effSeverity(f),
    verdict: f.verify.verdict,
    location: f.location,
    description: f.description,
    suggestion: f.suggestion,
    correction: (f.verify && f.verify.correction) || '',
  }))
  .sort((a, b) => (sevRank[a.severity] ?? 3) - (sevRank[b.severity] ?? 3))

// ---------------------------------------------------------------------------
// Phase 3: Synthesize into a report.
// ---------------------------------------------------------------------------
phase('Synthesize')

const dimSummaries = dims.map((d) => `- ${d.label} (${d.key}): ${d.summary || '(no summary)'}`).join('\n')

const report = await agent(
  `${ARCH}

You are the lead reviewer. Below are VERIFIED findings from a thorough multi-agent review of the
sentencesplit library. Each was independently re-checked against the source; refuted findings are
already removed. "uncertain" findings survived verification but could not be fully confirmed — include
them but clearly flag them as needs-confirmation.

Per-dimension impressions:
${dimSummaries}

VERIFIED FINDINGS (JSON, pre-sorted by severity):
${JSON.stringify(forReport, null, 2)}

Produce a thorough, well-organized Markdown review report titled "# sentencesplit — Library Review".
Requirements:
1. Start with an "## Executive summary" — 4-8 sentences on the overall health of the library and the
   most important themes (gaps, inconsistencies, architecture, other improvements).
2. A "## Top recommendations" numbered list (the ~8-12 highest-leverage actions), each with a one-line
   rationale and the file(s) involved.
3. Group the remaining detail under thematic sections: "## Correctness & bugs", "## Architecture",
   "## Cross-language consistency", "## Gaps & missing coverage", "## Performance", "## Tests",
   "## Docs & packaging". Put each finding under the best-fitting section (not necessarily its original
   category). DEDUPE: if multiple agents found the same issue, merge into one entry and note the
   corroboration.
4. For each finding: bold title, severity tag, file:line, a crisp description, and the suggested fix.
   Apply any "correction" notes to the location/suggestion. Mark uncertain ones with "(needs confirmation)".
5. End with "## What's working well" — a short, honest list of strengths, so the report is balanced.

Be specific and actionable. This report goes to the maintainer. Return ONLY the Markdown.`,
  { label: 'synthesize', phase: 'Synthesize' },
)

// ---------------------------------------------------------------------------
// Phase 4: Completeness critic.
// ---------------------------------------------------------------------------
phase('Critique')

const critique = await agent(
  `${ARCH}

A multi-agent review covered these dimensions:
${DIMENSIONS.map((d) => `- ${d.label} (${d.key}): ${d.scope}`).join('\n')}

It produced this report:

${report}

You are the completeness critic. Read the report and, using the actual source if needed, answer:
1. COVERAGE GAPS: What important part of the library or class of issue was NOT examined or is
   under-represented? (e.g. a module no dimension owned, a cross-cutting concern like Unicode/encoding,
   error handling, security/ReDoS, packaging, thread-safety, API stability/versioning.)
2. WEAK OR DUBIOUS FINDINGS: Any finding in the report that looks wrong, overstated, or likely a
   non-issue on closer reading? Name it and say why.
3. MISSED HIGH-VALUE ISSUES: If you can quickly spot a concrete issue the report missed, state it with
   file:line.
4. PRIORITIZATION CHECK: Does the "Top recommendations" ordering make sense? Suggest any reordering.

Be concise and concrete. Return Markdown with those four short sections.`,
  { label: 'critique', phase: 'Critique' },
)

// ---------------------------------------------------------------------------
// Return everything.
// ---------------------------------------------------------------------------
return {
  report,
  critique,
  stats: {
    dimensions: DIMENSIONS.length,
    rawFindings: allFindings.length,
    confirmed: confirmed.length,
    uncertain: uncertain.length,
    refuted: refuted.length,
    byDimension: dims.map((d) => ({
      key: d.key,
      total: d.findings.length,
      confirmed: d.findings.filter((f) => f.verify && f.verify.verdict === 'confirmed').length,
    })),
  },
}
