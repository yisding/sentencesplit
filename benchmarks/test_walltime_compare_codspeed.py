"""CodSpeed **walltime** benchmarks for a direct CPython-vs-PyPy comparison.

Four benchmarks total — two scenarios, each run on both interpreters and
labelled by interpreter so the pair sits side-by-side on the dashboard:

    test_walltime_segment_medium[cpython]   test_walltime_segment_medium[pypy]
    test_walltime_throughput[cpython]       test_walltime_throughput[pypy]

Both the CPython and the PyPy CodSpeed jobs collect all four ids, but each only
*runs* (and therefore reports) the two matching its own interpreter — the other
two self-skip. So every id is reported exactly once per commit (CodSpeed forbids
reporting the same id twice) while the ``[cpython]`` / ``[pypy]`` pairing makes
the comparison obvious.

Why walltime and not CodSpeed's default ``simulation`` mode: ``simulation``
counts CPU instructions by instrumenting the CPython interpreter, which PyPy's
JIT precludes, so it can't measure PyPy at all. Walltime works on both. The
deterministic CPython-only regression suite stays in ``test_latency_codspeed.py``
(``simulation`` mode); this file exists purely for the cross-interpreter
wall-clock comparison.

Run locally::

    pytest benchmarks/test_walltime_compare_codspeed.py --codspeed --codspeed-mode=walltime          # CPython
    pypy3.11 -m pytest benchmarks/test_walltime_compare_codspeed.py --codspeed --codspeed-mode=walltime  # PyPy
"""

from __future__ import annotations

import platform

import pytest

from benchmarks._samples import LARGE, MEDIUM
from sentencesplit import Segmenter

# "cpython" or "pypy" — the running interpreter, used to pick which labelled
# half of each scenario actually executes here.
_IMPL = platform.python_implementation().lower()


def _only(impl: str) -> None:
    if impl != _IMPL:
        pytest.skip(f"benchmark pinned to {impl}; running under {_IMPL}")


@pytest.fixture(scope="module")
def en_segmenter() -> Segmenter:
    # Construction is amortized in real reuse; benchmark only the per-call work.
    return Segmenter(language="en", clean=False)


@pytest.mark.parametrize("impl", ["cpython", "pypy"])
def test_walltime_segment_medium(benchmark, en_segmenter: Segmenter, impl: str) -> None:
    """Per-call latency: segment a short multi-sentence paragraph."""
    _only(impl)
    benchmark(en_segmenter.segment, MEDIUM)


@pytest.mark.parametrize("impl", ["cpython", "pypy"])
def test_walltime_throughput(benchmark, en_segmenter: Segmenter, impl: str) -> None:
    """Batch throughput: segment a ~5 KB document in one call."""
    _only(impl)
    benchmark(en_segmenter.segment, LARGE)
