# -*- coding: utf-8 -*-
"""Cross-language ``segment()`` regression gate.

Asserts the live engine reproduces the committed 26-language baseline
(``tests/regression/segment_snapshot.json``) byte-for-byte. Any structural change
that perturbs ``segment()`` output on a Golden-Rule or script-sample input
surfaces here as a failing diff.

If a behavior change is *intended*, regenerate the baseline deliberately::

    uv run python -m tests.regression.segment_snapshot --update

then commit ``tests/regression/segment_snapshot.json`` alongside an adjudication
of the changed ``(lang, input)`` pairs. A bare run is read-only and never rewrites
the baseline.
"""

from __future__ import annotations

from tests.regression.segment_snapshot import diff


def _format_records(records: list[dict[str, object]]) -> str:
    lines = [f"{len(records)} (lang,input) snapshot diffs:"]
    for rec in records:
        lines.append(f"  [{rec['kind']}] {rec['lang']}: {rec['input']!r}")
        lines.append(f"      baseline={rec['baseline']!r}")
        lines.append(f"      live    ={rec['live']!r}")
    lines.append(
        "If this change is intended, regenerate the baseline with "
        "`uv run python -m tests.regression.segment_snapshot --update` and adjudicate "
        "each changed (lang,input) pair."
    )
    return "\n".join(lines)


def test_segment_snapshot_matches_baseline() -> None:
    records = diff()
    assert records == [], _format_records(records)
