# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

sentencesplit is a rule-based sentence boundary detection library (derived from pySBD) supporting 24 languages. Pure Python, no external dependencies — only the `re` module. Python 3.11+.

## Commands

All commands must be run through `uv`:

```bash
uv sync --group dev              # Install dev dependencies
uv run pytest --cov=sentencesplit tests/ --color yes  # Full test suite
uv run pytest tests/lang/test_english.py             # Single language tests
uv run pytest tests/regression/                      # Regression tests only
uv run pytest -k "test_name"                         # Run specific test
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run ruff format --check .     # Format check (CI-enforced)
uv build                         # Build sdist/wheel
```

CI runs lint + tests on Python 3.11, 3.12, 3.13, 3.14.

## Architecture

**Segmentation pipeline:** `Segmenter` → `Processor` → sentence list

- `segmenter.py` — Public API. Takes `language` (ISO 639-1), `clean`, `doc_type`, `char_span`, `split_mode` params. Methods: `segment()`, `segment_spans()`, `segment_clean()`, `segment_with_lookahead()`, `should_wait_for_more()`. Also maps processed sentences back to original-text spans via `_match_spans()` and drives lookahead probing.
- `processor.py` — Core logic, organized into two explicit pipelines returned by `_text_processing_phases()` (newline normalization → list-item markers → abbreviation replacement → optional CJK abbreviation rules → numbers / continuous punctuation / numeric refs → special-token protection) and `_boundary_processing_phases()` (terminal marker → exclamation words → between-punctuation → double/quotation punctuation → list parens). After splitting, `split_into_segments()` post-processes, restores placeholders, re-splits at Latin `.) Capital` or CJK quote boundaries, and merges orphan fragments. Reads `split_mode` ("conservative" or "aggressive") for abbreviation ambiguity.
- `language_profile.py` — `LanguageProfile` frozen dataclass, resolved per-language via `LanguageProfile.from_language(lang)`. Centralizes all language-specific hooks the Processor needs: `abbreviation_replacer_cls`, `between_punctuation_cls`, `cjk_abbreviation_rules`, `colon_rule`, `comma_rule`, `latin_uppercase_resplit` flag, and compiled regexes (`sentence_boundary_re`, `quotation_end_re`, etc.). Processor reads everything language-specific through `self.profile` instead of `getattr(lang, ...)`.
- `cleaner.py` — Text normalization (HTML, PDF, escaped chars, newlines). Subclassable per language.
- `abbreviation_replacer.py` — Aho-Corasick automaton for efficient multi-pattern abbreviation matching with pre-compiled caching. Also handles `split_mode`-dependent abbreviation logic.
- `between_punctuation.py` — Handles punctuation inside quotes/parens to prevent false splits.
- `lists_item_replacer.py`, `punctuation_replacer.py`, `exclamation_words.py` — Rule modules invoked from processor phases (list-item marker insertion, placeholder substitution for punctuation protected from splitting, exclamation-word exceptions).
- `languages.py` — `LANGUAGE_CODES` lazy dict mapping ISO 639-1 codes to language classes; modules are imported on first access. Includes 24 natural languages plus the combined profile `en_es_zh` and the domain-specialized `en_legal`.
- `utils.py` — Shared types (`Rule`, `TextSpan`, `SegmentLookahead`) and helpers (`apply_rules`, `ensure_compiled`, Latin-uppercase detection for sentence-start heuristics).
- `spacy_component.py` — Optional spaCy pipeline factory, registered via entry point in `pyproject.toml`.

**Lookahead** (`segment_with_lookahead()` / `should_wait_for_more()`): For streaming use cases. Appends probe suffixes to detect whether the last boundary is stable — if adding plausible continuation tokens changes the final boundary, returns `should_wait_for_more=True`. Script-aware probe stems per language.

**Language modules** (`lang/`): Each language class inherits from `Common` + `Standard` (both from `lang/common/`), optionally mixing in `CJKBoundaryProfile` for Chinese/Japanese/`en_es_zh`, and defines:
- `Abbreviation` class with language-specific abbreviation lists
- Optional nested overrides: `AbbreviationReplacer`, `BetweenPunctuation`, `Cleaner`, `Processor`, `SENTENCE_BOUNDARY_REGEX`, `LATIN_UPPERCASE_RESPLIT` class attribute
- Combined profiles (e.g. `en_es_zh.py`) merge abbreviation lists from multiple languages for multi-language segmentation; `en_legal.py` specializes English for legal text.

**CJK handling** (`lang/common/cjk.py`): `CJKBoundaryProfile` uses CJK sentence-ending punctuation (`。．！？` etc.) + optional closing quotes/brackets and sets `LATIN_UPPERCASE_RESPLIT = False` so `LanguageProfile.latin_uppercase_resplit` is `False` and the Latin resplit heuristic is skipped. `CJKProcessor` (used by `zh` and `ja` via a nested `class Processor(CJKProcessor)`) adds a post-split pass that merges quote continuations like `"…" 他说。` when the language defines `CJK_REPORTING_CLAUSE_REGEX`. `en_es_zh` uses its own `Processor` subclass that re-runs both Latin-paren and CJK-quote resplit logic.

## Adding a New Language

1. Create `tests/lang/test_<language>.py` with Golden Rules (input/expected pairs)
2. Create `sentencesplit/lang/<language>.py` inheriting `Common, Standard`
3. Register in `languages.py` with ISO 639-1 code in `LANGUAGE_CODES`
4. Run tests — follow TDD: Red → Green → Refactor

## Style

- Ruff is the sole linter/formatter. Line length: 127.
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/) — `python-semantic-release` parses them to compute version bumps. Format: `<type>(<optional scope>): <imperative subject>`. Common types: `feat` (→ minor), `fix` (→ patch), `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore`. Breaking changes use `!` after the type/scope (e.g. `feat!: drop Python 3.10`) or a `BREAKING CHANGE:` footer, and trigger a major bump. Keep the subject short, imperative, and specific.
- Bug fixes get a regression test in `tests/regression/` before the fix.
- Public API changes (lookahead, split_mode, spans) go in `tests/test_segmenter.py`.
