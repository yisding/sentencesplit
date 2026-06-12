export const meta = {
  name: 'level-up',
  description: 'Fuse an internal capability audit with external landscape research (SOTA, competitors, LLM-era demand) into a prioritized roadmap for taking sentencesplit to the next level',
  whenToUse: 'When you want a comprehensive, forward-looking strategy for the library — not a bug review (use library-review) and not a benchmark loop (use compare-segmenters). Produces analysis/LEVEL_UP_PLAN.md.',
  phases: [
    { title: 'Map', detail: 'parallel internal-audit readers + external web researchers produce structured findings' },
    { title: 'Brief', detail: 'condense all findings into one grounded landscape brief' },
    { title: 'Envision', detail: 'generate independent strategic visions from distinct north-stars' },
    { title: 'Judge', detail: 'score each vision across feasibility / impact / differentiation / fit lenses' },
    { title: 'Roadmap', detail: 'synthesize a prioritized, sequenced plan grounded in the winning blend' },
    { title: 'Critique', detail: 'completeness critic flags missing angles and weak claims; final revise + write' },
  ],
}

// ---------------------------------------------------------------------------
// Shared grounding handed to every agent.
// ---------------------------------------------------------------------------
const ROOT = process.env.SENTENCESPLIT_ROOT || process.cwd()

const PROJECT = `
PROJECT: sentencesplit — a rule-based sentence boundary detection (SBD) library, derived from pySBD /
Pragmatic Segmenter, supporting 24 natural languages plus a combined "en_es_zh" profile and a domain
"en_legal" profile. Pure Python, ZERO runtime dependencies (stdlib only: re, unicodedata, string,
functools, dataclasses). Python 3.11+. MIT. Repo root: ${ROOT}. Current version 0.0.4.

PIPELINE: Segmenter -> Processor -> sentence list.
- sentencesplit/segmenter.py: public API. Params: language (ISO 639-1), clean, doc_type, char_span,
  split_mode ("conservative" | "balanced" | "aggressive"). Methods: segment(), segment_spans(),
  segment_clean(), segment_with_lookahead(), should_wait_for_more(). Maps sentences back to original
  spans via _match_spans(); drives streaming lookahead probing.
- sentencesplit/processor.py: core rule engine. Two pipelines: _text_processing_phases() and
  _boundary_processing_phases(). split_into_segments() post-processes, restores placeholders, re-splits
  at Latin ".) Capital" or CJK quote boundaries, merges orphan fragments.
- sentencesplit/language_profile.py: LanguageProfile frozen dataclass per language.
- sentencesplit/abbreviation_replacer.py: Aho-Corasick automaton for multi-pattern abbreviation matching.
- sentencesplit/{between_punctuation,lists_item_replacer,punctuation_replacer,exclamation_words}.py:
  rule modules invoked from processor phases.
- sentencesplit/cleaner.py: text normalization (HTML, PDF, escaped chars, newlines), subclassable.
- sentencesplit/languages.py: lazy ISO-639-1 -> language class registry.
- sentencesplit/lang/common/{common,standard,cjk}.py: base classes; CJK mix-in for zh/ja/en_es_zh.
- sentencesplit/spacy_component.py: optional spaCy pipeline factory (entry point).

EXISTING ASSETS to read for grounding (do not re-derive what's already written):
- benchmarks/corpus_compare/ : cross-library comparison harness (sentencesplit vs pysbd vs
  pragmatic_segmenter(Ruby) vs nltk punkt vs syntok) over Golden Rules + UD treebanks + Wikipedia +
  Gutenberg + legal. results/REPORT.md, results/IMPROVEMENTS.md, results/scoreboard.json.
- benchmarks/ : short_string_benchmark.py, bigtext_speed_benchmark.py, benchmark_sbd_tools.py,
  genia_benchmark.py, english_golden_rules.py.
- analysis/ : earlier pysbd-vs-punkt and wikipedia disagreement analyses.
- eval/ : vendored legal opinions for legal-SBD eval.
- tests/lang/*, tests/regression/*, tests/test_segmenter.py.

KNOWN CONTEXT (from prior benchmarking, treat as starting hypotheses to verify, not gospel):
- First full cross-library comparison: sentencesplit led on exact-match (~74%) and boundary-F1 (~94%)
  and on adjudicated win-count. Residual weaknesses surfaced: multi-sentence quotations, missing
  abbreviations in some languages, !!!/??? before a capital, trailing zero-width-space fragments.
- "UD colon-as-boundary losses" are annotation artifacts, NOT real bugs — don't chase them.
- Dev box is aarch64: blingfire / spaCy / stanza native wheels CRASH here, so any neural/ML angle must
  be evaluated on portability + optional-dependency grounds, not assumed runnable locally.

STYLE / CONSTRAINTS: ruff (line length 127), Conventional Commits, bug fixes get a regression test first.
The zero-dependency, pure-Python, fast-import ethos is a core selling point — weigh every proposal
against it.
`.trim()

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------
const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['area', 'summary', 'items'],
  properties: {
    area: { type: 'string' },
    summary: { type: 'string', description: '2-4 sentence state of this area' },
    items: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'detail', 'category', 'confidence'],
        properties: {
          title: { type: 'string' },
          detail: { type: 'string', description: 'specifics with evidence' },
          category: { type: 'string', enum: ['strength', 'gap', 'opportunity', 'risk', 'trend'] },
          evidence: { type: 'string', description: 'file:line, benchmark number, or quote' },
          sources: { type: 'array', items: { type: 'string' }, description: 'URLs for external claims' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
  },
}

const BRIEF_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['competitivePosition', 'strengths', 'gaps', 'externalTrends', 'opportunities'],
  properties: {
    competitivePosition: { type: 'string', description: 'where sentencesplit sits vs the field today' },
    strengths: { type: 'array', items: { type: 'string' } },
    gaps: { type: 'array', items: { type: 'string' } },
    externalTrends: { type: 'array', items: { type: 'string' }, description: 'what is changing in SBD / NLP / LLM tooling' },
    opportunities: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'rationale'],
        properties: { title: { type: 'string' }, rationale: { type: 'string' } },
      },
    },
  },
}

const VISION_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['name', 'northStar', 'thesis', 'initiatives', 'risks', 'successMetrics'],
  properties: {
    name: { type: 'string' },
    northStar: { type: 'string', description: 'the one sentence this vision optimizes for' },
    thesis: { type: 'string' },
    initiatives: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'what', 'why', 'effort', 'impact'],
        properties: {
          title: { type: 'string' },
          what: { type: 'string' },
          why: { type: 'string' },
          effort: { type: 'string', enum: ['S', 'M', 'L', 'XL'] },
          impact: { type: 'string', enum: ['low', 'medium', 'high', 'transformative'] },
        },
      },
    },
    risks: { type: 'array', items: { type: 'string' } },
    successMetrics: { type: 'array', items: { type: 'string' } },
  },
}

const SCORE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['lens', 'score', 'rationale', 'topStrength', 'topWeakness'],
  properties: {
    lens: { type: 'string' },
    score: { type: 'integer', minimum: 1, maximum: 10 },
    rationale: { type: 'string' },
    topStrength: { type: 'string' },
    topWeakness: { type: 'string' },
  },
}

const CRITIQUE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['missingAngles', 'weakClaims', 'sequencingIssues', 'verdict'],
  properties: {
    missingAngles: { type: 'array', items: { type: 'string' } },
    weakClaims: { type: 'array', items: { type: 'string' }, description: 'unverified market/competitor/SOTA claims to caveat or cut' },
    sequencingIssues: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string', enum: ['ship', 'revise', 'major-gaps'] },
  },
}

// ---------------------------------------------------------------------------
// Phase 1 — MAP: internal audit (read code) + external research (search web)
// ---------------------------------------------------------------------------
const INTERNAL = [
  {
    key: 'api-dx',
    label: 'API & developer experience',
    prompt: `Audit the PUBLIC SURFACE and developer experience. Read sentencesplit/segmenter.py, __init__.py,
utils.py (TextSpan / SegmentLookahead / Rule), spacy_component.py, README.md, and tests/test_segmenter.py.
Assess: ergonomics, configuration model (split_mode, doc_type, clean, char_span), span-mapping API,
streaming/lookahead API, type hints / py.typed, error handling, discoverability, docs quality, and what a
new user would struggle with. Identify strengths, gaps, and concrete opportunities to make the API best-in-class.`,
  },
  {
    key: 'accuracy',
    label: 'Accuracy posture & known weaknesses',
    prompt: `Audit ACCURACY. Read benchmarks/corpus_compare/results/REPORT.md and IMPROVEMENTS.md (if present),
benchmarks/corpus_compare/results/scoreboard.json, analysis/*.md and analysis/*.json, and skim
tests/regression/ to see what classes of bugs have been fixed. Summarize: where sentencesplit measurably wins
and loses today, residual bug classes, and the highest-leverage accuracy opportunities. Distinguish real
errors from annotation artifacts (e.g. UD colon-as-boundary is an artifact — do NOT count it as a loss).`,
  },
  {
    key: 'languages',
    label: 'Language coverage & quality tiers',
    prompt: `Audit LANGUAGE COVERAGE. List the languages in sentencesplit/lang/ and languages.py. By reading the
per-language modules (note rough sizes: italian.py and dutch.py are huge; japanese.py / tagalog.py tiny),
assign each a rough quality tier (deep / moderate / thin) based on how much language-specific rule work exists
(abbreviations, between-punctuation, cleaner, processor overrides, tests). Then identify high-demand world
languages that are MISSING or thin and would matter for adoption (consider speaker population + NLP demand,
e.g. Korean, Vietnamese, Thai, Indonesian/Malay, Hebrew, Portuguese, Romanian, Turkish, Bengali, Vietnamese,
Swedish/Norwegian/Finnish). Be specific about what "deep" support requires.`,
  },
  {
    key: 'performance',
    label: 'Performance, internals & robustness',
    prompt: `Audit PERFORMANCE and INTERNALS. Read sentencesplit/processor.py, abbreviation_replacer.py (Aho-Corasick),
between_punctuation.py, cleaner.py, and the benchmarks/ speed scripts (short_string_benchmark.py,
bigtext_speed_benchmark.py). Assess: throughput on big text and on many short strings, import time, memory,
regex-pass count, the C901-complexity processor, caching, and any pathological-input / ReDoS exposure (note the
repo has prior HTML-ReDoS fixes). Identify the realistic performance ceiling for pure Python and where an
optional native/compiled accelerator could matter.`,
  },
  {
    key: 'eval-infra',
    label: 'Evaluation infra & repo health',
    prompt: `Audit EVALUATION INFRASTRUCTURE and REPO HEALTH. Read benchmarks/corpus_compare/ (corpora.py,
segmenters.py, run_compare.py, REPORT.md), benchmarks/*.py, eval/, pyproject.toml (CI matrix, optional deps,
release automation), and the test layout under tests/. Assess: how credibly the project can CLAIM and DEFEND
accuracy/perf numbers today, what corpora/metrics are covered vs missing, reproducibility, coverage, and what
evaluation/CI/release machinery a serious "level up" would need (e.g. a public, versioned benchmark leaderboard).`,
  },
]

const EXTERNAL = [
  {
    key: 'sota',
    label: 'SOTA & research frontier',
    prompt: `Research the STATE OF THE ART in sentence boundary detection / segmentation. Use WebSearch + WebFetch.
Cover modern neural/ML approaches and how they compare to rule-based SBD on accuracy, language coverage, speed,
model size, and licensing. Investigate at minimum: wtpsplit (WtP and the newer "Segment any Text" / SaT models),
Ersatz (multilingual sentence segmentation), deep multilingual punctuation restoration models, and how UD parsers
(spaCy, stanza, Trankit) do sentence segmentation. Note recent papers/benchmarks (2022-2025), reported accuracy
ceilings per language family, and what a pure-Python rule library can realistically match vs cannot. Cite URLs.`,
  },
  {
    key: 'competitors',
    label: 'Competitor libraries',
    prompt: `Research COMPETING / ADJACENT sentence-splitting libraries. Use WebSearch + WebFetch. For each, capture
languages supported, approach (rule/statistical/neural), dependencies, speed, license, maintenance status,
GitHub stars, and notable strengths/weaknesses vs a zero-dependency rule engine. Cover at least: pysbd (the
ancestor), pragmatic_segmenter (Ruby), nltk punkt, syntok, segtok, spaCy sentencizer vs senter vs parser,
stanza, blingfire, charsplit, and the JS/other-ecosystem options. Conclude with where sentencesplit is
differentiated and where it is behind. Cite URLs.`,
  },
  {
    key: 'llm-demand',
    label: 'LLM-era demand & chunking',
    prompt: `Research what MODERN LLM / RAG pipelines need from a sentence splitter. Use WebSearch + WebFetch.
Investigate: LangChain text splitters (RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter),
LlamaIndex SentenceSplitter and SemanticSplitterNodeParser, Haystack, and "semantic chunking" / token-aware
chunking practices for embeddings and retrieval. Also research streaming use cases (segmenting live LLM output
for TTS / incremental display) and what practitioners complain about (over/under-splitting, code blocks, lists,
markdown, multilingual). Identify concrete features a sentence library could offer to become the default
building block for AI text pipelines. Cite URLs.`,
  },
  {
    key: 'datasets-metrics',
    label: 'Datasets, metrics & how to claim SOTA',
    prompt: `Research EVALUATION STANDARDS for sentence segmentation. Use WebSearch + WebFetch. Cover the corpora and
benchmarks the field uses (Universal Dependencies sentence segmentation, the Ersatz test suite, OPUS/WMT data,
GENIA / biomedical, legal/clinical corpora) and the metrics (sentence-boundary F1, exact match, Pk, WindowDiff).
Determine what it would take to credibly publish "SOTA among rule-based / zero-dependency splitters" numbers and
a reproducible public leaderboard. Note licensing constraints on redistributing eval corpora. Cite URLs.`,
  },
  {
    key: 'adoption-packaging',
    label: 'Adoption signals, packaging & ecosystem',
    prompt: `Research ADOPTION and PACKAGING expectations. Use WebSearch + WebFetch. Look at PyPI download trends and
GitHub issue themes for pysbd / nltk / spaCy / blingfire / syntok to infer what users actually hit and want.
Investigate distribution/perf levers that drive adoption in 2025: typing, async, optional Rust/C extension
(pyo3/maturin) or a WASM/JS port, HuggingFace tokenizers / datasets integration, and ecosystem entry points
(spaCy factory, LangChain/LlamaIndex integrations). Assess how a zero-dependency MIT library should position,
document, and govern itself to grow. Cite URLs.`,
  },
]

phase('Map')
log(`Mapping: ${INTERNAL.length} internal-audit readers + ${EXTERNAL.length} external researchers`)

const mapFindings = await parallel([
  ...INTERNAL.map((d) => () =>
    agent(`${PROJECT}\n\n=== YOUR TASK (internal audit: ${d.label}) ===\n${d.prompt}\n\nReturn structured findings. Ground every item in a file:line, a benchmark number, or a quote.`,
      { label: `audit:${d.key}`, phase: 'Map', schema: FINDINGS_SCHEMA, agentType: 'Explore' })
  ),
  ...EXTERNAL.map((d) => () =>
    agent(`${PROJECT}\n\n=== YOUR TASK (external research: ${d.label}) ===\n${d.prompt}\n\nReturn structured findings. Every external claim MUST carry source URLs. Prefer primary sources (papers, repos, docs) over blog summaries. Flag anything you could not verify as low confidence.`,
      { label: `research:${d.key}`, phase: 'Map', schema: FINDINGS_SCHEMA, agentType: 'general-purpose' })
  ),
]).then((r) => r.filter(Boolean))

log(`Collected ${mapFindings.length} finding sets (${mapFindings.reduce((n, f) => n + (f.items?.length || 0), 0)} items)`)

// ---------------------------------------------------------------------------
// Phase 2 — BRIEF: one synthesizer condenses everything into a landscape brief
// ---------------------------------------------------------------------------
phase('Brief')
const brief = await agent(
  `${PROJECT}\n\n=== YOUR TASK ===\nYou are the lead strategist. Below are structured findings from 5 internal-audit readers and 5 external researchers. Synthesize them into ONE tight landscape brief: where sentencesplit honestly stands versus the field, its real strengths and gaps, the external trends that matter, and the biggest opportunities. Be specific and skeptical — discard double-counted or weakly-sourced claims, and keep the zero-dependency ethos front of mind.\n\n=== FINDINGS (JSON) ===\n${JSON.stringify(mapFindings)}`,
  { label: 'landscape-brief', phase: 'Brief', schema: BRIEF_SCHEMA }
)
log(`Brief ready. ${brief.opportunities?.length || 0} opportunities, ${brief.gaps?.length || 0} gaps identified`)

// ---------------------------------------------------------------------------
// Phase 3+4 — ENVISION (generate) then JUDGE (score), pipelined per vision
// ---------------------------------------------------------------------------
const VISIONS = [
  {
    key: 'best-rule-engine',
    northStar: 'The most accurate, broadest, zero-dependency rule-based splitter on earth.',
    angle: `Double down on the core: close the residual accuracy gaps, deepen thin languages, add the highest-demand
missing languages, and ship a public reproducible leaderboard proving "best rule-based / zero-dep" SBD. Stay pure Python.`,
  },
  {
    key: 'llm-infra',
    northStar: 'The default text-segmentation building block for LLM / RAG / streaming pipelines.',
    angle: `Reposition as AI-pipeline infrastructure: first-class semantic/token-aware chunking, robust markdown/code/list
handling, rock-solid streaming segmentation for live LLM output, span alignment for citations, and turnkey LangChain /
LlamaIndex / spaCy / HF integrations.`,
  },
  {
    key: 'hybrid-ml',
    northStar: 'Rule-engine accuracy by default, optional ML to chase true SOTA and hard languages.',
    angle: `Keep the pure-Python core as the default, but add an OPTIONAL pluggable ML backend (e.g. an SaT/wtpsplit-style
model behind an extra) for languages and domains where rules plateau — without compromising the zero-dependency default
import. Be honest about the aarch64 native-wheel portability hazard.`,
  },
  {
    key: 'dx-ecosystem',
    northStar: 'The splitter developers reach for because it is delightful, fast, and trustworthy.',
    angle: `Win on developer experience and trust: superb typing/docs/recipes, an optional compiled accelerator
(Rust/pyo3 or a WASM/JS port) for speed, transparent versioned benchmarks, great error/edge-case behavior, and a
welcoming contribution + governance model that grows language coverage via the community.`,
  },
]

const LENSES = ['feasibility-given-zero-dep-ethos', 'user/market-impact', 'differentiation-vs-competitors', 'maintainability-and-risk']

phase('Envision')
log(`Generating ${VISIONS.length} strategic visions, each judged across ${LENSES.length} lenses`)

const judged = await pipeline(
  VISIONS,
  // Stage 1: generate the vision, grounded by the shared brief.
  (v) =>
    agent(
      `${PROJECT}\n\n=== SHARED LANDSCAPE BRIEF (JSON) ===\n${JSON.stringify(brief)}\n\n=== YOUR TASK ===\nYou are a product strategist arguing for ONE specific direction for sentencesplit.\nNORTH STAR: ${v.northStar}\nANGLE: ${v.angle}\n\nProduce an ambitious but grounded vision: a thesis, and 4-7 concrete initiatives each with what/why and an effort (S/M/L/XL) + impact (low/medium/high/transformative) estimate, plus the key risks and the success metrics that would prove it worked. Commit fully to this north star — do not hedge toward the others.`,
      { label: `vision:${v.key}`, phase: 'Envision', schema: VISION_SCHEMA }
    ),
  // Stage 2: judge this vision across all lenses concurrently.
  (vision, v) =>
    parallel(
      LENSES.map((lens) => () =>
        agent(
          `${PROJECT}\n\n=== SHARED LANDSCAPE BRIEF (JSON) ===\n${JSON.stringify(brief)}\n\n=== VISION UNDER REVIEW (JSON) ===\n${JSON.stringify(vision)}\n\n=== YOUR TASK ===\nScore this vision STRICTLY through ONE lens only: "${lens}". Give a 1-10 score, a rationale, its single biggest strength and biggest weakness through this lens. Be a tough, specific critic — reserve 9-10 for genuinely exceptional fit and call out fatal flaws plainly.`,
          { label: `judge:${v.key}:${lens.split('-')[0]}`, phase: 'Judge', schema: SCORE_SCHEMA }
        )
      )
    ).then((scores) => {
      const valid = scores.filter(Boolean)
      const avg = valid.length ? valid.reduce((s, x) => s + x.score, 0) / valid.length : 0
      return { key: v.key, vision, scores: valid, avgScore: Math.round(avg * 10) / 10 }
    })
)

const ranked = judged.filter(Boolean).sort((a, b) => b.avgScore - a.avgScore)
log(`Visions ranked: ${ranked.map((r) => `${r.key}=${r.avgScore}`).join(', ')}`)

// ---------------------------------------------------------------------------
// Phase 5 — ROADMAP: synthesize a prioritized plan from the winning blend
// ---------------------------------------------------------------------------
phase('Roadmap')
const draft = await agent(
  `${PROJECT}\n\n=== SHARED LANDSCAPE BRIEF (JSON) ===\n${JSON.stringify(brief)}\n\n=== JUDGED & RANKED VISIONS (JSON) ===\n${JSON.stringify(ranked)}\n\n=== YOUR TASK ===\nYou are the lead maintainer writing the definitive plan to take sentencesplit to the next level. Do NOT just pick one vision — synthesize the strongest, highest-scoring threads across all of them into ONE coherent strategy, while grafting the best individual initiatives from the runners-up. The judges' lens scores tell you what is feasible and differentiated; honor that.\n\nWrite a comprehensive markdown roadmap with these sections:\n1. **Executive summary** — the thesis in 3-4 sentences and the single biggest bet.\n2. **Where we stand** — honest competitive position (strengths, gaps), citing the brief.\n3. **Strategy** — the chosen north star and why, plus what we explicitly will NOT do.\n4. **Roadmap** — concrete initiatives grouped into **Now (0-3mo) / Next (3-9mo) / Later (9mo+)**. For each: what, why it matters, rough effort (S/M/L/XL), expected impact, and key risk. Order by impact-per-effort.\n5. **Accuracy & evaluation plan** — how we measure and credibly claim improvement (corpora, metrics, leaderboard).\n6. **Success metrics** — the 5-8 numbers that define "leveled up".\n7. **Risks & open questions**.\n\nBe specific and opinionated. Tie initiatives to evidence from the brief/research. Keep proposals honest about the zero-dependency ethos and the aarch64 native-wheel hazard. Return the full markdown.`,
  { label: 'roadmap-draft', phase: 'Roadmap' }
)

// ---------------------------------------------------------------------------
// Phase 6 — CRITIQUE then final revise + write the artifact
// ---------------------------------------------------------------------------
phase('Critique')
const critique = await agent(
  `${PROJECT}\n\n=== DRAFT ROADMAP (markdown) ===\n${draft}\n\n=== SHARED LANDSCAPE BRIEF (JSON) ===\n${JSON.stringify(brief)}\n\n=== YOUR TASK ===\nYou are a completeness critic. Stress-test this roadmap. What angle or modality is missing (a language family, a use case, a competitor, a packaging lever, a failure mode)? Which market/competitor/SOTA claims are unverified and need a caveat or cut? Are the sequencing and effort/impact estimates internally consistent? Give a verdict.`,
  { label: 'completeness-critic', phase: 'Critique', schema: CRITIQUE_SCHEMA }
)
log(`Critic verdict: ${critique.verdict}; ${critique.missingAngles?.length || 0} missing angles, ${critique.weakClaims?.length || 0} weak claims`)

const finalNote = await agent(
  `${PROJECT}\n\n=== YOUR TASK ===\nProduce the FINAL version of the level-up roadmap and write it to a file.\n\nStart from the draft, then fold in the critic's feedback: add any missing angles, caveat or remove the weak/unverified claims (mark genuinely uncertain market numbers as "approximate — verify"), and fix sequencing/estimate inconsistencies. Keep it comprehensive but tight and opinionated. Preserve the section structure (Executive summary, Where we stand, Strategy, Roadmap Now/Next/Later, Accuracy & evaluation plan, Success metrics, Risks & open questions). End the document with a short "## Sources" section listing the key URLs the research relied on.\n\n=== DRAFT (markdown) ===\n${draft}\n\n=== CRITIC FEEDBACK (JSON) ===\n${JSON.stringify(critique)}\n\n=== LANDSCAPE BRIEF (JSON, for source URLs and grounding) ===\n${JSON.stringify(brief)}\n\nWrite the finished markdown to the absolute path ${ROOT}/analysis/LEVEL_UP_PLAN.md (overwrite if it exists). Then return a 6-10 line plain-text executive summary of the plan (the top bet, the Now-phase initiatives, and the headline success metrics) for the human who triggered this.`,
  { label: 'finalize+write', phase: 'Critique', agentType: 'general-purpose' }
)

return {
  artifact: 'analysis/LEVEL_UP_PLAN.md',
  rankedVisions: ranked.map((r) => ({ vision: r.key, avgScore: r.avgScore })),
  criticVerdict: critique.verdict,
  executiveSummary: finalNote,
}
