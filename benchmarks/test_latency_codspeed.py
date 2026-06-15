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

from sentencesplit import Segmenter, StreamSegmenter

SHORT = "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones."
MEDIUM = (
    "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
    "The model is GPT 3.1 and it is fast. That is all for now. Goodbye. "
    "She paid $4.50 for the U.S. edition (vol. 2, p. 17). Mr. Lee agreed."
)
# A larger realistic document: repeat the medium sample to ~5 KB of prose.
LARGE = " ".join([MEDIUM] * 20)

# Abbreviation-dense legal prose. General prose spends little time in the
# abbreviation phase, so the V2 PeriodClassifier change is barely visible there;
# this dense sample (run through the en_legal profile below) is the workload that
# actually guards the engine rewrite against regression.
LEGAL = (
    "Dr. Smith, Jr., Ph.D., M.D., et al., v. U.S. Dept. of Justice, No. 21-1234, "
    "slip op. at 3 (2d Cir. Mar. 5, 2021). See 5 U.S.C. § 552(a)(4)(B); cf. Fed. R. "
    "Civ. P. 12(b)(6). Mr. Lee, Esq., of Lee & Co., LLP, argued for appellant. The "
    "Hon. J. Roberts, C.J., wrote for the majority. Compare id. at 5, with Ibid. n.7."
)

_SAMPLES = {"short": SHORT, "medium": MEDIUM, "large": LARGE}
# Whitespace-delimited token stream (LLM/ASR-like) for the streaming benchmark.
_STREAM_TOKENS = [tok + " " for tok in MEDIUM.split(" ")]

# Non-Latin scripts exercise different code paths (CJK has no whitespace word
# boundaries and uses the CJK resplit pass; Cyrillic exercises the Latin-style
# abbreviation/resplit rules over a non-ASCII alphabet), so they catch
# regressions the English samples would miss.
_MULTILINGUAL = {
    "zh": "史密斯博士去了华盛顿。他于1月5日下午3点到达。一切都很顺利。再见。",
    "ru": "Доктор Иванов поехал в Москву. Он прибыл 5 января в 15:00. Всё прошло хорошо. До свидания.",
}


@pytest.fixture(scope="module")
def en_segmenter() -> Segmenter:
    # Construction (language profile + abbreviation automaton) is amortized
    # across the stream, matching real reuse; benchmark only the per-call work.
    return Segmenter(language="en", clean=False)


@pytest.fixture(scope="module")
def en_legal_segmenter() -> Segmenter:
    # The abbreviation-dense domain profile; pairs with the LEGAL sample to track
    # the V2 abbreviation engine on the workload it most affects.
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
    # segment_spans is the canonical span API in v2 (the char_span constructor arg
    # was removed), so the span-mapping path gets its own regression guard.
    text = _SAMPLES[sample]
    benchmark(en_segmenter.segment_spans, text)


def test_segment_legal_dense(benchmark, en_legal_segmenter: Segmenter) -> None:
    # Abbreviation-dense legal text through the en_legal profile: the workload the
    # V2 PeriodClassifier change is most visible on.
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
