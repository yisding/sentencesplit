"""Differential profiler: sentencesplit vs pySBD on identical input.

Answers "what *exactly* makes us slower than pySBD per call" by profiling both
on the same text and surfacing the operation-level deltas that matter:

  * per-call wall time (ours vs pySBD),
  * count + time of every regex op (sub / findall / search / finditer / split)
    per call — the clearest "we run more passes" signal,
  * total time spent inside the `re` module,
  * the top tottime functions for each library, side by side.

Run with:
    uv run python benchmarks/differential_profile.py --size short
    uv run python benchmarks/differential_profile.py --size medium --top 18
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import time
from collections import Counter

import pysbd

import sentencesplit

SHORT = "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones."
MEDIUM = (
    "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
    "The model is GPT 3.1 and it is fast. That is all for now. Goodbye. "
    "She paid $4.50 for the U.S. edition (vol. 2, p. 17). Mr. Lee agreed."
)
LARGE = " ".join([MEDIUM] * 20)
_SAMPLES = {"short": SHORT, "medium": MEDIUM, "large": LARGE}

_REGEX_OPS = ("sub", "findall", "search", "match", "finditer", "split", "fullmatch")


def _walltime(fn, text: str, iters: int) -> float:
    for _ in range(20):
        fn(text)
    t0 = time.perf_counter()
    for _ in range(iters):
        fn(text)
    return (time.perf_counter() - t0) / iters * 1e6  # us/call


def _profile(fn, text: str, iters: int) -> pstats.Stats:
    pr = cProfile.Profile()
    for _ in range(5):
        fn(text)
    pr.enable()
    for _ in range(iters):
        fn(text)
    pr.disable()
    return pstats.Stats(pr)


def _regex_op_summary(stats: pstats.Stats, iters: int) -> tuple[Counter, float]:
    """Per-call regex op counts and time spent in the regex engine.

    Counts ONLY the compiled-Pattern method calls (e.g. ``<method 'sub' of
    're.Pattern' objects>``), not the module-level ``re.sub``/``re.findall``
    wrapper frames that delegate to them. Counting both double-counts an
    uncompiled ``re.sub(str, ...)`` — which would bias a library that does not
    pre-compile (it routes through the wrapper) against one that does.
    """
    counts: Counter = Counter()
    re_time = 0.0
    for (_filename, _lineno, funcname), (_cc, nc, tt, _ct, _cb) in stats.stats.items():
        if funcname.startswith("<method '") and "re.Pattern" in funcname:
            for op in _REGEX_OPS:
                if f"'{op}'" in funcname:
                    counts[op] += nc
                    re_time += tt
                    break
    per_call = Counter({k: v / iters for k, v in counts.items()})
    return per_call, re_time / iters * 1e6


def _top(stats: pstats.Stats, n: int, iters: int) -> list[tuple[str, float, int]]:
    rows = []
    for (filename, lineno, funcname), (_cc, nc, tt, _ct, _cb) in stats.stats.items():
        short = filename.replace("\\", "/").split("/")[-1]
        rows.append((f"{short}:{lineno}:{funcname}", tt / iters * 1e6, nc // iters))
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["short", "medium", "large"], default="short")
    ap.add_argument("--top", type=int, default=14)
    args = ap.parse_args()

    text = _SAMPLES[args.size]
    iters = 8000 if args.size != "large" else 1000

    ours = sentencesplit.Segmenter(language="en", clean=False)
    sbd = pysbd.Segmenter(language="en", clean=False)
    engines = {"sentencesplit": ours.segment, "pysbd": sbd.segment}

    print(f"differential profile  size={args.size}  ({len(text)} chars)  iters={iters}")
    print("=" * 72)
    walls = {name: _walltime(fn, text, iters) for name, fn in engines.items()}
    print(
        f"wall time:  ours {walls['sentencesplit']:.2f} us/call   "
        f"pysbd {walls['pysbd']:.2f} us/call   "
        f"ours is {walls['sentencesplit'] / walls['pysbd']:.2f}x pysbd"
    )
    print()

    for name, fn in engines.items():
        stats = _profile(fn, text, iters)
        ops, re_us = _regex_op_summary(stats, iters)
        total_ops = sum(ops.values())
        print(f"--- {name} ---")
        print(
            f"  regex ops/call: {total_ops:.1f}  "
            f"({'  '.join(f'{k}={v:.1f}' for k, v in sorted(ops.items(), key=lambda x: -x[1]))})"
        )
        print(f"  time in re/call: {re_us:.1f} us")
        print(f"  top {args.top} by tottime (us/call, calls/call):")
        for label, us, calls in _top(stats, args.top, iters):
            print(f"    {us:7.2f}  x{calls:<4} {label}")
        print()


if __name__ == "__main__":
    main()
