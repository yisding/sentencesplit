# Architecture Notes

This document records the current internal shape of `sentencesplit`. It is a
behavior-preserving refactor guide, not a public API promise.

## Layers

The library has four main layers:

1. Public API: `Segmenter`, `StreamSegmenter`, spaCy integration, and shared
   return types in `utils.py`.
2. Language configuration: `languages.py`, `LanguageProfile`, language modules
   under `sentencesplit/lang/`, and shared profiles under `lang/common/`.
3. Rule pipeline: `Processor` and helper modules that protect abbreviations,
   punctuation, list markers, quotes, and language-specific boundary cases.
4. Projection: `Segmenter` maps processor output back onto the original input
   for `segment_spans()` and filters the projected text for `segment()`.

## Processor Pipeline

`Processor.process()` is the core segmentation path for non-streaming text:

1. Reject empty input early.
2. Escape any user-provided single-character internal sentinels through
   `_sentinel.py`.
3. Normalize and protect text through the language profile hooks.
4. Apply boundary-processing phases, including exclamation-word, quote,
   list-item, and punctuation rules.
5. Split on boundary markers, then resplit or merge fragments for quotes,
   orphan closers, and split-mode-specific ambiguity.
6. Restore escaped user-provided sentinels atomically before returning strings.

Language modules should override the narrow hook methods documented in
`CONTRIBUTING.md` when possible. A full `process()` override should be reserved
for languages whose pipeline order is genuinely different.

## Invariants

- `segment_spans(text, clean=False)` tiles the original input with no gaps,
  overlaps, or reordered text. Each returned `TextSpan.text` must equal
  `text[start:end]`.
- `segment(text, clean=False)` is a projection of `segment_spans()`: it may drop
  whitespace-only or zero-width-only spans, but it must not invent content.
- `clean=True` may rewrite text and therefore cannot produce source spans.
  `doc_type="pdf"` requires `clean=True`.
- Internal sentinels are private intermediate representation. If source text
  contains a single-character sentinel, `_sentinel.py` must escape it to an
  absent token and restore it after processing.
- Multi-character `&X&` sentinels are intentionally not escaped. They overlap
  with cleaner output and remain an internal limitation for literal source text
  in `clean=True` mode.
- `LanguageProfile` instances are cached and should be treated as immutable
  after construction. Registry mutation belongs at startup or in tests.
- `split_mode` changes only ambiguous boundary decisions. It should not change
  language registration, cleaning, or source-span projection rules.
- Streaming segmentation may resegment the unemitted tail, but it must not alter
  already emitted text. `clean=True` is not supported for streaming.

## Change Protocol

- For behavior changes, add a regression or language golden-rule test before
  changing rules.
- For refactors, keep existing public output identical and prefer contract tests
  over golden snapshot rewrites.
- Keep runtime dependencies at zero. Optional integrations and benchmarks belong
  behind extras.
- Place reusable rule-free mechanics in focused private modules, such as
  `_sentinel.py`; keep language heuristics near `Processor` or the relevant
  language profile.
