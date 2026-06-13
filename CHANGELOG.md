<!-- version list -->

# v0.1.0 (Unreleased)
- feat: support free-threaded (no-GIL) Python builds.
- refactor(lang): remove the hard-coded sentence-starter word lists; route starter/abbreviation boundary decisions through `split_mode` instead, with the prior behavior characterized by new split-mode tests.
- fix(abbrev): route dotted acronyms and two-letter initialisms through `split_mode`; scope the standalone `I` boundary restoration and preserve abbreviations during quoted resplit.
- fix(lang): resplit `en_es_zh` multi-terminator boundaries; restore empty `AbbreviationReplacer` overrides so languages no longer inherit English starters; preserve Kazakh and Russian abbreviation handling.
- fix(lookahead): ignore boundary zero-width characters and linearize zero-width stripping before closers.
- fix(processor): bound sentinel delimiter selection and delimit the sentinel escape fallback.
- fix(en): narrow the all-caps imprint abbreviation guard.
- fix(list): preserve lowercase numbered-item splits.
- fix(spacy): preserve the positional `language` argument.
- fix(security): avoid repeated boundary-lookahead slicing.
- test: reorganize the suite structure and consolidate shared test helpers.
- ci: pin `uv run` interpreters.

# v0.0.5 (2026-06-12)
- feat(api): add `list_languages()` discovery, package metadata, and a zero-dependency guard; add `register_language`/`unregister_language`; validate `doc_type`; add a package-rooted exception hierarchy.
- feat(stream): add `StreamSegmenter` for first-class streaming segmentation.
- feat(split_mode): generalize `split_mode` into a 3-level oversplit/undersplit bias and apply the dials in the German and `en_es_zh` replacer overrides.
- deprecate(api): soft-deprecate the `char_span` parameter (`.. deprecated:: 0.0.5`). It is retained indefinitely as a convenience alias with no planned removal; prefer `segment_spans()`. First use now emits a one-time `DeprecationWarning`.
- fix(spans): `segment_spans()` now guarantees a byte-faithful round-trip back to the original text, enforced by new property-based tests.
- fix(stream): drive bookkeeping on byte-exact spans to stop zero-width drift; hold non-final spans abutting a terminal cluster; compact the buffer at confirmed boundaries; keep the `char_span` flush type contract for trailing whitespace; re-segment only the unemitted tail.
- fix(cleaner): harden HTML/TOC handling against ReDoS and quadratic backtracking; fix escaped-HTML prose, escaped-newline order, and PDF de-hyphenation.
- fix(processor): protect input sentinels and restore sentinel escapes atomically to keep the round-trip safe; re-split multi-character terminators and multi-sentence quotations before a capital; fix orphan merge.
- fix(abbreviation): avoid quadratic initials scans; keep initials-chain walks ASCII-only; protect number abbreviations before unknown placeholders; keep chained single-letter initials attached to a surname.
- fix(ellipsis): protect leading dot-runs and keep glued run-on scans linear.
- fix(lang): per-language boundary fixes for Spanish (period-before-comma, trailing zero-width-space phantoms), Dutch opening-quote, German consecutive ordinals, Greek multi-period abbreviations, Russian abbreviations/inline language tags, and Arabic-script period protection.
- perf: lazily resolve package metadata to cut import time; dedup abbreviation occurrences and cache `LanguageProfile.from_language`.
- refactor(api): add `__all__`; type the mode parameters as `Literal` aliases; add a scoped mypy gate for the public type surface.
- test(regression-gate): add a hermetic CI gate scoring `sentencesplit` against committed gold output.
- docs: document the versioning and output-stability policy; document the `StreamSegmenter` wrapper in the README; expand project URLs and add `SECURITY.md` + `CITATION.cff`.
- ci: pin the PyPI publish action and CI actions to immutable SHAs; assert the built wheel ships `py.typed` and all language modules; set least-privilege token permissions.

# v0.0.4 (2026-05-10)
- feat(api): export `TextSpan` from the package root.
- feat(typing): add a `py.typed` marker so type checkers see inline types.
- build: add a `spacy` optional-dependency group and bump `uv-build` to 0.11.x.
- docs: add a pull request template; ci: add Dependabot for GitHub Actions.

# v0.0.3 (2026-04-12)
- refactor: split the processor into explicit text-processing and boundary-processing phase pipelines (`_text_processing_phases`, `_boundary_processing_phases`).
- ci: decouple the release workflow from the PyPI publish workflow so tags can be republished independently.
- docs: refresh `CLAUDE.md`, `AGENTS.md`, and `README.md` for accuracy and onboarding.

# v0.0.2 (2026-04-11)
- feat(lang): add `Eq.` and `Pt.` to number abbreviations and tighten en_es_zh abbreviation handling.
- fix: handle non-ASCII boundary characters across the abbreviation paths without over-splitting CJK text.
- fix: exclude CJK from the Latin uppercase resplit heuristic; restrict sentence-start detection to Latin uppercase only.
- fix(en_es_zh): broaden abbreviation protection so CJK after an abbreviation does not trigger a false split.
- fix: CJK quote-split regression and compact AM/PM matching.
- refactor: deduplicate helpers and document broadened quotation regexes.
- ci: allow manual PyPI publishes and call the publish workflow from the release workflow.

# v0.0.1 (2026-04-08)
- First PyPI release under the `sentencesplit` name (project renamed from `pysbd`, derived with attribution).
- feat(lang): add `en_legal` profile specialized for legal-document segmentation, plus common English abbreviations to prevent false splits.
- feat: add Python 3.14 to the supported matrix.
- perf: pre-compile regex patterns, lazy language loading, and cache class references; `LANGUAGE_CODES` now implements `MutableMapping` for dict-compatible mutation.
- fix: prevent `ListItemReplacer` from mis-splitting `v.` as an alphabetical list item.
- fix(lang): improve Italian abbreviation handling.
- fix: CJK-related boundary fixes for Chinese and Japanese.
- ci: add `uv`-based release and publish GitHub Actions workflows.
- docs: add release instructions.

# v0.4.0
- Renamed package from `pysbd` to `sentencesplit`. The project is derived from pySBD with clear attribution.

# v0.3.4
- 🐛 Fix trailing period/ellipses with spaces - #83
- 🐛 Regex escape for parenthesis - #87

# v0.3.3
- 🐛 Better handling consecutive periods and reserved special symbols - allenai/scholarphi#114
- Add CONTRIBUTING.md

# v0.3.2
- 🐛 ✅ Enforce clean=True when doc_type="pdf" - \#75

# v0.3.1
- 🚑 ✅ Handle Newline character & update tests

# v0.3.0
-   ✨ 💫  Support Multiple languages - \#2
-   🏎⚡️💯 Benchmark across Segmentation Tools, Libraries and Algorithms
-   🎨 ♻️ Update sentence char_span logic
-   ⚡️  Performance improvements - \#41
-   ♻️🐛 Refactor AbbreviationReplacer

# v0.3.0rc
-   ✨ 💫 sent `char_span` through with spaCy & regex approach - \#63
-   ♻️ Refactoring to support multiple languages
-   ✨ 💫Initial language support for - Hindi, Marathi, Chinese, Spanish
-   ✅ Updated tests - more coverage & regression tests for issues
-   👷👷🏻‍♀️ GitHub actions for CI-CD
-   💚☂️ Add code coverage - coverage.py Add Codecov
-   🐛 Fix incorrect text span & vanilla pysbd vs spacy output discrepancy - \#49, \#53, \#55 , \#59
-   🐛 Fix `NUMBERED_REFERENCE_REGEX` for zero or one time - \#58
-   🔐Fix security vulnerability bleach - \#62


# v0.2.3
-   🐛 Performance improvement in `abbreviation_replacer`- \#50

# v0.2.2
-   🐛 Fix unbalanced parenthesis - \#47

# v0.2.1
-   ✨pySBD as a spaCy component through entrypoints

# v0.2.0
-   ✨Add `char_span` parameter (optional) to get sentence & its (start, end) char offsets from original text
-   ✨pySBD as a spaCy component example
-   🐛 Fix double question mark swallow bug - \#39

# v0.1.5
-   🐛 Handle text with only punctuations - \#36
-   🐛 Handle exclamation marks at EOL- \#37

# v0.1.4
-   ✨ ✅ Handle intermittent punctuations - \#34

# v0.1.3
-   🐛 Fix `lists_item_replacer` - \#29
-   🐛 Fix & ♻️refactor `replace_multi_period_abbreviations` - \#30
-   🐛 Fix `abbreviation_replacer` - \#31
-   ✅ Add regression tests for issues

# v0.1.2
-   🐛BugFix - IndexError of `scanlists` function

# v0.1.1
-   English language support only
-   Support for oother languages - WIP

# v0.1.0
-   Initial Release
