# -*- coding: utf-8 -*-
"""Run every available segmenter over every corpus unit, score against gold,
and emit the set of *divergences* (units where segmenters disagree) for review.

Outputs (under ``results/``):
  - ``scoreboard.json``      objective accuracy on ground-truth corpora + availability
  - ``divergences_all.json`` every divergent unit
  - ``divergences.json``     ranked + capped subset chosen for adjudication
  - ``cases/case_XXXX.json`` one file per adjudication case (read by judge agents)

This is the deterministic stage. The LLM "manual review" of each case happens in
the accompanying workflow (``.claude/workflows/compare-segmenters.js``).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from corpora import load_all
from segmenters import _redact_environment_paths, build_registry

_HERE = Path(__file__).resolve().parent
_RESULTS = _HERE / "results"
_CASES = _RESULTS / "cases"


# ── boundary-level scoring (whitespace-insensitive) ───────────────────────────


def _stream(sents: list[str]) -> str:
    return "".join("".join(s.split()) for s in sents)


def _boundaries(sents: list[str]) -> set[int]:
    pos, bs = 0, set()
    for s in sents[:-1]:
        pos += len("".join(s.split()))
        bs.add(pos)
    return bs


def boundary_f1(pred: list[str], gold: list[str]):
    """Precision/recall/F1 over boundary positions. ``None`` if a segmenter
    altered the underlying characters (streams differ) — then it's not a pure
    boundary decision and we report it separately."""
    if _stream(pred) != _stream(gold):
        return None
    gb, pb = _boundaries(gold), _boundaries(pred)
    tp = len(gb & pb)
    p = tp / len(pb) if pb else 1.0
    r = tp / len(gb) if gb else 1.0
    f = (2 * p * r / (p + r)) if (p + r) else 1.0
    return p, r, f


# ── run all segmenters over all units (batched per language) ──────────────────


def run_segmenters(units, registry):
    by_lang = defaultdict(list)
    for i, u in enumerate(units):
        by_lang[u.language].append(i)

    # results[i] = {seg_name: [sentences] or None if not applicable}
    results: list[dict] = [dict() for _ in units]
    for seg in registry:
        if not seg.available:
            continue
        for lang, idxs in by_lang.items():
            if not seg.supports(lang):
                continue
            texts = [units[i].text for i in idxs]
            try:
                batch = seg.segment_batch(texts, lang)
            except Exception as e:
                print(f"  ! {seg.name} failed on lang={lang}: {e}")
                batch = [None] * len(idxs)
            for i, out in zip(idxs, batch):
                results[i][seg.name] = out
    return results


# ── scoreboard on ground-truth corpora ────────────────────────────────────────


def build_scoreboard(units, results, registry):
    avail = [s for s in registry if s.available]
    # accumulators keyed by (segmenter, bucket)
    exact = defaultdict(lambda: [0, 0])  # [correct, total]
    f1sum = defaultdict(lambda: [0.0, 0])  # [sum_f1, n_comparable]
    altered = defaultdict(int)

    for u, res in zip(units, results):
        if u.gold is None:
            continue
        for seg in avail:
            pred = res.get(seg.name)
            if pred is None:
                continue
            for bucket in ("__overall__", f"corpus:{u.corpus}", f"lang:{u.language}"):
                key = (seg.name, bucket)
                exact[key][1] += 1
                if pred == u.gold:
                    exact[key][0] += 1
                prf = boundary_f1(pred, u.gold)
                if prf is None:
                    if bucket == "__overall__":
                        altered[seg.name] += 1
                else:
                    f1sum[key][0] += prf[2]
                    f1sum[key][1] += 1

    def table(bucket_prefix):
        out = {}
        for (name, bucket), (c, t) in exact.items():
            if bucket_prefix == "__overall__" and bucket != "__overall__":
                continue
            if bucket_prefix != "__overall__" and not bucket.startswith(bucket_prefix):
                continue
            label = bucket if bucket_prefix == "__overall__" else bucket.split(":", 1)[1]
            fs = f1sum[(name, bucket)]
            out.setdefault(label, {})[name] = {
                "exact_match": round(c / t * 100, 1) if t else None,
                "boundary_f1": round(fs[0] / fs[1] * 100, 1) if fs[1] else None,
                "n": t,
            }
        return out

    return {
        "overall": table("__overall__").get("__overall__", {}),
        "by_corpus": table("corpus:"),
        "by_language": table("lang:"),
        "altered_text_units": dict(altered),
    }


# ── divergence detection + ranking ────────────────────────────────────────────


def detect_divergences(units, results):
    divs = []
    for u, res in zip(units, results):
        outputs = {name: out for name, out in res.items() if out is not None}
        if len(outputs) < 2:
            continue
        distinct = {tuple(v) for v in outputs.values()}
        if len(distinct) == 1:
            continue  # full agreement

        counts = {name: len(v) for name, v in outputs.items()}
        spread = max(counts.values()) - min(counts.values())

        # plurality segmentation among the tools
        tally = Counter(tuple(v) for v in outputs.values())
        plurality, plurality_n = tally.most_common(1)[0]
        ours = tuple(outputs.get("sentencesplit", ()))
        ss_is_odd = "sentencesplit" in outputs and ours != plurality

        gold_t = tuple(u.gold) if u.gold is not None else None
        someone_matches_gold = gold_t is not None and any(tuple(v) == gold_t for v in outputs.values())
        ss_matches_gold = gold_t is not None and ours == gold_t

        divs.append(
            {
                "id": "",  # filled after ranking
                "corpus": u.corpus,
                "genre": u.genre,
                "language": u.language,
                "unit_id": u.unit_id,
                "text": u.text,
                "gold": u.gold,
                "outputs": outputs,
                "features": {
                    "n_distinct": len(distinct),
                    "sentence_counts": counts,
                    "count_spread": spread,
                    "sentencesplit_is_odd_one_out": ss_is_odd,
                    "has_gold": gold_t is not None,
                    "someone_matches_gold": someone_matches_gold,
                    "sentencesplit_matches_gold": ss_matches_gold,
                },
            }
        )
    return divs


def interestingness(d) -> float:
    f = d["features"]
    score = 0.0
    # Objective cases (gold present, somebody wrong) are most valuable.
    if f["has_gold"]:
        score += 3.0
        if not f["someone_matches_gold"]:
            score += 1.0  # everyone disagrees with gold — interesting
        if f["sentencesplit_matches_gold"]:
            score += 0.5
    # Clean binary disagreements are easy + decisive to adjudicate.
    if f["n_distinct"] == 2:
        score += 1.5
    # We especially want to know when *we* are the outlier.
    if f["sentencesplit_is_odd_one_out"]:
        score += 2.0
    score += min(f["count_spread"], 4) * 0.5
    return score


def select_cases(divs, cap: int):
    """Stratified, interestingness-ranked selection across corpora for breadth."""
    for d in divs:
        d["_score"] = interestingness(d)
    by_corpus = defaultdict(list)
    for d in divs:
        by_corpus[d["corpus"]].append(d)
    for lst in by_corpus.values():
        lst.sort(key=lambda d: d["_score"], reverse=True)

    selected, corpora = [], sorted(by_corpus)
    idx = 0
    while len(selected) < cap and any(by_corpus[c] for c in corpora):
        c = corpora[idx % len(corpora)]
        if by_corpus[c]:
            selected.append(by_corpus[c].pop(0))
        idx += 1
    selected.sort(key=lambda d: d["_score"], reverse=True)
    for n, d in enumerate(selected, 1):
        d["id"] = f"case_{n:04d}"
        d.pop("_score", None)
    return selected


# ── main ──────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=120, help="max divergence cases to emit for adjudication")
    args = ap.parse_args()

    _RESULTS.mkdir(parents=True, exist_ok=True)
    _CASES.mkdir(parents=True, exist_ok=True)
    for old in _CASES.glob("case_*.json"):
        old.unlink()

    print("[1/4] loading corpora ...")
    units = load_all()
    print(f"      {len(units)} units")

    print("[2/4] building segmenter registry ...")
    registry = build_registry()
    avail = [s.name for s in registry if s.available]
    print(f"      available: {', '.join(avail)}")

    print("[3/4] segmenting (batched per language) ...")
    results = run_segmenters(units, registry)

    print("[4/4] scoring + detecting divergences ...")
    scoreboard = build_scoreboard(units, results, registry)
    divs = detect_divergences(units, results)
    selected = select_cases(divs, args.cap)

    scoreboard_doc = {
        "segmenters": [
            {
                "name": s.name,
                "kind": s.kind,
                "description": s.description,
                "available": s.available,
                "unavailable_reason": _redact_environment_paths(s.unavailable_reason),
                "languages": "any" if s.languages is None else sorted(s.languages),
            }
            for s in registry
        ],
        "gold_scores": scoreboard,
        "agreement": {
            "total_units": len(units),
            "divergent_units": len(divs),
            "agreement_rate_pct": round((1 - len(divs) / len(units)) * 100, 1) if units else None,
            "divergences_by_corpus": dict(Counter(d["corpus"] for d in divs)),
            "divergences_by_language": dict(Counter(d["language"] for d in divs)),
        },
        "metric_notes": (
            "exact_match: predicted sentence list == gold list (strict). "
            "boundary_f1: F1 over whitespace-insensitive boundary positions; "
            "units where a tool altered the underlying characters are excluded "
            "and counted in altered_text_units. UD gold paragraphs are "
            "reconstructed by space-joining gold sentences (no-space for zh)."
        ),
    }
    (_RESULTS / "scoreboard.json").write_text(json.dumps(scoreboard_doc, ensure_ascii=False, indent=2))

    (_RESULTS / "divergences_all.json").write_text(
        json.dumps({"count": len(divs), "divergences": divs}, ensure_ascii=False, indent=2)
    )

    for d in selected:
        (_CASES / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2))

    manifest = {
        "cap": args.cap,
        "total_divergences": len(divs),
        "emitted_cases": len(selected),
        "dropped": max(0, len(divs) - len(selected)),
        "available_segmenters": avail,
        "cases": [
            {
                "id": d["id"],
                "path": str((_CASES / f"{d['id']}.json").relative_to(_HERE)),
                "corpus": d["corpus"],
                "language": d["language"],
                "n_distinct": d["features"]["n_distinct"],
                "sentencesplit_is_odd_one_out": d["features"]["sentencesplit_is_odd_one_out"],
                "has_gold": d["features"]["has_gold"],
            }
            for d in selected
        ],
    }
    (_RESULTS / "divergences.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(
        f"\nDONE. units={len(units)} divergent={len(divs)} "
        f"agreement={scoreboard_doc['agreement']['agreement_rate_pct']}% "
        f"emitted_cases={len(selected)} (dropped {manifest['dropped']})"
    )
    print(f"  scoreboard:   {(_RESULTS / 'scoreboard.json').relative_to(_HERE)}")
    print(f"  divergences:  {(_RESULTS / 'divergences.json').relative_to(_HERE)}")
    print(f"  case files:   {_CASES.relative_to(_HERE)}/case_*.json")


if __name__ == "__main__":
    main()
