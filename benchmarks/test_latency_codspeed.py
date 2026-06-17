"""CodSpeed benchmarks for the latency-sensitive paths.

These are deterministic (instruction-count) benchmarks run in CI by
``.github/workflows/codspeed.yml`` via ``pytest --codspeed``. CodSpeed measures
CPU instructions rather than wall-clock time, so the numbers are stable across
noisy shared runners and a per-PR regression shows up as a real instruction
delta rather than runner jitter.

Scope / isolation:
  * The main CI points pytest at ``tests/`` only, so it never collects this file
    and the ``pytest-codspeed`` plugin stays out of the default test matrix.
  * The plugin lives in the ``bench`` dependency group, not ``dev``.

Run locally (smoke test, no measurement)::

    uv run --no-default-groups --group bench pytest benchmarks/test_latency_codspeed.py

With the ``pytest-codspeed`` plugin installed, the ``benchmark`` fixture simply
calls the target once when ``--codspeed`` is absent, so these double as cheap
import/smoke tests.
"""

from __future__ import annotations

import pytest

from benchmarks._samples import LEGAL
from benchmarks._samples import MULTILINGUAL as _MULTILINGUAL
from benchmarks._samples import SAMPLES as _SAMPLES
from benchmarks._samples import STREAM_TOKENS as _STREAM_TOKENS
from sentencesplit import Segmenter, StreamSegmenter


@pytest.fixture(scope="module")
def en_segmenter() -> Segmenter:
    # Construction (language profile + abbreviation automaton) is amortized
    # across the stream, matching real reuse; benchmark only the per-call work.
    return Segmenter(language="en", clean=False)


@pytest.fixture(scope="module")
def en_legal_segmenter() -> Segmenter:
    # The abbreviation-dense domain profile; pairs with the LEGAL sample to track
    # the abbreviation engine on the workload it most affects.
    return Segmenter(language="en_legal", clean=False)


@pytest.fixture(scope="module")
def segmenter_cache() -> dict[str, Segmenter]:
    # Reused across parametrized cases so per-language construction stays out of
    # the timed callable.
    return {}


@pytest.mark.parametrize("sample", ["short", "medium", "large"])
def test_segment(benchmark, en_segmenter: Segmenter, sample: str) -> None:
    text = _SAMPLES[sample]
    benchmark(en_segmenter.segment, text)


@pytest.mark.parametrize("sample", ["short", "medium", "large"])
def test_segment_spans(benchmark, en_segmenter: Segmenter, sample: str) -> None:
    # segment_spans is the canonical span API (the char_span constructor arg
    # was removed), so the span-mapping path gets its own regression guard.
    text = _SAMPLES[sample]
    benchmark(en_segmenter.segment_spans, text)


def test_segment_legal_dense(benchmark, en_legal_segmenter: Segmenter) -> None:
    # Abbreviation-dense legal text through the en_legal profile: the workload the
    # PeriodClassifier is most visible on.
    benchmark(en_legal_segmenter.segment, LEGAL)


@pytest.mark.parametrize("sample", ["short", "medium", "large"])
def test_should_wait_for_more(benchmark, en_segmenter: Segmenter, sample: str) -> None:
    text = _SAMPLES[sample]
    benchmark(en_segmenter.should_wait_for_more, text)


@pytest.mark.parametrize("language", ["zh", "ru"])
def test_segment_multilingual(benchmark, segmenter_cache: dict[str, Segmenter], language: str) -> None:
    segmenter = segmenter_cache.setdefault(language, Segmenter(language=language, clean=False))
    benchmark(segmenter.segment, _MULTILINGUAL[language])


@pytest.mark.parametrize("mode", ["conservative", "aggressive"])
def test_stream_feed_document(benchmark, mode: str) -> None:
    def run() -> None:
        stream = StreamSegmenter(language="en", buffering_mode=mode)
        for tok in _STREAM_TOKENS:
            stream.feed(tok)
        stream.flush()

    benchmark(run)
