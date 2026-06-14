# -*- coding: utf-8 -*-
"""Regression test for the span-matching fallback CPU-amplification finding.

In the default ``clean=False`` path, ``Segmenter._match_spans`` maps each
processed sentence back to the original text. When the processor strips a space
(e.g. ``'" (...) "'`` becomes ``'(...)"'``) ``str.find`` misses and the code
previously fell back to compiling a regex built from the *entire* sentence via
``_zero_width_flexible_pattern`` (~8 pattern chars per input char, no length cap,
no caching). That is an O(N) build/compile per sentence driven by input length:
~13.7s for a single 160KB ``'" (...) "'`` sentence — an unguarded ReDoS-class gap.

The fix bounds the regex fallback so a long divergent sentence is re-anchored
with a linear whitespace/zero-width-tolerant index walk instead. The walk costs
about the same as the non-divergent baseline of the same size, so the divergent
case must no longer be dramatically slower than that baseline.
"""

from __future__ import annotations

import time

import pytest

import sentencesplit


def _best_segment_time(seg, text, repeats=3):
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        out = seg.segment(text)
        best = min(best, time.perf_counter() - start)
    return best, out


@pytest.mark.perf
def test_span_match_fallback_not_quadratic_on_long_quote_paren_sentence():
    """A 100KB ``'" (...) "'`` single sentence triggers the divergent span
    fallback (the processor strips the space before the closing quote, so
    ``str.find`` misses). It must re-anchor in well under ~0.5s and stay
    non-destructive. The pre-fix code took several seconds here (8s+)."""
    text = '" (' + "a" * 100000 + ') "'

    seg = sentencesplit.Segmenter(language="en")
    seg.segment("warm up. ok.")  # prime caches outside the timed region
    elapsed, segments = _best_segment_time(seg, text)

    # Round-trip / no text loss: spans must tile the original exactly.
    assert "".join(segments) == text
    assert elapsed < 0.5


@pytest.mark.perf
def test_span_match_fallback_no_worse_than_non_divergent_baseline():
    """The divergent fallback must add only negligible overhead: a 100KB
    sentence that hits the fallback must not be materially slower than a
    same-size sentence whose processed form still matches via ``str.find``.

    This pins the *amplification* directly and is independent of the machine's
    inherent linear cost on a 100KB token (pre-fix the ratio blew up with N)."""
    n = 100000
    divergent = '" (' + "a" * n + ') "'  # space before closing quote is stripped
    baseline = "x (" + "a" * n + ") y."  # processed form still matches str.find

    seg = sentencesplit.Segmenter(language="en")
    seg.segment("warm up. ok.")

    baseline_time, base_out = _best_segment_time(seg, baseline)
    divergent_time, div_out = _best_segment_time(seg, divergent)

    assert "".join(base_out) == baseline
    assert "".join(div_out) == divergent
    # The fallback walk is linear, so the divergent case stays within a small
    # constant factor of the non-divergent baseline (with a floor so timing
    # jitter on a fast baseline can't make the bound spuriously tight).
    assert divergent_time <= max(baseline_time * 4.0, 0.5)


@pytest.mark.perf
def test_span_match_fallback_not_quadratic_with_char_spans():
    """The same divergent path is shared by ``segment_spans()``; it must
    also stay bounded and contiguously tile the original text."""
    text = '" (' + "b" * 100000 + ') "'

    seg = sentencesplit.Segmenter(language="en")
    seg.segment_spans("warm up. ok.")
    start = time.perf_counter()
    spans = seg.segment_spans(text)
    elapsed = time.perf_counter() - start

    assert "".join(s.sent for s in spans) == text
    prev_end = 0
    for s in spans:
        assert s.start == prev_end
        assert text[s.start : s.end] == s.sent
        prev_end = s.end
    assert prev_end == len(text)
    assert elapsed < 0.5
