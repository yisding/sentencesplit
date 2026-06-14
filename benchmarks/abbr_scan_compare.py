"""Head-to-head: our Aho-Corasick abbreviation scan vs a pySBD-style `in` loop.

Settles which abbreviation-*discovery* mechanism is faster at each input size.
Both find the identical set of present abbreviations; this times only that
discovery step (not the per-occurrence regex replacement that follows it).

Finding (see analysis/SHORT_STRING_LATENCY_PLAN.md §2a): our pure-Python
automaton is faster on short input; the `in` loop only overtakes around
~100-150 chars. So the scan is *not* the short-string bottleneck — it is ~3% of
the call — and must not be replaced.

Run with:
    uv run python benchmarks/abbr_scan_compare.py
"""

from __future__ import annotations

import time

from sentencesplit.abbreviation_replacer import _AbbreviationData
from sentencesplit.languages import LANGUAGE_CODES

_MEDIUM = (
    "dr. smith went to washington. he arrived on jan. 5th at 3 p.m. the model is gpt 3.1 and it is fast. "
    "that is all for now. goodbye. she paid $4.50 for the u.s. edition (vol. 2, p. 17). mr. lee agreed."
)
CASES = {
    "tiny (15c)": "dr. smith left.",
    "short (87c)": "dr. smith went to washington. he arrived on jan. 5th at 3 p.m. and met with sen. jones.",
    "medium (198c)": _MEDIUM,
    "large (4k)": " ".join([_MEDIUM] * 20),
    "huge (40k)": " ".join([_MEDIUM] * 200),
}


def _bench(fn, text: str) -> float:
    iters = 20000 if len(text) < 300 else (3000 if len(text) < 6000 else 300)
    for _ in range(50):
        fn(text)
    t0 = time.perf_counter()
    for _ in range(iters):
        fn(text)
    return (time.perf_counter() - t0) / iters * 1e6  # us/call


def main() -> None:
    data = _AbbreviationData(LANGUAGE_CODES["en"].Abbreviation)
    automaton = data.automaton
    # The automaton is keyed on "<abbr>." (the trailing period pre-filter), so the
    # equivalent naive loop tests for "<abbr>." too.
    abbr_keys = [a[1] + "." for a in data.abbreviations]  # stripped, lowercased, + '.'

    def ac_scan(text: str) -> set[int]:
        return automaton.search(text)

    def in_loop(text: str) -> set[int]:
        return {i for i, a in enumerate(abbr_keys) if a in text}

    print(f"abbreviation discovery: Aho-Corasick vs `in` loop  ({len(abbr_keys)} patterns)")
    print("=" * 60)
    print(f"{'input':<16}{'AC us':>10}{'in us':>10}{'winner':>10}{'ratio':>8}")
    print("-" * 60)
    for name, text in CASES.items():
        assert ac_scan(text) == in_loop(text), f"match-set mismatch for {name}"
        ac = _bench(ac_scan, text)
        inf = _bench(in_loop, text)
        winner = "AC" if ac < inf else "in"
        print(f"{name:<16}{ac:>10.2f}{inf:>10.2f}{winner:>10}{inf / ac:>8.2f}")
    print("-" * 60)
    print("ratio = in/AC (>1 means AC faster). Match-sets verified identical.")


if __name__ == "__main__":
    main()
