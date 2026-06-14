"""Shared benchmark corpus for the CodSpeed latency suites.

The leading underscore keeps pytest from collecting this as a test module. Both
the CPython instruction-count suite (``test_latency_codspeed.py``) and the PyPy
walltime suite (``test_pypy_walltime_codspeed.py``) import these samples so the
two runtimes exercise identical inputs.
"""

from __future__ import annotations

SHORT = "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones."
MEDIUM = (
    "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
    "The model is GPT 3.1 and it is fast. That is all for now. Goodbye. "
    "She paid $4.50 for the U.S. edition (vol. 2, p. 17). Mr. Lee agreed."
)
# A larger realistic document: repeat the medium sample to ~5 KB of prose.
LARGE = " ".join([MEDIUM] * 20)

SAMPLES = {"short": SHORT, "medium": MEDIUM, "large": LARGE}

# Whitespace-delimited token stream (LLM/ASR-like) for the streaming benchmark.
STREAM_TOKENS = [tok + " " for tok in MEDIUM.split(" ")]

# Non-Latin scripts exercise different code paths (CJK has no whitespace word
# boundaries and uses the CJK resplit pass; Cyrillic exercises the Latin-style
# abbreviation/resplit rules over a non-ASCII alphabet), so they catch
# regressions the English samples would miss.
MULTILINGUAL = {
    "zh": "史密斯博士去了华盛顿。他于1月5日下午3点到达。一切都很顺利。再见。",
    "ru": "Доктор Иванов поехал в Москву. Он прибыл 5 января в 15:00. Всё прошло хорошо. До свидания.",
}
