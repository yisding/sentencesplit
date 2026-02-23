#!/usr/bin/env python3
"""Small Wikipedia comparison: sentencesplit vs pySBD vs NLTK Punkt."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

import nltk
import nltk.data
import pysbd
import requests
import sentencesplit

ARTICLES = [
    "Albert_Einstein",
    "Python_(programming_language)",
    "World_War_II",
    "Marie_Curie",
    "Photosynthesis",
    "Quantum_mechanics",
    "DNA",
    "Climate_change",
    "Artificial_intelligence",
    "General_relativity",
    "Evolution",
    "Penicillin",
    "CRISPR_gene_editing",
    "Roman_Empire",
    "French_Revolution",
    "Cold_War",
    "Mahatma_Gandhi",
    "Nelson_Mandela",
    "Abraham_Lincoln",
    "United_Nations",
    "William_Shakespeare",
    "Ludwig_van_Beethoven",
    "Pablo_Picasso",
    "The_Great_Gatsby",
    "Amazon_rainforest",
    "Mount_Everest",
    "New_York_City",
    "Tokyo",
    "Philosophy",
    "Economics",
]
MAX_PARAGRAPHS_PER_ARTICLE = 10
MIN_PARAGRAPH_LEN = 80
USER_AGENT = "sentencesplit-eval/1.0 (research)"


@dataclass
class Record:
    id: int
    article: str
    paragraph: str
    sentencesplit: list[str]
    pysbd: list[str]
    punkt: list[str]
    verdict_sentencesplit: str
    verdict_pysbd: str
    verdict_punkt: str
    notes: str


def fetch_wikipedia_text(title: str) -> str:
    resp = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": "1",
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    pages = resp.json()["query"]["pages"]
    page = next(iter(pages.values()))
    return page.get("extract", "")


def get_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for p in re.split(r"\n{2,}", text):
        p = p.strip()
        if len(p) > MIN_PARAGRAPH_LEN and "." in p:
            paragraphs.append(p)
    return paragraphs


def _has_orphan_ellipsis(sents: list[str]) -> bool:
    return any(s.strip() == "..." for s in sents)


def _has_w_e_b_split(sents: list[str]) -> bool:
    return any(s.endswith("W. E. B.") for s in sents)


def _quote_fragment_split(sents: list[str]) -> bool:
    for i in range(len(sents) - 1):
        if sents[i].count('"') % 2 == 1 and sents[i + 1].count('"') % 2 == 1:
            return True
    return False


def judge(sents: list[str], paragraph: str) -> tuple[str, str]:
    if _has_orphan_ellipsis(sents):
        return "incorrect", "Creates standalone ellipsis fragment."
    if _has_w_e_b_split(sents):
        return "incorrect", "Splits inside the name 'W. E. B. Du Bois'."
    if _quote_fragment_split(sents):
        return "incorrect", "Splits quoted material into fragments."
    if paragraph.startswith("===") and len(sents) > 0 and "\n" in sents[0]:
        return "incorrect", "Merges section heading with body sentence."
    return "correct", "No obvious boundary error in this paragraph."


def main() -> None:
    nltk.download("punkt_tab", quiet=True)
    punkt = nltk.data.load("tokenizers/punkt_tab/english.pickle")
    ss = sentencesplit.Segmenter(language="en", clean=False)
    ps = pysbd.Segmenter(language="en", clean=False)

    raw_paras: list[tuple[str, str]] = []
    for article in ARTICLES:
        article_paras = get_paragraphs(fetch_wikipedia_text(article))[:MAX_PARAGRAPHS_PER_ARTICLE]
        for p in article_paras:
            raw_paras.append((article, p))

    records: list[Record] = []
    for idx, (article, para) in enumerate(raw_paras, start=1):
        ss_s = [s.strip() for s in ss.segment(para) if s.strip()]
        ps_s = [s.strip() for s in ps.segment(para) if s.strip()]
        pk_s = [s.strip() for s in punkt.tokenize(para) if s.strip()]

        ss_v, ss_n = judge(ss_s, para)
        ps_v, ps_n = judge(ps_s, para)
        pk_v, pk_n = judge(pk_s, para)

        note_parts = []
        if ss_s != ps_s:
            note_parts.append("sentencesplit differs from pySBD")
        if ss_s != pk_s:
            note_parts.append("sentencesplit differs from punkt")
        notes = "; ".join(note_parts) if note_parts else "all three agree"

        records.append(
            Record(
                id=idx,
                article=article,
                paragraph=para,
                sentencesplit=ss_s,
                pysbd=ps_s,
                punkt=pk_s,
                verdict_sentencesplit=ss_v,
                verdict_pysbd=ps_v,
                verdict_punkt=pk_v,
                notes=f"{notes}. ss: {ss_n} ps: {ps_n} punkt: {pk_n}",
            )
        )

    summary = {
        "articles": len(ARTICLES),
        "max_paragraphs_per_article": MAX_PARAGRAPHS_PER_ARTICLE,
        "paragraphs": len(records),
        "sentencesplit_incorrect": sum(1 for r in records if r.verdict_sentencesplit == "incorrect"),
        "pysbd_incorrect": sum(1 for r in records if r.verdict_pysbd == "incorrect"),
        "punkt_incorrect": sum(1 for r in records if r.verdict_punkt == "incorrect"),
        "ss_vs_pysbd_differences": sum(1 for r in records if r.sentencesplit != r.pysbd),
        "ss_vs_punkt_differences": sum(1 for r in records if r.sentencesplit != r.punkt),
    }

    out = {"summary": summary, "records": [asdict(r) for r in records]}
    with open("analysis/wiki_small_comparison.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
