# Repository Guidelines

## Project Structure & Module Organization
Core package code lives in `sentencesplit/`:
- `segmenter.py`: public `Segmenter` API, helper methods such as `segment_spans()`, `segment_clean()`, `segment_with_lookahead()`, `should_wait_for_more()`, and `split_mode` handling.
- `processor.py`, `abbreviation_replacer.py`, `punctuation_replacer.py`, `between_punctuation.py`, `cleaner.py`, `lists_item_replacer.py`: the main rule pipeline and boundary heuristics.
- `languages.py`: registry of supported ISO codes, including combined profiles such as `en_es_zh`.
- `spacy_component.py`: spaCy factory registered through `spacy_factories`.
- `utils.py`: shared types such as `TextSpan` and `SegmentLookahead`.
- `lang/`: language-specific rules plus `lang/common/` shared base profiles.
- `clean/`: normalization rules.

Tests are in `tests/`:
- `tests/lang/test_<language>.py` for Golden Rules by language.
- `tests/regression/test_issues.py` for issue-driven regressions.
- `tests/test_segmenter.py` for public API behavior, lookahead, spans, and `split_mode`.
- `tests/test_languages.py`, `tests/test_cleaner.py`, and similar `tests/test_*.py` files for registry and pipeline units.

Docs and research assets:
- `README.md`: install, public API, lookahead behavior, multi-language usage, and spaCy integration.
- `CONTRIBUTING.md`: contribution workflow and TDD guidance.
- `analysis/`: comparison scripts plus checked-in JSON/Markdown reports.
- `benchmarks/`: benchmark helpers and golden-rule benchmark data.
- `examples/`: runnable examples, including the spaCy component and timing script.

## Build, Test, and Development Commands
- Always run Python tooling through `uv` (for example: `uv run pytest`, not bare `pytest`).
- `uv sync --group dev`: install pinned dev dependencies.
- `uv run pytest --cov=sentencesplit tests/ --color yes`: run full test suite with coverage.
- `uv run pytest tests/test_segmenter.py`: run the public API and lookahead coverage.
- `uv run pytest tests/lang/test_english.py`: run a single language Golden Rules file.
- `uv run pytest tests/regression/`: run regression coverage only.
- `uv run ruff check .`: lint checks.
- `uv run ruff format --check .`: formatting check (CI-enforced).
- `uv run ruff format .`: apply formatting locally.
- `uv build`: build sdist/wheel using `uv_build`.

CI in `.github/workflows/python-package.yml` runs lint + tests on Python 3.11, 3.12, 3.13, and 3.14; keep local checks aligned before opening a PR.

## Coding Style & Naming Conventions
- Python 3.11+ with 4-space indentation; the package stays pure Python with no runtime dependencies.
- Ruff is the source of truth for linting/formatting (`line-length = 127`).
- Use `snake_case` for modules/functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep public API additions aligned with `README.md` examples and `sentencesplit/__init__.py` exports.
- For new languages, follow existing naming: `sentencesplit/lang/<language>.py`, register the ISO code in `sentencesplit/languages.py`, and add `tests/lang/test_<language>.py`.
- If you touch spaCy integration, keep the import optional and compatible with the entry point in `pyproject.toml`.

## Testing Guidelines
- Framework: `pytest` with `pytest-cov`.
- Add or update tests with every behavior change.
- Prefer TDD flow from `CONTRIBUTING.md`: Red -> Green -> Refactor.
- Put public `Segmenter` API changes, helper methods, lookahead rules, and `split_mode` coverage in `tests/test_segmenter.py`.
- For bug fixes, add a regression test first in `tests/regression/test_issues.py` unless the behavior is language-specific, then implement the fix.
- For language-rule changes, update or add the relevant Golden Rules file in `tests/lang/` and verify the language remains registered in `tests/test_languages.py`.

## Commit & Pull Request Guidelines
- Commit messages in this repo are short, imperative, and specific (for example: `Refine lookahead handling for quoted terminal periods`).
- Keep commits focused; separate refactors/formatting from behavior changes when practical.
- PRs should include a clear problem statement and scope, linked issue(s) for bug fixes, test evidence (`uv run pytest ...`), and representative input/output examples for language, lookahead, `split_mode`, or spaCy behavior changes.
