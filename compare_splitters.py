#!/usr/bin/env python3
"""Compare pySBD vs NLTK Punkt sentence splitting on Wikipedia articles."""

import json
import re

import nltk.data
import requests

import pysbd

# ── Fetch Wikipedia articles ──────────────────────────────────────────────────

ARTICLES = [
    # Original 5
    "Albert_Einstein",
    "Python_(programming_language)",
    "World_War_II",
    "Marie_Curie",
    "Photosynthesis",
    # Science & technology
    "Quantum_mechanics",
    "DNA",
    "Climate_change",
    "Artificial_intelligence",
    "General_relativity",
    "Evolution",
    "Penicillin",
    "CRISPR_gene_editing",
    # History & politics
    "Roman_Empire",
    "French_Revolution",
    "Cold_War",
    "Mahatma_Gandhi",
    "Nelson_Mandela",
    "Abraham_Lincoln",
    "United_Nations",
    # Arts & literature
    "William_Shakespeare",
    "Ludwig_van_Beethoven",
    "Pablo_Picasso",
    "The_Great_Gatsby",
    # Geography & places
    "Amazon_rainforest",
    "Mount_Everest",
    "New_York_City",
    "Tokyo",
    # Philosophy & social sciences
    "Philosophy",
    "Economics",
    "Psychology",
    # Medicine & biology
    "COVID-19",
    "Human_brain",
    "Vaccine",
    # Computing
    "Linux",
    "Internet",
    "Machine_learning",
    "Bitcoin",
    # Sports & culture
    "Olympic_Games",
    "FIFA_World_Cup",
    "Jazz",
]


def fetch_wikipedia_text(title: str) -> str:
    """Fetch plain-text extract of a Wikipedia article."""
    resp = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": "1",
            "format": "json",
        },
        headers={"User-Agent": "pySBD-comparison/1.0 (research script)"},
        timeout=15,
    )
    resp.raise_for_status()
    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    return page.get("extract", "")


def build_corpus() -> dict[str, str]:
    corpus = {}
    for title in ARTICLES:
        print(f"  Fetching {title}...")
        text = fetch_wikipedia_text(title)
        if text:
            corpus[title] = text
    return corpus


# ── Split into paragraphs ────────────────────────────────────────────────────


def get_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs (double-newline separated)."""
    paragraphs = re.split(r"\n{2,}", text)
    result = []
    for p in paragraphs:
        p = p.strip()
        if len(p) <= 40 or "." not in p:
            continue
        # Skip paragraphs with embedded LaTeX math markup (unfair to both splitters)
        if "\\displaystyle" in p or "{\\" in p:
            continue
        result.append(p)
    return result


# ── Compare ──────────────────────────────────────────────────────────────────


def compare(corpus: dict[str, str]):
    seg = pysbd.Segmenter(language="en", clean=False)
    punkt = nltk.data.load("tokenizers/punkt_tab/english.pickle")

    total_paragraphs = 0
    agree_paragraphs = 0
    disagree_records = []

    for title, text in corpus.items():
        paragraphs = get_paragraphs(text)
        for para in paragraphs:
            total_paragraphs += 1

            pysbd_sents = seg.segment(para)
            punkt_sents = punkt.tokenize(para)

            # Normalize for comparison: strip whitespace from each sentence
            pysbd_norm = [s.strip() for s in pysbd_sents if s.strip()]
            punkt_norm = [s.strip() for s in punkt_sents if s.strip()]

            if pysbd_norm == punkt_norm:
                agree_paragraphs += 1
            else:
                disagree_records.append(
                    {
                        "article": title,
                        "paragraph": para,
                        "pysbd": pysbd_norm,
                        "punkt": punkt_norm,
                    }
                )

    return total_paragraphs, agree_paragraphs, disagree_records


# ── Judgment ──────────────────────────────────────────────────────────────────


def judge_difference(para: str, pysbd_sents: list[str], punkt_sents: list[str]) -> str:
    """Simple heuristic to judge which splitter is correct."""
    reasons = []

    # Check for common error patterns
    for i, s in enumerate(pysbd_sents):
        # pySBD incorrectly split on abbreviation
        if s.rstrip().endswith((".", "!", "?")) is False and i < len(pysbd_sents) - 1:
            reasons.append("pySBD: possible false split (sentence doesn't end with punctuation)")

    for i, s in enumerate(punkt_sents):
        if s.rstrip().endswith((".", "!", "?")) is False and i < len(punkt_sents) - 1:
            reasons.append("Punkt: possible false split (sentence doesn't end with punctuation)")

    # Check for obvious abbreviation errors
    abbr_pattern = re.compile(
        r"\b(?:Dr|Mr|Mrs|Ms|Prof|Rev|Gen|Corp|Inc|Ltd|Jr|Sr|vs|etc|Fig|fig|Vol|vol|No|no|approx|est|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|St|Ave|Blvd)\.$"
    )
    for sents, name in [(pysbd_sents, "pySBD"), (punkt_sents, "Punkt")]:
        for i, s in enumerate(sents[:-1]):  # skip last
            if abbr_pattern.search(s.rstrip()):
                reasons.append(f"{name}: likely false split after abbreviation '{s.rstrip()[-8:]}'")

    # Check for splits inside parentheses or quotes
    for sents, name in [(pysbd_sents, "pySBD"), (punkt_sents, "Punkt")]:
        open_parens = 0
        open_quotes = 0
        for i, s in enumerate(sents):
            open_parens += s.count("(") - s.count(")")
            open_quotes += s.count('"') - s.count('"')  # Rough check
            if open_parens > 0 and i < len(sents) - 1:
                reasons.append(f"{name}: split inside unclosed parentheses")
                open_parens = 0  # reset to avoid duplicates
            if open_quotes % 2 != 0 and i < len(sents) - 1:
                reasons.append(f"{name}: split inside unclosed quotes")
                open_quotes = 0

    if not reasons:
        # Count sentences — often more splits = over-splitting
        if len(pysbd_sents) > len(punkt_sents):
            reasons.append("pySBD splits more finely (possible over-splitting)")
        elif len(punkt_sents) > len(pysbd_sents):
            reasons.append("Punkt splits more finely (possible over-splitting)")
        else:
            reasons.append("Same number of sentences but different boundaries")

    return "; ".join(reasons)


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    print("Fetching Wikipedia articles...")
    corpus = build_corpus()
    print(f"Fetched {len(corpus)} articles, {sum(len(t) for t in corpus.values()):,} chars total.\n")

    print("Comparing pySBD vs Punkt...")
    total, agree, disagreements = compare(corpus)

    print(f"\n{'=' * 80}")
    print(f"RESULTS: {total} paragraphs compared")
    print(f"  Agree:    {agree} ({100 * agree / total:.1f}%)")
    print(f"  Disagree: {len(disagreements)} ({100 * len(disagreements) / total:.1f}%)")
    print(f"{'=' * 80}\n")

    # Show a sample of disagreements
    MAX_SHOW = 30
    for idx, rec in enumerate(disagreements[:MAX_SHOW]):
        para = rec["paragraph"]
        pysbd_s = rec["pysbd"]
        punkt_s = rec["punkt"]

        para_display = para[:200] + "..." if len(para) > 200 else para

        print(f"── Disagreement #{idx + 1} ({rec['article']}) ──")
        print(f"Paragraph: {para_display}")
        print(f"  pySBD ({len(pysbd_s)} sents):")
        for i, s in enumerate(pysbd_s):
            marker = "→ " if i >= len(punkt_s) or s != punkt_s[i] else "  "
            print(f"    {marker}[{i}] {s[:120]}{'...' if len(s) > 120 else ''}")
        print(f"  Punkt ({len(punkt_s)} sents):")
        for i, s in enumerate(punkt_s):
            marker = "→ " if i >= len(pysbd_s) or s != pysbd_s[i] else "  "
            print(f"    {marker}[{i}] {s[:120]}{'...' if len(s) > 120 else ''}")
        print()

    if len(disagreements) > MAX_SHOW:
        print(f"... and {len(disagreements) - MAX_SHOW} more disagreements.\n")

    # Save ALL results to JSON for further analysis
    output = {
        "total_paragraphs": total,
        "agree": agree,
        "disagree": len(disagreements),
        "disagreements": disagreements,
    }
    with open("/Users/yi/Code/pySBD/comparison_results.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Full results saved to comparison_results.json ({len(disagreements)} disagreements)")


if __name__ == "__main__":
    main()
