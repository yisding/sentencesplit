# -*- coding: utf-8 -*-
"""Regenerate the hermetic regression-gate gold subset and/or baseline.

This is the operational half of the N2 governance contract (see ``GOVERNANCE.md``).
It has two responsibilities, run from the repo root via ``uv``:

  * ``--vendor-gold`` — re-extract the vendored UD gold units from the corpus
    cache under ``benchmarks/corpus_compare/corpora_cache/`` into
    ``gold/ud_gold_subset.json``. This needs the cached ``.conllu`` files (a
    network fetch via ``benchmarks/corpus_compare/corpora.py`` populates them);
    it is *not* part of the hermetic test path and is only run when the vendored
    units must change. English Golden Rules are not vendored here — they already
    live in ``benchmarks/english_golden_rules.py`` and are referenced directly.

  * ``--update-baseline "<one-line rationale>"`` — re-score the current
    ``sentencesplit`` over the committed gold and rewrite ``baseline.json``,
    stamping the supplied rationale. This is the reviewed ``# baseline-update``
    flow: a maintainer runs it deliberately, the diff is reviewed, and the
    rationale is recorded in the file (and should be echoed in the commit body).

Both steps reuse the exact scoring (``boundary_f1``) and the exact UD parsing /
unit-selection logic the cross-library harness uses, so the gate measures the
same thing the Tier-2 comparison does.

Examples
--------
    # one-off: refresh the vendored UD gold from the (network-populated) cache
    uv run python tests/regression/gate/regen_gate.py --vendor-gold

    # reviewed baseline bump after a net-positive accuracy change
    uv run python tests/regression/gate/regen_gate.py \
        --update-baseline "de/nl abbreviation curation: +6.7 de, +3.3 nl, net +1.7 EM"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
_GOLD_DIR = _HERE / "gold"
_UD_GOLD = _GOLD_DIR / "ud_gold_subset.json"
_BASELINE = _HERE / "baseline.json"
_CACHE = _REPO_ROOT / "benchmarks" / "corpus_compare" / "corpora_cache"

# Per-treebank attribution. UD treebanks are redistributable under their stated
# licenses; we vendor only the small gold subset actually scored by the gate.
# (repo, file_prefix, ISO 639-1, genre, license). Homepage is derived from repo.
_UD_TREEBANKS = [
    ("UD_English-EWT", "en_ewt", "en", "web", "CC BY-SA 4.0"),
    ("UD_English-GUM", "en_gum", "en", "academic/varied", "CC BY-NC-SA 4.0"),
    ("UD_German-GSD", "de_gsd", "de", "news/wiki", "CC BY-SA 4.0"),
    ("UD_French-GSD", "fr_gsd", "fr", "news/wiki", "CC BY-SA 4.0"),
    ("UD_Spanish-GSD", "es_gsd", "es", "news/wiki", "CC BY-SA 4.0"),
    ("UD_Italian-ISDT", "it_isdt", "it", "news/legal", "CC BY-NC-SA 3.0"),
    ("UD_Dutch-Alpino", "nl_alpino", "nl", "news", "CC BY-SA 4.0"),
    ("UD_Russian-GSD", "ru_gsd", "ru", "wiki", "CC BY-SA 4.0"),
    ("UD_Greek-GDT", "el_gdt", "el", "news/wiki", "CC BY-NC-SA 3.0"),
    ("UD_Chinese-GSD", "zh_gsd", "zh", "wiki", "CC BY-SA 4.0"),
]
_UD_HOMEPAGE = "https://github.com/UniversalDependencies/{repo}"
_MAX_UNITS_PER_TREEBANK = 30


def _ud_parse(conllu: str, language: str):
    """Group consecutive ``# text =`` sentences into paragraph-sized units.

    Mirrors ``benchmarks/corpus_compare/corpora.py::_ud_parse`` exactly so the
    vendored units match the cross-library harness's selection.
    """
    joiner = "" if language in {"zh", "ja"} else " "
    groups: list[list[str]] = []
    cur: list[str] = []
    for line in conllu.splitlines():
        if line.startswith("# newpar") or line.startswith("# newdoc"):
            if cur:
                groups.append(cur)
                cur = []
        elif line.startswith("# text ="):
            sent = line.split("=", 1)[1].strip()
            if sent:
                cur.append(sent)
                if len(cur) >= 5:
                    groups.append(cur)
                    cur = []
    if cur:
        groups.append(cur)
    return groups, joiner


def vendor_gold() -> dict:
    """Extract the UD gold units the harness selects out of the cached conllu."""
    if not _CACHE.exists():
        sys.exit(
            f"corpus cache not found: {_CACHE}\n"
            "Populate it first by running the cross-library corpora loader:\n"
            "  uv run python benchmarks/corpus_compare/corpora.py"
        )
    corpora = []
    for repo, prefix, lang, genre, lic in _UD_TREEBANKS:
        path = _CACHE / f"ud_{prefix}_test.conllu"
        if not path.exists():
            sys.exit(f"missing cached treebank: {path} (run the corpora loader to fetch it)")
        conllu = path.read_text(encoding="utf-8")
        groups, joiner = _ud_parse(conllu, lang)
        units = []
        kept = 0
        for gi, sentences in enumerate(groups):
            if len(sentences) < 2:  # need a real interior boundary
                continue
            text = joiner.join(sentences)
            if len(text) > 2000:
                continue
            units.append({"unit_id": f"{prefix}_{gi:04d}", "text": text, "gold": list(sentences)})
            kept += 1
            if kept >= _MAX_UNITS_PER_TREEBANK:
                break
        corpora.append(
            {
                "corpus": f"ud_{prefix}",
                "language": lang,
                "genre": genre,
                "treebank": repo,
                "license": lic,
                "homepage": _UD_HOMEPAGE.format(repo=repo),
                "units": units,
            }
        )
    doc = {
        "_about": (
            "Vendored Universal Dependencies gold units for the hermetic regression gate. "
            "Only the gold sentence segmentations actually scored by the gate are stored "
            "(text + sentence list per unit), not the full treebanks. Each treebank's "
            "license and homepage are recorded for attribution. Regenerate with "
            "`uv run python tests/regression/gate/regen_gate.py --vendor-gold`."
        ),
        "source": "Universal Dependencies (https://universaldependencies.org/), test splits",
        "extraction": "Mirrors benchmarks/corpus_compare/corpora.py: group consecutive `# text =` "
        "lines into <=5-sentence units at newpar/newdoc, keep first 30 multi-sentence units <=2000 chars.",
        "corpora": corpora,
    }
    _GOLD_DIR.mkdir(parents=True, exist_ok=True)
    _UD_GOLD.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(c["units"]) for c in corpora)
    print(f"wrote {_UD_GOLD.relative_to(_REPO_ROOT)}: {len(corpora)} treebanks, {total} units")
    return doc


def update_baseline(rationale: str) -> dict:
    """Re-score current sentencesplit over the committed gold and rewrite baseline."""
    # Import lazily so --vendor-gold doesn't require the scoring deps on path.
    sys.path.insert(0, str(_HERE))
    from gate_scoring import load_gold_corpora, score_corpus

    corpora = load_gold_corpora()
    scores = {}
    overall_em = [0, 0]
    overall_f1 = [0.0, 0]
    for corpus, lang, units in corpora:
        em, f1, n, em_pair, f1_pair = score_corpus(lang, units)
        scores[corpus] = {"language": lang, "exact_match": em, "boundary_f1": f1, "n": n}
        overall_em[0] += em_pair[0]
        overall_em[1] += em_pair[1]
        overall_f1[0] += f1_pair[0]
        overall_f1[1] += f1_pair[1]
    overall = {
        "exact_match": round(overall_em[0] / overall_em[1] * 100, 1) if overall_em[1] else None,
        "boundary_f1": round(overall_f1[0] / overall_f1[1] * 100, 1) if overall_f1[1] else None,
        "n": overall_em[1],
    }
    doc = {
        "_about": (
            "Committed baseline for the hermetic CI regression gate "
            "(tests/regression/test_regression_gate.py). Per-corpus exact-match and "
            "boundary-F1 for sentencesplit over the vendored gold. The gate FAILS a PR "
            "if any corpus drops below its score here by more than the per-language "
            "tolerance in gate_scoring.TOLERANCES. Update only via the reviewed "
            "`# baseline-update` flow documented in GOVERNANCE.md."
        ),
        "updated": date.today().isoformat(),
        "rationale": rationale,
        "overall": overall,
        "by_corpus": scores,
    }
    _BASELINE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {_BASELINE.relative_to(_REPO_ROOT)}")
    print(f"  overall: EM={overall['exact_match']} F1={overall['boundary_f1']} n={overall['n']}")
    for corpus, s in scores.items():
        print(f"  {corpus:16} EM={s['exact_match']:5} F1={s['boundary_f1']:5} n={s['n']}")
    print(f"  rationale: {rationale}")
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vendor-gold", action="store_true", help="re-extract vendored UD gold from the corpus cache")
    ap.add_argument(
        "--update-baseline",
        metavar="RATIONALE",
        help="re-score sentencesplit and rewrite baseline.json, stamping a one-line rationale",
    )
    args = ap.parse_args()
    if not args.vendor_gold and args.update_baseline is None:
        ap.error("nothing to do: pass --vendor-gold and/or --update-baseline 'rationale'")
    if args.vendor_gold:
        vendor_gold()
    if args.update_baseline is not None:
        rationale = args.update_baseline.strip()
        if not rationale:
            ap.error("--update-baseline requires a non-empty one-line rationale")
        update_baseline(rationale)


if __name__ == "__main__":
    main()
