"""Competitive CodSpeed benchmarks: sentencesplit vs pySBD vs punkt.

Tracks sentencesplit's latency/throughput against the two pure-Python sentence
boundary detectors it is most often compared to:

  * **pySBD** — the rule-based library sentencesplit was derived from.
  * **punkt** — nltk's classic unsupervised statistical tokenizer.

Why only these two: CodSpeed's instrumentation mode measures CPU *instructions*,
which is a fair proxy for wall-clock time only among libraries of the same
execution character. All three here are pure Python, so the comparison is
apples-to-apples. C/Cython tokenizers (spaCy, blingfire, stanza) would have a
very different instruction-to-wallclock ratio and are intentionally excluded —
compare against those with a wall-clock harness (see the ``compare-segmenters``
skill / ``benchmarks/benchmark_sbd_tools.py``) instead.

Reading the results: CodSpeed compares each benchmark against itself across
commits, not library-to-library. To compare the three engines, read the
absolute per-benchmark numbers side by side in the CodSpeed dashboard — the
``[size-ours]`` / ``[size-pysbd]`` / ``[size-punkt]`` rows for one size are
directly comparable (identical input, each engine constructed once outside the
timed call). The per-PR delta still guards each engine against regression.

Run locally (smoke test, no measurement)::

    uv run --no-sync pytest benchmarks/test_competitive_codspeed.py
"""

from __future__ import annotations

import pytest

SHORT = "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones."
MEDIUM = (
    "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
    "The model is GPT 3.1 and it is fast. That is all for now. Goodbye. "
    "She paid $4.50 for the U.S. edition (vol. 2, p. 17). Mr. Lee agreed."
)
LARGE = " ".join([MEDIUM] * 20)
# A larger document (~10 KB) used as a throughput proxy: per-run cost is inversely
# proportional to sentences/sec, so the relative costs rank the engines' throughput.
THROUGHPUT_DOC = " ".join([MEDIUM] * 50)

_SAMPLES = {"short": SHORT, "medium": MEDIUM, "large": LARGE}
_LIBRARIES = ["ours", "pysbd", "punkt"]


@pytest.fixture(scope="module")
def segmenters() -> dict[str, object]:
    """Each engine constructed once; only the per-call segment is benchmarked.

    Construction cost (sentencesplit's automaton, pySBD's compiled rules, punkt's
    pickled model) is amortized exactly as it is in real reuse, so the timed call
    is steady-state segmentation only.
    """
    import nltk
    import pysbd

    import sentencesplit

    ours = sentencesplit.Segmenter(language="en", clean=False)
    sbd = pysbd.Segmenter(language="en", clean=False)
    # Warm punkt so its one-time model load is not measured (nltk caches the
    # loaded tokenizer, so subsequent calls reuse it).
    nltk.sent_tokenize("Warm up the punkt model. It is ready now.")

    return {
        "ours": ours.segment,
        "pysbd": sbd.segment,
        "punkt": nltk.sent_tokenize,
    }


@pytest.mark.parametrize("library", _LIBRARIES)
@pytest.mark.parametrize("size", ["short", "medium", "large"])
def test_segment(benchmark, segmenters: dict[str, object], size: str, library: str) -> None:
    segment = segmenters[library]
    benchmark(segment, _SAMPLES[size])


@pytest.mark.parametrize("library", _LIBRARIES)
def test_throughput(benchmark, segmenters: dict[str, object], library: str) -> None:
    segment = segmenters[library]
    benchmark(segment, THROUGHPUT_DOC)
