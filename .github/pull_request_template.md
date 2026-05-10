## Summary

<!-- 1-3 bullets describing the change and the user-visible effect. -->

## Type of change

<!-- Match a Conventional Commit type: feat / fix / perf / refactor / docs / test / build / ci / chore. -->

## Linked issues

<!-- Closes #N for bug fixes. Skip if not applicable. -->

## Input / output examples

<!-- Required for language, lookahead, split_mode, spans, or spaCy behavior changes. Show before vs after. -->

```python
# Before
seg.segment("...")
# [...]

# After
seg.segment("...")
# [...]
```

## Test evidence

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run pytest --cov=sentencesplit tests/`
- [ ] Added a regression test in `tests/regression/test_issues.py` (for bug fixes) or a Golden Rule in `tests/lang/test_<language>.py` (for language-rule changes).

## Notes for reviewers

<!-- Anything reviewers should focus on: tradeoffs, follow-up work, perf concerns, etc. -->
