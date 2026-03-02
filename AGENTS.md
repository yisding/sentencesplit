# Repository Guidelines

## Project Structure & Module Organization
Core library code lives in `sentencesplit/`:
- `segmenter.py`, `processor.py`, `cleaner.py`: segmentation pipeline.
- `lang/`: language-specific rules (one module per language).
- `clean/`: text normalization rules.

Tests are in `tests/`:
- `tests/lang/test_<language>.py` for Golden Rules by language.
- `tests/regression/test_issues.py` for issue-driven regressions.
- `tests/test_*.py` for core behavior.

Benchmarks and exploratory scripts are in `benchmarks/` and top-level `analyze_*.py`/`compare_splitters.py`. Usage examples are in `examples/`.

## Build, Test, and Development Commands
- Always run Python tooling through `uv` (for example: `uv run python script.py`, not `python script.py`).
- `uv sync --group dev`: install pinned dev dependencies.
- `uv run pytest --cov=sentencesplit tests/ --color yes`: run full test suite with coverage.
- `uv run ruff check .`: lint checks.
- `uv run ruff format --check .`: formatting check (CI-enforced).
- `uv run ruff format .`: apply formatting locally.
- `uv build`: build sdist/wheel using `uv_build`.

CI runs lint + tests on Python 3.11, 3.12, and 3.13; keep local checks aligned before opening a PR.

## Coding Style & Naming Conventions
- Python 3.11+ with 4-space indentation.
- Ruff is the source of truth for linting/formatting (`line-length = 127`).
- Use `snake_case` for modules/functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- For new languages, follow existing naming: `sentencesplit/lang/<language>.py` and test file `tests/lang/test_<language>.py`.

## Testing Guidelines
- Framework: `pytest` with `pytest-cov`.
- Add or update tests with every behavior change.
- Prefer TDD flow from `CONTRIBUTING.md`: Red -> Green -> Refactor.
- For bug fixes, add a regression test first in `tests/regression/` (or relevant language test), then implement the fix.

## Commit & Pull Request Guidelines
- Commit messages in this repo are short, imperative, and specific (for example: `Add Spanish parity for challenging abbreviation boundaries`).
- Keep commits focused; separate refactors/formatting from behavior changes when practical.
- PRs should include a clear problem statement and scope, linked issue(s) for bug fixes, test evidence (`uv run pytest ...`), and notes on language-rule changes with representative input/output examples.
