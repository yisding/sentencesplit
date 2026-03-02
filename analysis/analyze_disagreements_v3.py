#!/usr/bin/env python3
"""Examine the 'unclear' cases to understand what's actually happening."""

import json
import re

with open("analysis/pysbd_vs_punkt_results.json") as f:
    data = json.load(f)


# Specifically look at cases where "Same count, different boundaries" after removing headers
HEADER_RE = re.compile(r"^={2,}\s.*={2,}")


def strip_headers(sents):
    return [s for s in sents if not HEADER_RE.match(s.strip())]


def norm(sents):
    return [s.strip() for s in sents if s.strip()]


for i, rec in enumerate(data["disagreements"]):
    pysbd = rec["pysbd"]
    punkt = rec["punkt"]

    ps = norm(strip_headers(pysbd))
    ks = norm(strip_headers(punkt))

    if ps == ks:
        # This is a header-only difference
        continue

    # Find first divergence
    min_len = min(len(ps), len(ks))
    div = None
    for j in range(min_len):
        if ps[j] != ks[j]:
            div = j
            break
    if div is None:
        # One is a prefix of the other
        div = min_len

    # Categorize the divergence
    if div < len(ps) and div < len(ks):
        p_sent = ps[div]
        k_sent = ks[div]

        # Is pySBD's sentence a prefix of Punkt's?
        if k_sent.startswith(p_sent.rstrip()):
            pattern = "pySBD_SPLITS_EARLY"
        elif p_sent.startswith(k_sent.rstrip()):
            pattern = "PUNKT_SPLITS_EARLY"
        else:
            pattern = "DIFFERENT_BOUNDARIES"
    elif div >= len(ps):
        pattern = "PUNKT_HAS_EXTRA"
    else:
        pattern = "PYSBD_HAS_EXTRA"

    print(f"#{i + 1:>2} [{rec['article'][:20]:<20}] {len(ps):>2}v{len(ks):<2} {pattern}")

    if div is not None and div < min_len:
        # Show the divergence
        ctx_start = max(0, div - 1)
        print(f"    Diverges at [{div}]:")

        p_text = ps[div][:100]
        k_text = ks[div][:100]
        print(f"    pySBD: {p_text}{'...' if len(ps[div]) > 100 else ''}")
        print(f"    Punkt: {k_text}{'...' if len(ks[div]) > 100 else ''}")

        # If there's a next sentence, show it too
        if div + 1 < len(ps):
            print(f"    pySBD[{div + 1}]: {ps[div + 1][:80]}{'...' if len(ps[div + 1]) > 80 else ''}")
        if div + 1 < len(ks):
            print(f"    Punkt[{div + 1}]: {ks[div + 1][:80]}{'...' if len(ks[div + 1]) > 80 else ''}")
    elif div >= min_len:
        extra = "pySBD" if len(ps) > len(ks) else "Punkt"
        extra_sents = ps[div:] if len(ps) > len(ks) else ks[div:]
        print(f"    {extra} has {len(extra_sents)} extra sentence(s):")
        for s in extra_sents[:3]:
            print(f"      {s[:80]}{'...' if len(s) > 80 else ''}")

    print()
