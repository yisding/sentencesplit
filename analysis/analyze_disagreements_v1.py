#!/usr/bin/env python3
"""Analyze each disagreement between pySBD and Punkt, determine which is correct."""

import json
import re

with open("analysis/pysbd_vs_punkt_results.json") as f:
    data = json.load(f)

# Known abbreviations that should NOT cause a sentence split
KNOWN_ABBRS = {
    "Mr",
    "Mrs",
    "Ms",
    "Dr",
    "Prof",
    "Rev",
    "Gen",
    "Gov",
    "Sgt",
    "Cpl",
    "Pvt",
    "Corp",
    "Inc",
    "Ltd",
    "Jr",
    "Sr",
    "vs",
    "etc",
    "Fig",
    "fig",
    "Vol",
    "vol",
    "No",
    "no",
    "approx",
    "est",
    "ca",
    "dept",
    "Dept",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Sept",
    "Oct",
    "Nov",
    "Dec",
    "St",
    "Ave",
    "Blvd",
    "Rd",
    "Mt",
    "Ft",
    "U.S",
    "U.S.A",
    "U.K",
    "E.U",
    "D.C",
    "Ph.D",
    "M.D",
    "B.A",
    "M.A",
    "B.S",
    "M.S",
    "i.e",
    "e.g",
    "al",  # et al.
    "Adm",
    "Bros",
    "Co",
    "Col",
    "Capt",
    "Lt",
    "Maj",
    "Messrs",
    # Names that end with initials
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
}


def ends_with_abbreviation(sent: str) -> str | None:
    """Check if a sentence ends with a known abbreviation. Returns the abbreviation or None."""
    sent = sent.rstrip()
    if not sent.endswith("."):
        return None

    # Check for single-letter initials like "W. E. B."
    m = re.search(r"([A-Z])\.\s*$", sent)
    if m:
        return m.group(1)

    # Check for multi-letter abbreviations
    for abbr in sorted(KNOWN_ABBRS, key=len, reverse=True):
        if sent.endswith(abbr + "."):
            # Make sure it's a word boundary before the abbreviation
            prefix = sent[: -(len(abbr) + 1)]
            if not prefix or prefix[-1] in " \t\n([\"'":
                return abbr

    # Check for abbreviation patterns like "D.C." or "U.S.A."
    m = re.search(r"([A-Z]\.(?:[A-Z]\.)+)\s*$", sent)
    if m:
        return m.group(1)

    return None


def check_parenthesis_balance(sents: list[str]) -> list[int]:
    """Return indices where splits occur inside unclosed parentheses."""
    bad = []
    depth = 0
    for i, s in enumerate(sents):
        if depth > 0:
            bad.append(i)
        depth += s.count("(") - s.count(")")
    return bad


def check_quote_balance(sents: list[str]) -> list[int]:
    """Return indices where splits occur inside unclosed quotes."""
    bad = []
    # Track both straight and curly quotes
    open_double = 0
    for i, s in enumerate(sents):
        if open_double % 2 != 0 and i > 0:
            bad.append(i)
        open_double += s.count('"') + s.count("\u201c") - s.count("\u201d")
        # For straight quotes, count total and track parity
        straight = s.count('"')
        open_double += straight  # rough heuristic
    return bad


def analyze_one(para: str, pysbd_sents: list[str], punkt_sents: list[str]) -> dict:
    """Analyze a single disagreement and return a verdict."""

    # Detect section headers that pySBD splits off
    pysbd_has_header = bool(pysbd_sents and re.match(r"^={2,}", pysbd_sents[0]))
    punkt_has_header = bool(punkt_sents and re.match(r"^={2,}", punkt_sents[0]))

    issues = {"pysbd": [], "punkt": []}

    # Check for abbreviation splits
    for name, sents in [("pysbd", pysbd_sents), ("punkt", punkt_sents)]:
        for i, s in enumerate(sents[:-1]):  # don't check last sentence
            abbr = ends_with_abbreviation(s)
            if abbr:
                issues[name].append(f"False split after abbreviation '{abbr}.' in sent [{i}]")

    # Check for parenthesis balance
    for name, sents in [("pysbd", pysbd_sents), ("punkt", punkt_sents)]:
        bad_paren = check_parenthesis_balance(sents)
        for idx in bad_paren:
            issues[name].append(f"Split inside parentheses at sent [{idx}]")

    # Check for splits that produce fragments (very short segments that aren't real sentences)
    for name, sents in [("pysbd", pysbd_sents), ("punkt", punkt_sents)]:
        for i, s in enumerate(sents):
            stripped = s.strip()
            # A real sentence almost always has a space (subject + verb at minimum)
            if len(stripped) < 15 and " " not in stripped and i > 0 and i < len(sents) - 1:
                issues[name].append(f"Suspiciously short fragment '{stripped}' at sent [{i}]")

    # Check for header splitting differences
    if pysbd_has_header and not punkt_has_header:
        # pySBD splits header as separate sentence, Punkt keeps it joined
        # Both approaches are debatable, but splitting header off is arguably cleaner
        pass
    elif punkt_has_header and not pysbd_has_header:
        pass

    # Detect the specific difference patterns
    n_pysbd = len(pysbd_sents)
    n_punkt = len(punkt_sents)

    # Determine verdict
    pysbd_errors = len(issues["pysbd"])
    punkt_errors = len(issues["punkt"])

    if pysbd_errors == 0 and punkt_errors == 0:
        # No obvious errors detected — need deeper analysis
        # Check if the difference is just header splitting
        if pysbd_has_header and not punkt_has_header and n_pysbd == n_punkt + 1:
            # Only difference is header splitting
            verdict = "TRIVIAL"
            explanation = "Only difference is header line splitting (pySBD separates '=== Header ===' as its own segment)"
        elif n_pysbd == n_punkt:
            verdict = "UNCLEAR"
            explanation = "Same count, different boundaries — manual review needed"
        elif n_pysbd < n_punkt:
            verdict = "PYSBD_LIKELY_CORRECT"
            explanation = (
                f"Punkt over-splits ({n_punkt} vs {n_pysbd} sents) — likely splitting inside quotes or at abbreviations"
            )
        else:
            verdict = "PUNKT_LIKELY_CORRECT"
            explanation = f"pySBD over-splits ({n_pysbd} vs {n_punkt} sents) — may be splitting at non-boundary punctuation"
        # Refine: check if Punkt split inside a quote by looking at the actual text
        # Find sentences in Punkt that end with an unclosed quote
        for i, s in enumerate(punkt_sents[:-1]):
            # If a punkt sentence ends mid-quote and next starts lowercase or with continuation
            if s.rstrip().endswith("...") and i + 1 < len(punkt_sents):
                next_s = punkt_sents[i + 1].lstrip()
                if next_s and next_s[0].islower():
                    issues["punkt"].append(f"Split at ellipsis mid-sentence at sent [{i}]")
    elif pysbd_errors < punkt_errors:
        verdict = "PYSBD_CORRECT"
        explanation = f"pySBD has {pysbd_errors} issues vs Punkt's {punkt_errors}"
    elif punkt_errors < pysbd_errors:
        verdict = "PUNKT_CORRECT"
        explanation = f"Punkt has {punkt_errors} issues vs pySBD's {pysbd_errors}"
    else:
        verdict = "BOTH_WRONG"
        explanation = f"Both have issues: pySBD={pysbd_errors}, Punkt={punkt_errors}"

    return {
        "verdict": verdict,
        "explanation": explanation,
        "pysbd_issues": issues["pysbd"],
        "punkt_issues": issues["punkt"],
        "n_pysbd": n_pysbd,
        "n_punkt": n_punkt,
    }


# ── Analyze all disagreements ─────────────────────────────────────────────────

verdicts = {
    "PYSBD_CORRECT": [],
    "PUNKT_CORRECT": [],
    "PYSBD_LIKELY_CORRECT": [],
    "PUNKT_LIKELY_CORRECT": [],
    "BOTH_WRONG": [],
    "TRIVIAL": [],
    "UNCLEAR": [],
}

for i, rec in enumerate(data["disagreements"]):
    result = analyze_one(rec["paragraph"], rec["pysbd"], rec["punkt"])
    result["index"] = i + 1
    result["article"] = rec["article"]
    result["paragraph_preview"] = rec["paragraph"][:100]
    verdicts[result["verdict"]].append(result)


# ── Print report ──────────────────────────────────────────────────────────────

print("=" * 90)
print("DETAILED ANALYSIS: pySBD vs Punkt on Wikipedia Corpus")
print("=" * 90)
print(f"\nTotal disagreements analyzed: {len(data['disagreements'])}")
print()

for verdict_name, items in verdicts.items():
    if not items:
        continue
    print(f"\n{'─' * 90}")
    print(f"  {verdict_name}: {len(items)} cases")
    print(f"{'─' * 90}")

    for item in items:
        print(f"\n  #{item['index']} [{item['article']}] ({item['n_pysbd']} vs {item['n_punkt']} sents)")
        print(f"  Para: {item['paragraph_preview']}...")
        print(f"  → {item['explanation']}")
        if item["pysbd_issues"]:
            for iss in item["pysbd_issues"]:
                print(f"    pySBD issue: {iss}")
        if item["punkt_issues"]:
            for iss in item["punkt_issues"]:
                print(f"    Punkt issue: {iss}")

# Summary
print(f"\n\n{'=' * 90}")
print("SUMMARY")
print(f"{'=' * 90}")
print(f"  Total disagreements:       {len(data['disagreements'])}")
print()

pysbd_wins = len(verdicts["PYSBD_CORRECT"]) + len(verdicts["PYSBD_LIKELY_CORRECT"])
punkt_wins = len(verdicts["PUNKT_CORRECT"]) + len(verdicts["PUNKT_LIKELY_CORRECT"])
both_bad = len(verdicts["BOTH_WRONG"])
trivial = len(verdicts["TRIVIAL"])
unclear = len(verdicts["UNCLEAR"])

pysbd_def = len(verdicts["PYSBD_CORRECT"])
pysbd_likely = len(verdicts["PYSBD_LIKELY_CORRECT"])
print(f"  pySBD correct/better:      {pysbd_wins} ({pysbd_def} definite + {pysbd_likely} likely)")
punkt_def = len(verdicts["PUNKT_CORRECT"])
punkt_likely = len(verdicts["PUNKT_LIKELY_CORRECT"])
print(f"  Punkt correct/better:      {punkt_wins} ({punkt_def} definite + {punkt_likely} likely)")
print(f"  Both wrong:                {both_bad}")
print(f"  Trivial (header split):    {trivial}")
print(f"  Unclear:                   {unclear}")
print()

total = len(data["disagreements"])
agree = data["agree"]
total_paras = data["total_paragraphs"]
print(f"  Agreement rate:            {agree}/{total_paras} = {100 * agree / total_paras:.1f}%")
pysbd_err = punkt_wins + both_bad
pysbd_err_pct = 100 * pysbd_err / total_paras
print(
    f"  pySBD error rate:          {pysbd_err}/{total_paras} = {pysbd_err_pct:.1f}%"
    f" (cases where Punkt was better or both wrong)"
)
punkt_err = pysbd_wins + both_bad
punkt_err_pct = 100 * punkt_err / total_paras
print(
    f"  Punkt error rate:          {punkt_err}/{total_paras} = {punkt_err_pct:.1f}%"
    f" (cases where pySBD was better or both wrong)"
)

# Detailed examples of each category
print(f"\n\n{'=' * 90}")
print("NOTABLE EXAMPLES")
print(f"{'=' * 90}")


def show_diff(rec, result):
    """Show a detailed diff of one disagreement."""
    pysbd_s = rec["pysbd"]
    punkt_s = rec["punkt"]
    # Find where they first diverge
    min_len = min(len(pysbd_s), len(punkt_s))
    diverge_at = min_len
    for j in range(min_len):
        if pysbd_s[j] != punkt_s[j]:
            diverge_at = j
            break

    print(f"\n  First divergence at sentence [{diverge_at}]:")
    # Show context: the diverging sentences from each
    start = max(0, diverge_at - 1)
    end_p = min(len(pysbd_s), diverge_at + 3)
    end_k = min(len(punkt_s), diverge_at + 3)

    print("    pySBD:")
    for j in range(start, end_p):
        marker = ">>>" if j >= diverge_at else "   "
        text = pysbd_s[j][:120]
        print(f"      {marker} [{j}] {text}{'...' if len(pysbd_s[j]) > 120 else ''}")

    print("    Punkt:")
    for j in range(start, end_k):
        marker = ">>>" if j >= diverge_at else "   "
        text = punkt_s[j][:120]
        print(f"      {marker} [{j}] {text}{'...' if len(punkt_s[j]) > 120 else ''}")


# Show a few examples from each category
for category, label in [
    ("PYSBD_CORRECT", "pySBD CORRECT (Punkt has clear errors)"),
    ("PUNKT_CORRECT", "PUNKT CORRECT (pySBD has clear errors)"),
    ("BOTH_WRONG", "BOTH WRONG"),
]:
    items = verdicts[category]
    if not items:
        continue
    print(f"\n{'─' * 90}")
    print(f"  {label}")
    print(f"{'─' * 90}")

    for item in items[:5]:
        rec = data["disagreements"][item["index"] - 1]
        print(f"\n  #{item['index']} [{item['article']}]")
        print(f"  {item['explanation']}")
        for iss in item["pysbd_issues"]:
            print(f"    pySBD: {iss}")
        for iss in item["punkt_issues"]:
            print(f"    Punkt: {iss}")
        show_diff(rec, item)
