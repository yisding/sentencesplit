"""Latency baseline profiler for sentencesplit.

Measures wall-clock latency (not token lag) for the three latency-sensitive
paths and produces a cProfile hot-function breakdown:

  1. one-shot ``segment()``           -- interactive / per-request use
  2. ``should_wait_for_more()``       -- the lookahead probe path
  3. ``StreamSegmenter.feed()``       -- token-by-token streaming

Run with:
    uv run python benchmarks/latency_baseline.py
    uv run python benchmarks/latency_baseline.py --profile   # adds cProfile
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import statistics
import time
from io import StringIO

from sentencesplit import Segmenter, StreamSegmenter

SHORT = "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones."
MEDIUM = (
    "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
    "The model is GPT 3.1 and it is fast. That is all for now. Goodbye. "
    "She paid $4.50 for the U.S. edition (vol. 2, p. 17). Mr. Lee agreed."
)
# A larger realistic document: repeat the medium sample to ~5 KB of prose.
LARGE = " ".join([MEDIUM] * 20)

SAMPLES = {"short": SHORT, "medium": MEDIUM, "large": LARGE}


def _stats(times_ms: list[float]) -> str:
    times_ms.sort()
    median = statistics.median(times_ms)
    mean = statistics.fmean(times_ms)
    p95 = times_ms[min(len(times_ms) - 1, int(0.95 * len(times_ms)))]
    p99 = times_ms[min(len(times_ms) - 1, int(0.99 * len(times_ms)))]
    return f"mean={mean:.3f}ms  median={median:.3f}ms  p95={p95:.3f}ms  p99={p99:.3f}ms"


def _time_calls(fn, iters: int) -> list[float]:
    # warm up (build caches: language profile, abbreviation automaton)
    for _ in range(3):
        fn()
    times = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return times


def bench_oneshot(iters: int) -> None:
    print("\n== one-shot segment()  (reused Segmenter) ==")
    seg = Segmenter(language="en", clean=False, char_span=False)
    for name, text in SAMPLES.items():
        times = _time_calls(lambda t=text: seg.segment(t), iters)
        print(f"  {name:7} ({len(text):>4} chars): {_stats(times)}")


def bench_lookahead(iters: int) -> None:
    print("\n== should_wait_for_more()  (lookahead probe path) ==")
    seg = Segmenter(language="en", clean=False, char_span=False)
    # A text whose last segment ends in '.' triggers the probe loop.
    for name, text in SAMPLES.items():
        times = _time_calls(lambda t=text: seg.should_wait_for_more(t), iters)
        print(f"  {name:7} ({len(text):>4} chars): {_stats(times)}")


def bench_streaming(iters: int) -> None:
    print("\n== StreamSegmenter.feed()  (per-token wall time over a full doc) ==")
    for mode in ("conservative", "aggressive"):
        per_doc_ms = []
        for _ in range(iters):
            stream = StreamSegmenter(language="en", buffering_mode=mode)
            tokens = [t + " " for t in MEDIUM.split(" ")]
            t0 = time.perf_counter()
            for tok in tokens:
                stream.feed(tok)
            stream.flush()
            per_doc_ms.append((time.perf_counter() - t0) * 1000)
        n_tokens = len(MEDIUM.split(" "))
        per_doc_ms.sort()
        med = statistics.median(per_doc_ms)
        print(f"  {mode:13}: whole-doc median={med:.3f}ms over {n_tokens} feeds "
              f"(~{med / n_tokens:.4f}ms/token)")


def profile_path(label: str, fn, n: int) -> None:
    print(f"\n##### cProfile: {label} (x{n}) #####")
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(n):
        fn()
    pr.disable()
    s = StringIO()
    pstats.Stats(pr, stream=s).strip_dirs().sort_stats("cumulative").print_stats(18)
    print(s.getvalue())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--profile", action="store_true")
    args = ap.parse_args()

    print("sentencesplit latency baseline")
    print("=" * 64)
    bench_oneshot(args.iters)
    bench_lookahead(max(args.iters // 4, 200))
    bench_streaming(max(args.iters // 20, 50))

    if args.profile:
        seg = Segmenter(language="en", clean=False, char_span=False)
        profile_path("segment(MEDIUM)", lambda: seg.segment(MEDIUM), 4000)
        profile_path("should_wait_for_more(MEDIUM)", lambda: seg.should_wait_for_more(MEDIUM), 2000)


if __name__ == "__main__":
    main()
