#!/usr/bin/env python3
"""Refined analysis: examine each disagreement closely, accounting for header splits."""

import json
import re

with open("analysis/pysbd_vs_punkt_results.json") as f:
    data = json.load(f)


KNOWN_ABBRS_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Rev|Gen|Gov|Sgt|Cpl|Pvt|Corp|Inc|Ltd|Jr|Sr|vs|etc|Fig|fig|Vol|vol"
    r"|No|no|approx|est|ca|dept|Dept|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r"|St|Ave|Blvd|Rd|Mt|Ft|Ph\.D|M\.D|B\.A|M\.A|B\.S|M\.S|i\.e|e\.g|al)\.$"
)
INITIAL_RE = re.compile(r"\b[A-Z]\.$")
HEADER_RE = re.compile(r"^={2,}\s.*\s={2,}$")


def is_header(s: str) -> bool:
    return bool(HEADER_RE.match(s.strip()))


def classify(para, pysbd_sents, punkt_sents):
    """Return (verdict, explanation, details)."""
    # If pySBD splits header off and Punkt doesn't, remove headers and re-compare
    pysbd_content = [s for s in pysbd_sents if not is_header(s)]
    punkt_content = [s for s in punkt_sents if not is_header(s)]

    pysbd_norm = [s.strip() for s in pysbd_content if s.strip()]
    punkt_norm = [s.strip() for s in punkt_content if s.strip()]

    # Case: after removing headers, they agree
    if pysbd_norm == punkt_norm:
        return "HEADER_ONLY", "Only difference is section header splitting", {}

    # Now look at actual content differences
    issues = {"pysbd": [], "punkt": []}

    for name, sents in [("pysbd", pysbd_content), ("punkt", punkt_content)]:
        for i, s in enumerate(sents[:-1]):
            stripped = s.rstrip()
            # Check abbreviation splits
            if KNOWN_ABBRS_RE.search(stripped):
                abbr = KNOWN_ABBRS_RE.search(stripped).group()
                issues[name].append(f"False split after '{abbr}' at [{i}]")
            elif INITIAL_RE.search(stripped):
                # Check if next sentence starts with what looks like a continuation
                if i + 1 < len(sents):
                    next_s = sents[i + 1].lstrip()
                    # "W. E. B." split from "Du Bois" — next starts with uppercase
                    # But a proper sentence also starts with uppercase
                    # If next sentence doesn't start with a typical sentence starter
                    # and the initial is preceded by another initial, it's a false split
                    if re.search(r"[A-Z]\.\s+[A-Z]\.$", stripped):
                        issues[name].append(f"False split after initials at [{i}]")
                    elif next_s and not next_s[0].isupper():
                        issues[name].append(f"False split after initial at [{i}]")

        # Check for orphan fragments
        for i, s in enumerate(sents):
            stripped = s.strip()
            if stripped in (".", "..", "...", "....") and i > 0:
                issues[name].append(f"Orphan punctuation fragment '{stripped}' at [{i}]")
            elif len(stripped) < 5 and i > 0 and i < len(sents) - 1:
                issues[name].append(f"Tiny fragment '{stripped}' at [{i}]")

        # Check parenthesis balance
        depth = 0
        for i, s in enumerate(sents):
            if depth > 0 and i > 0:
                issues[name].append(f"Split inside unclosed parens at [{i}]")
                depth = 0  # reset
            depth += s.count("(") - s.count(")")

    # Find where they diverge and look at the actual text
    min_len = min(len(pysbd_norm), len(punkt_norm))
    for i in range(min_len):
        if pysbd_norm[i] != punkt_norm[i]:
            # Analyze the divergence point
            # Check if Punkt split inside a quote
            p_sent = pysbd_norm[i]
            k_sent = punkt_norm[i]

            # If pySBD sentence is longer and contains the Punkt sentence as a prefix
            if p_sent.startswith(k_sent[:20]) and len(p_sent) > len(k_sent):
                # Punkt may have over-split
                # Check what Punkt cut at
                if k_sent.rstrip()[-1] == '"' or k_sent.rstrip()[-1] == "\u201d":
                    issues["punkt"].append(f"Possible false split at end of quote at [{i}]")
                if k_sent.rstrip().endswith("..."):
                    issues["punkt"].append(f"Possible false split at ellipsis at [{i}]")
            elif k_sent.startswith(p_sent[:20]) and len(k_sent) > len(p_sent):
                # pySBD may have over-split
                if p_sent.rstrip()[-1] == '"' or p_sent.rstrip()[-1] == "\u201d":
                    issues["pysbd"].append(f"Possible false split at end of quote at [{i}]")
            break

    pe = len(issues["pysbd"])
    ke = len(issues["punkt"])

    if pe == 0 and ke == 0:
        # No detected issues — look at sentence counts
        np = len(pysbd_norm)
        nk = len(punkt_norm)
        if np == nk:
            return "UNCLEAR", f"Same count ({np}), different boundaries", issues
        elif abs(np - nk) == 1:
            return "MINOR_DIFF", f"Slight split difference ({np} vs {nk})", issues
        else:
            more = "pySBD" if np > nk else "Punkt"
            return "UNCLEAR", f"{more} splits more ({np} vs {nk}), no clear errors", issues
    elif pe < ke:
        return "PYSBD_BETTER", f"pySBD: {pe} issues, Punkt: {ke} issues", issues
    elif ke < pe:
        return "PUNKT_BETTER", f"pySBD: {pe} issues, Punkt: {ke} issues", issues
    else:
        return "BOTH_ISSUES", f"Both have {pe} issue(s) each", issues


# ── Run analysis ──────────────────────────────────────────────────────────────

results = {}
for i, rec in enumerate(data["disagreements"]):
    verdict, explanation, issues = classify(rec["paragraph"], rec["pysbd"], rec["punkt"])
    results.setdefault(verdict, []).append(
        {
            "idx": i + 1,
            "article": rec["article"],
            "explanation": explanation,
            "issues": issues,
            "n_pysbd": len(rec["pysbd"]),
            "n_punkt": len(rec["punkt"]),
            "para_preview": rec["paragraph"][:80],
        }
    )


# ── Print ─────────────────────────────────────────────────────────────────────

print("=" * 80)
print("REFINED ANALYSIS: pySBD vs Punkt on Wikipedia Corpus")
print("=" * 80)
total_paras = data["total_paragraphs"]
agree = data["agree"]
disagree = len(data["disagreements"])

print(f"\nCorpus: 5 Wikipedia articles, {total_paras} paragraphs")
print(f"Agreement: {agree}/{total_paras} ({100 * agree / total_paras:.1f}%)")
print(f"Disagreements: {disagree}/{total_paras} ({100 * disagree / total_paras:.1f}%)")

print(f"\n{'─' * 80}")
print("BREAKDOWN OF DISAGREEMENTS:")
print(f"{'─' * 80}")

category_order = [
    ("HEADER_ONLY", "Header-only differences (not real errors)"),
    ("PYSBD_BETTER", "pySBD correct / Punkt has errors"),
    ("PUNKT_BETTER", "Punkt correct / pySBD has errors"),
    ("BOTH_ISSUES", "Both have errors"),
    ("MINOR_DIFF", "Minor differences (1-sentence off, no clear errors)"),
    ("UNCLEAR", "Unclear / needs manual review"),
]

for key, label in category_order:
    items = results.get(key, [])
    if not items:
        continue
    print(f"\n  {label}: {len(items)}")
    for item in items:
        tag = f"#{item['idx']}"
        art = item["article"][:20]
        n = f"{item['n_pysbd']}v{item['n_punkt']}"
        print(f"    {tag:>4} [{art:<20}] ({n:>5}) {item['explanation']}")
        for name in ("pysbd", "punkt"):
            for iss in item["issues"].get(name, []):
                print(f"          {'pySBD' if name == 'pysbd' else 'Punkt'}: {iss}")


# ── Summary table ─────────────────────────────────────────────────────────────

header_only = len(results.get("HEADER_ONLY", []))
pysbd_better = len(results.get("PYSBD_BETTER", []))
punkt_better = len(results.get("PUNKT_BETTER", []))
both_issues = len(results.get("BOTH_ISSUES", []))
minor = len(results.get("MINOR_DIFF", []))
unclear = len(results.get("UNCLEAR", []))

print(f"\n\n{'=' * 80}")
print("FINAL SUMMARY")
print(f"{'=' * 80}")
print(f"""
  Paragraphs tested:        {total_paras}
  Full agreement:            {agree} ({100 * agree / total_paras:.1f}%)
  Header-only difference:    {header_only} ({100 * header_only / total_paras:.1f}%)
  ─────────────────────────────────
  Effective agreement:       {agree + header_only} ({100 * (agree + header_only) / total_paras:.1f}%)

  pySBD better than Punkt:   {pysbd_better}
  Punkt better than pySBD:   {punkt_better}
  Both have errors:          {both_issues}
  Minor / no clear winner:   {minor}
  Unclear:                   {unclear}
""")

# Characterize the error types
print(f"{'=' * 80}")
print("ERROR TYPE ANALYSIS")
print(f"{'=' * 80}")

pysbd_error_types = {}
punkt_error_types = {}

for key in results:
    for item in results[key]:
        for iss in item["issues"].get("pysbd", []):
            category = iss.split(" at ")[0] if " at " in iss else iss
            pysbd_error_types[category] = pysbd_error_types.get(category, 0) + 1
        for iss in item["issues"].get("punkt", []):
            category = iss.split(" at ")[0] if " at " in iss else iss
            punkt_error_types[category] = punkt_error_types.get(category, 0) + 1

print("\n  pySBD error types:")
for err, count in sorted(pysbd_error_types.items(), key=lambda x: -x[1]):
    print(f"    {count:>3}x  {err}")

print("\n  Punkt error types:")
for err, count in sorted(punkt_error_types.items(), key=lambda x: -x[1]):
    print(f"    {count:>3}x  {err}")

print(f"\n  Total detected issues: pySBD={sum(pysbd_error_types.values())}, Punkt={sum(punkt_error_types.values())}")
