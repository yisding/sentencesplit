#!/usr/bin/env python3
"""Compare sentence boundary detection: en vs en_legal vs NLTK Punkt on legal documents."""

import re
import sys
from pathlib import Path

import nltk
nltk.download("punkt_tab", quiet=True)
from nltk.tokenize import sent_tokenize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sentencesplit.segmenter import Segmenter

# --- Helpers ---

def segment_en(text: str) -> list[str]:
    s = Segmenter(language="en", clean=False)
    return [x.strip() for x in s.segment(text) if x.strip()]


def segment_en_legal(text: str) -> list[str]:
    s = Segmenter(language="en_legal", clean=False)
    return [x.strip() for x in s.segment(text) if x.strip()]


def segment_punkt(text: str) -> list[str]:
    return sent_tokenize(text)


# --- Evaluation on known-good examples ---

# Manually curated legal sentences with expected splits.
# These are excerpts chosen to stress-test abbreviation handling.
GOLD_EXAMPLES = [
    {
        "name": "Case citation with v.",
        "text": "The ruling in Brown v. Board of Education established a precedent. It was a landmark case.",
        "expected": [
            "The ruling in Brown v. Board of Education established a precedent.",
            "It was a landmark case.",
        ],
    },
    {
        "name": "Multiple reporter citations",
        "text": "See 42 U.S.C. § 1983. The statute provides a cause of action.",
        "expected": [
            "See 42 U.S.C. § 1983.",
            "The statute provides a cause of action.",
        ],
    },
    {
        "name": "Justice abbreviation",
        "text": "J. Roberts delivered the opinion. The case was decided 6-3.",
        "expected": [
            "J. Roberts delivered the opinion.",
            "The case was decided 6-3.",
        ],
    },
    {
        "name": "Circuit court abbreviation",
        "text": "The 9th Cir. reversed the decision. The case was remanded for further proceedings.",
        "expected": [
            "The 9th Cir. reversed the decision.",
            "The case was remanded for further proceedings.",
        ],
    },
    {
        "name": "Bankruptcy court",
        "text": "The Bankr. Court approved the reorganization plan. Creditors objected.",
        "expected": [
            "The Bankr. Court approved the reorganization plan.",
            "Creditors objected.",
        ],
    },
    {
        "name": "District court",
        "text": "The Dist. Court granted summary judgment. The plaintiff appealed.",
        "expected": [
            "The Dist. Court granted summary judgment.",
            "The plaintiff appealed.",
        ],
    },
    {
        "name": "Et al. citation",
        "text": "Smith et al. filed a brief in support. The court considered the arguments.",
        "expected": [
            "Smith et al. filed a brief in support.",
            "The court considered the arguments.",
        ],
    },
    {
        "name": "Amendment with Roman numeral",
        "text": "Pursuant to Amend. XIV, equal protection is guaranteed. This principle is fundamental.",
        "expected": [
            "Pursuant to Amend. XIV, equal protection is guaranteed.",
            "This principle is fundamental.",
        ],
    },
    {
        "name": "Federal Supplement citation",
        "text": "In Jones v. Smith, 550 F.Supp. 123, the court ruled for the plaintiff. The decision was later affirmed.",
        "expected": [
            "In Jones v. Smith, 550 F.Supp. 123, the court ruled for the plaintiff.",
            "The decision was later affirmed.",
        ],
    },
    {
        "name": "Administrative law",
        "text": "The Admin. Law Judge found in favor of the petitioner. The agency accepted the recommendation.",
        "expected": [
            "The Admin. Law Judge found in favor of the petitioner.",
            "The agency accepted the recommendation.",
        ],
    },
    {
        "name": "Attorney abbreviation",
        "text": "Atty. General Garland issued the memorandum. It addressed prosecution priorities.",
        "expected": [
            "Atty. General Garland issued the memorandum.",
            "It addressed prosecution priorities.",
        ],
    },
    {
        "name": "Schedule reference",
        "text": "See Sched. A for the complete list of properties. All parcels are included.",
        "expected": [
            "See Sched. A for the complete list of properties.",
            "All parcels are included.",
        ],
    },
    {
        "name": "Supra citation",
        "text": "See supra at 5. The argument is well-founded.",
        "expected": [
            "See supra at 5.",
            "The argument is well-founded.",
        ],
    },
    {
        "name": "Complex legal passage",
        "text": (
            "In Marbury v. Madison, 5 U.S. 137 (1803), the Court established judicial review. "
            "Ch. J. Marshall wrote the opinion. "
            "The Def. argued that the Court lacked jurisdiction. "
            "See also McCulloch v. Maryland, 17 U.S. 316 (1819)."
        ),
        "expected": [
            "In Marbury v. Madison, 5 U.S. 137 (1803), the Court established judicial review.",
            "Ch. J. Marshall wrote the opinion.",
            "The Def. argued that the Court lacked jurisdiction.",
            "See also McCulloch v. Maryland, 17 U.S. 316 (1819).",
        ],
    },
    {
        "name": "C.F.R. citation",
        "text": "Under 29 C.F.R. § 1910.134, employers must provide respirators. Compliance is mandatory.",
        "expected": [
            "Under 29 C.F.R. § 1910.134, employers must provide respirators.",
            "Compliance is mandatory.",
        ],
    },
]


def evaluate_gold(name: str, func, examples: list[dict]) -> dict:
    correct = 0
    errors = []
    for ex in examples:
        result = func(ex["text"])
        if result == ex["expected"]:
            correct += 1
        else:
            errors.append({
                "name": ex["name"],
                "expected": ex["expected"],
                "got": result,
            })
    return {"name": name, "correct": correct, "total": len(examples), "errors": errors}


# --- Document-level analysis ---

def find_bad_splits(sentences: list[str], abbreviations: list[str]) -> list[dict]:
    """Find sentences that likely split incorrectly on an abbreviation."""
    issues = []
    for i, sent in enumerate(sentences):
        # Check if sentence ends with a known abbreviation (false positive split)
        stripped = sent.rstrip()
        for abbr in abbreviations:
            pattern = rf"\b{re.escape(abbr)}\.$"
            if re.search(pattern, stripped, re.IGNORECASE):
                next_sent = sentences[i + 1].strip() if i + 1 < len(sentences) else ""
                # Only flag if next sentence starts with a non-sentence-starter pattern
                if next_sent and not re.match(r'^["\'\(]', next_sent):
                    issues.append({
                        "index": i,
                        "abbr": abbr,
                        "fragment": stripped[-60:],
                        "next_start": next_sent[:60],
                    })
                break
    return issues


LEGAL_ABBREVIATIONS = [
    "v", "vs", "Cir", "Dist", "Bankr", "App", "Sup", "Ct",
    "J", "JJ", "Ch", "Atty", "Mag", "Admin",
    "Amend", "Sec", "Art", "Cl", "Sched",
    "F.Supp", "F.2d", "F.3d", "S.Ct", "L.Ed",
    "U.S.C", "C.F.R", "Fed",
    "Def", "Pl", "Compl", "Mot", "Pet", "Resp",
    "et al", "ibid", "supra",
]


def analyze_document(filepath: str) -> None:
    text = Path(filepath).read_text()
    name = Path(filepath).stem

    print(f"\n{'='*80}")
    print(f"DOCUMENT: {name}")
    print(f"{'='*80}")
    print(f"Length: {len(text):,} chars, {len(text.split()):,} words")

    results = {}
    for label, func in [("en", segment_en), ("en_legal", segment_en_legal), ("punkt", segment_punkt)]:
        sents = func(text)
        issues = find_bad_splits(sents, LEGAL_ABBREVIATIONS)
        results[label] = {"count": len(sents), "issues": issues}

    print(f"\n{'Method':<12} {'Sentences':>10} {'Suspect Splits':>16}")
    print(f"{'-'*12} {'-'*10} {'-'*16}")
    for label, r in results.items():
        print(f"{label:<12} {r['count']:>10} {len(r['issues']):>16}")

    # Show sample suspect splits for each method
    for label, r in results.items():
        if r["issues"]:
            print(f"\n  Suspect splits in [{label}] (showing up to 5):")
            for iss in r["issues"][:5]:
                print(f"    #{iss['index']}: ...{iss['fragment']}")
                print(f"         -> {iss['next_start']}...")
                print(f"         (split on: {iss['abbr']}.)")


def main():
    print("=" * 80)
    print("PART 1: GOLD-STANDARD EVALUATION (curated legal examples)")
    print("=" * 80)

    for label, func in [("en (base)", segment_en), ("en_legal", segment_en_legal), ("punkt", segment_punkt)]:
        result = evaluate_gold(label, func, GOLD_EXAMPLES)
        pct = result["correct"] / result["total"] * 100
        print(f"\n{label}: {result['correct']}/{result['total']} correct ({pct:.0f}%)")
        if result["errors"]:
            for err in result["errors"]:
                print(f"  FAIL: {err['name']}")
                print(f"    expected: {err['expected']}")
                print(f"    got:      {err['got']}")

    print(f"\n\n{'='*80}")
    print("PART 2: REAL DOCUMENT ANALYSIS")
    print("=" * 80)

    eval_dir = Path(__file__).parent
    for f in sorted(eval_dir.glob("*.txt")):
        analyze_document(str(f))

    print()


if __name__ == "__main__":
    main()
