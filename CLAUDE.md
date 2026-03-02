# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

sentencesplit is a rule-based sentence boundary detection library (derived from pySBD) supporting 23 languages. Pure Python, no external dependencies — only the `re` module. Python 3.11+.

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

CI runs lint + tests on Python 3.11, 3.12, 3.13.

## Architecture

**Segmentation pipeline:** `Segmenter` → `Processor` → sentence list

- `segmenter.py` — Public API. Takes `language` (ISO 639-1), `clean`, `doc_type`, `char_span` params. Methods: `segment()`, `segment_spans()`, `segment_clean()`.
- `processor.py` — Core logic: abbreviation replacement, punctuation processing, boundary detection, segment post-processing. Contains `LATIN_UPPERCASE_RESPLIT` heuristic (disabled for CJK).
- `cleaner.py` — Text normalization (HTML, PDF, escaped chars, newlines). Subclassable per language.
- `abbreviation_replacer.py` — Aho-Corasick automaton for efficient multi-pattern abbreviation matching with pre-compiled caching.
- `between_punctuation.py` — Handles punctuation inside quotes/parens to prevent false splits.
- `languages.py` — `LANGUAGE_CODES` dict mapping ISO 639-1 codes to language classes.

**Language modules** (`lang/`): Each language inherits from `Common` + `Standard` (or `CJKBoundaryProfile` for Chinese/Japanese) and defines:
- `Abbreviation` class with language-specific abbreviation lists
- Optional overrides: `AbbreviationReplacer`, `BetweenPunctuation`, `Cleaner`, `SENTENCE_BOUNDARY_REGEX`

**CJK handling** (`lang/common/cjk.py`): `CJKBoundaryProfile` uses CJK sentence-ending punctuation (`。．！？` etc.) + optional closing quotes/brackets, and disables the Latin uppercase resplit heuristic.

## Adding a New Language

1. Create `tests/lang/test_<language>.py` with Golden Rules (input/expected pairs)
2. Create `sentencesplit/lang/<language>.py` inheriting `Common, Standard`
3. Register in `languages.py` with ISO 639-1 code in `LANGUAGE_CODES`
4. Run tests — follow TDD: Red → Green → Refactor

## Style

- Ruff is the sole linter/formatter. Line length: 127.
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- Commit messages: short, imperative, specific.
- Bug fixes get a regression test in `tests/regression/` before the fix.
