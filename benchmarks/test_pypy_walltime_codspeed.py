"""CodSpeed **walltime** benchmarks, used for the PyPy job.

Why a separate file from ``test_latency_codspeed.py``:

* PyPy can't use CodSpeed's default ``simulation`` (instruction-count) mode —
  that relies on Valgrind-style instrumentation of the CPython interpreter, and
  PyPy's JIT makes an instruction count both impossible to collect and
  meaningless. PyPy is therefore benchmarked in ``walltime`` mode instead.
* CodSpeed does not support reporting the *same* benchmark id twice for one
  commit. The CPython suite already reports ``test_latency_codspeed.py::…`` ids
  under ``simulation``; these live in their own file so the PyPy walltime job
  reports a disjoint set of ids (``test_pypy_walltime_codspeed.py::…``) and the
  two jobs never collide.

The benchmarked code paths mirror the CPython latency suite (same shared corpus
from ``benchmarks._samples``) so PyPy vs CPython numbers line up case-for-case on
the dashboard. These track PyPy performance over time / catch PyPy-specific
regressions; CPython regression detection stays on the deterministic
``simulation`` job.

Run locally::

    # CPython smoke (no measurement)
    uv run --no-default-groups --group bench pytest benchmarks/test_pypy_walltime_codspeed.py
    # PyPy walltime measurement
    pypy3.11 -m pytest benchmarks/test_pypy_walltime_codspeed.py --codspeed --codspeed-mode=walltime
"""

from __future__ import annotations

import pytest

from benchmarks._samples import MULTILINGUAL, SAMPLES, STREAM_TOKENS
from sentencesplit import Segmenter, StreamSegmenter


@pytest.fixture(scope="module")
def en_segmenter() -> Segmenter:
    # Construction (language profile + abbreviation automaton) is amortized in
    # real reuse; benchmark only the per-call work.
    return Segmenter(language="en", clean=False, char_span=False)


@pytest.fixture(scope="module")
def segmenter_cache() -> dict[str, Segmenter]:
    return {}


@pytest.mark.parametrize("sample", ["short", "medium", "large"])
def test_segment(benchmark, en_segmenter: Segmenter, sample: str) -> None:
    text = SAMPLES[sample]
    benchmark(en_segmenter.segment, text)


@pytest.mark.parametrize("sample", ["short", "medium", "large"])
def test_should_wait_for_more(benchmark, en_segmenter: Segmenter, sample: str) -> None:
    text = SAMPLES[sample]
    benchmark(en_segmenter.should_wait_for_more, text)


@pytest.mark.parametrize("language", ["zh", "ru"])
def test_segment_multilingual(benchmark, segmenter_cache: dict[str, Segmenter], language: str) -> None:
    segmenter = segmenter_cache.setdefault(language, Segmenter(language=language, clean=False, char_span=False))
    benchmark(segmenter.segment, MULTILINGUAL[language])


@pytest.mark.parametrize("mode", ["conservative", "aggressive"])
def test_stream_feed_document(benchmark, mode: str) -> None:
    def run() -> None:
        stream = StreamSegmenter(language="en", buffering_mode=mode)
        for tok in STREAM_TOKENS:
            stream.feed(tok)
        stream.flush()

    benchmark(run)
