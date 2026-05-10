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
