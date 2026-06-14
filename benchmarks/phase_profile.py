"""Phase-level latency profiler for the segmentation pipeline.

Where ``latency_baseline.py`` answers "how fast is a call?", this answers "which
*phase* of the call is the time in?" — it wraps each Processor / AbbreviationReplacer
/ Segmenter stage with a timer and reports per-phase wall time, call count, and
share of the total, for short / medium / large input.

This is the exploration harness for the short/medium-vs-pySBD latency gap: the
fixed per-call cost (the phases that run on every call regardless of input) is
what dominates short strings, so this attributes that cost to concrete phases.

Run with:
    uv run python benchmarks/phase_profile.py
    uv run python benchmarks/phase_profile.py --size short --iters 20000
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict

from sentencesplit import Segmenter
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.processor import Processor
from sentencesplit.segmenter import Segmenter as _Seg

SHORT = "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones."
MEDIUM = (
    "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
    "The model is GPT 3.1 and it is fast. That is all for now. Goodbye. "
    "She paid $4.50 for the U.S. edition (vol. 2, p. 17). Mr. Lee agreed."
)
LARGE = " ".join([MEDIUM] * 20)
_SAMPLES = {"short": SHORT, "medium": MEDIUM, "large": LARGE}

# (class, method) pairs to attribute. Grouped by pipeline stage; the label is what
# the report prints. Only methods that exist are wrapped.
_TARGETS = [
    # --- text-processing phases (run once per call over the whole text) ---
    (Processor, "_normalize_newlines", "text: normalize_newlines"),
    (Processor, "_mark_list_item_boundaries", "text: list_item_boundaries"),
    (Processor, "replace_abbreviations", "text: replace_abbreviations"),
    (Processor, "replace_numbers", "text: replace_numbers"),
    (Processor, "replace_continuous_punctuation", "text: continuous_punct"),
    (Processor, "replace_periods_before_numeric_references", "text: numeric_refs"),
    (Processor, "_protect_special_tokens", "text: special_tokens"),
    # --- boundary-processing phases (per segment) ---
    (Processor, "_ensure_terminal_marker", "bound: terminal_marker"),
    (Processor, "_apply_exclamation_word_rules", "bound: exclamation_words"),
    (Processor, "between_punctuation", "bound: between_punctuation"),
    (Processor, "_apply_double_punctuation_rules", "bound: double_punct"),
    (Processor, "_apply_quotation_punctuation_rules", "bound: quotation_punct"),
    (Processor, "_replace_list_parens", "bound: list_parens"),
    (Processor, "sentence_boundary_punctuation", "bound: sentence_boundary"),
    # --- post-split passes ---
    (Processor, "split_into_segments", "post: split_into_segments (incl. boundary)"),
    (Processor, "_resplit_segments", "post: resplit_segments"),
    (Processor, "_merge_orphan_fragments", "post: merge_orphans"),
    # --- abbreviation internals (the suspected fixed cost) ---
    (AbbreviationReplacer, "replace", "abbr: replace (whole)"),
    (AbbreviationReplacer, "search_for_abbreviations_in_string", "abbr: search_in_string"),
    (AbbreviationReplacer, "apply_ampm_boundary_rules", "abbr: ampm_rules"),
    # --- span mapping (segmenter) ---
    (_Seg, "_match_spans", "span: match_spans"),
]

_stats: dict[str, list[float | int]] = defaultdict(lambda: [0.0, 0])  # label -> [total_s, calls]


def _wrap(cls, method_name: str, label: str) -> None:
    original = getattr(cls, method_name, None)
    if original is None:
        return

    def timed(self, *args, _orig=original, _label=label, **kwargs):
        t0 = time.perf_counter()
        try:
            return _orig(self, *args, **kwargs)
        finally:
            rec = _stats[_label]
            rec[0] += time.perf_counter() - t0
            rec[1] += 1

    setattr(cls, method_name, timed)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["short", "medium", "large"], default="short")
    ap.add_argument("--iters", type=int, default=20000)
    args = ap.parse_args()

    for cls, name, label in _TARGETS:
        _wrap(cls, name, label)

    seg = Segmenter(language="en", clean=False, char_span=False)
    text = _SAMPLES[args.size]
    for _ in range(5):
        seg.segment(text)
    _stats.clear()

    t0 = time.perf_counter()
    for _ in range(args.iters):
        seg.segment(text)
    total = time.perf_counter() - t0

    print(f"phase profile  size={args.size}  iters={args.iters}  ({len(text)} chars)")
    print(f"total: {total * 1000 / args.iters:.4f} ms/call  ({total:.2f}s)")
    print("=" * 78)
    print(f"{'phase':<46}{'ms/call':>10}{'calls/seg':>10}{'% total':>10}")
    print("-" * 78)
    rows = sorted(_stats.items(), key=lambda kv: kv[1][0], reverse=True)
    for label, (total_s, calls) in rows:
        ms_per_call = total_s * 1000 / args.iters
        calls_per_seg = calls / args.iters
        pct = 100 * total_s / total
        # split_into_segments wraps the boundary phases, so its % overlaps them;
        # mark it so the breakdown is not misread as additive.
        note = "  *wrapper" if "split_into_segments" in label or label == "abbr: replace (whole)" else ""
        print(f"{label:<46}{ms_per_call:>10.4f}{calls_per_seg:>10.1f}{pct:>9.1f}%{note}")
    print("-" * 78)
    print("* wrapper rows contain the rows below them; do not sum across them.")


if __name__ == "__main__":
    main()
