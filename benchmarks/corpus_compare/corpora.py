# -*- coding: utf-8 -*-
"""Fetch a variety of publicly available corpora for the SBD comparison.

Each corpus yields a list of ``Unit`` records — a small, self-contained passage
(a rule, a paragraph, or a treebank sentence-group) that segmenters run on and
that a reviewer can read in full. Ground-truth corpora (Golden Rules, Universal
Dependencies) carry ``gold`` sentence lists; free-text corpora (Wikipedia,
Project Gutenberg, legal opinions) carry ``gold=None`` and exist to surface
real-world divergences.

All network fetches are cached under ``corpora_cache/`` so re-runs are offline
and deterministic. Fetch failures are skipped with a warning rather than
aborting the run.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CACHE = _HERE / "corpora_cache"
_REPO_ROOT = _HERE.parent.parent
_UA = "sentencesplit-benchmark/1.0 (sentence boundary detection research)"


@dataclass
class Unit:
    corpus: str
    genre: str
    language: str
    unit_id: str
    text: str
    gold: list[str] | None = None


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _fetch(url: str, cache_name: str, *, retries: int = 4) -> str | None:
    import time

    _CACHE.mkdir(parents=True, exist_ok=True)
    path = _CACHE / cache_name
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            text = data.decode("utf-8", errors="replace")
            path.write_text(text, encoding="utf-8")
            return text
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))  # polite backoff for rate limits
                continue
            _log(f"  ! fetch failed {url}: {e}")
            return None
        except Exception as e:  # network failure: skip this source
            _log(f"  ! fetch failed {url}: {e}")
            return None


def _paragraphs(text: str, *, min_chars: int = 40, max_chars: int = 2000) -> list[str]:
    """Split free text into reviewable paragraph units (blank-line separated)."""
    out = []
    for block in re.split(r"\n\s*\n", text):
        para = " ".join(block.split())
        if min_chars <= len(para) <= max_chars and re.search(r"[.!?。！？]", para):
            out.append(para)
    return out


# ── Golden Rules (English, ground truth, vendored) ────────────────────────────


def golden_rules() -> list[Unit]:
    sys.path.insert(0, str(_REPO_ROOT / "benchmarks"))
    try:
        from english_golden_rules import GOLDEN_EN_RULES
    except Exception as e:
        _log(f"  ! golden rules unavailable: {e}")
        return []
    units = []
    for i, (text, expected) in enumerate(GOLDEN_EN_RULES, 1):
        units.append(Unit("golden_rules", "rule-test", "en", f"gr{i:02d}", text, gold=list(expected)))
    return units


# ── Universal Dependencies treebanks (ground truth, multilingual) ─────────────

# (repo suffix, file prefix, ISO code, genre). Test split: smallest, gold segmented.
_UD_TREEBANKS = [
    ("UD_English-EWT", "en_ewt", "en", "web"),
    ("UD_English-GUM", "en_gum", "en", "academic/varied"),
    ("UD_German-GSD", "de_gsd", "de", "news/wiki"),
    ("UD_French-GSD", "fr_gsd", "fr", "news/wiki"),
    ("UD_Spanish-GSD", "es_gsd", "es", "news/wiki"),
    ("UD_Italian-ISDT", "it_isdt", "it", "news/legal"),
    ("UD_Dutch-Alpino", "nl_alpino", "nl", "news"),
    ("UD_Russian-GSD", "ru_gsd", "ru", "wiki"),
    ("UD_Greek-GDT", "el_gdt", "el", "news/wiki"),
    ("UD_Chinese-GSD", "zh_gsd", "zh", "wiki"),
]


def _ud_parse(conllu: str, language: str) -> list[list[str]]:
    """Group consecutive ``# text =`` sentences into paragraph-sized units.

    Boundaries: ``# newpar`` / ``# newdoc`` markers, or a cap of 5 sentences.
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


def universal_dependencies(max_units_per_treebank: int = 30) -> list[Unit]:
    units = []
    for repo, prefix, lang, genre in _UD_TREEBANKS:
        url = f"https://raw.githubusercontent.com/UniversalDependencies/{repo}/master/{prefix}-ud-test.conllu"
        conllu = _fetch(url, f"ud_{prefix}_test.conllu")
        if not conllu:
            continue
        groups, joiner = _ud_parse(conllu, lang)
        kept = 0
        for gi, sentences in enumerate(groups):
            if len(sentences) < 2:  # need a real boundary to be interesting
                continue
            text = joiner.join(sentences)
            if len(text) > 2000:
                continue
            units.append(Unit(f"ud_{prefix}", genre, lang, f"{prefix}_{gi:04d}", text, gold=sentences))
            kept += 1
            if kept >= max_units_per_treebank:
                break
        _log(f"  UD {repo}: {kept} units")
    return units


# ── Wikipedia (free text, multi-domain, multilingual) ─────────────────────────

_WIKI = {
    "en": ["Albert Einstein", "DNA", "Roman Empire", "Jazz", "Black hole", "Coffee",
           "Supreme Court of the United States", "Photosynthesis", "Mount Everest", "Bitcoin"],
    "de": ["Albert Einstein", "Berlin"],
    "fr": ["Paris", "Napoléon Ier"],
    "es": ["Miguel de Cervantes", "Madrid"],
    "it": ["Leonardo da Vinci"],
    "nl": ["Amsterdam"],
    "ru": ["Москва"],
    "zh": ["北京"],
}  # fmt: skip


def wikipedia(max_paras_per_article: int = 8) -> list[Unit]:
    units = []
    for lang, titles in _WIKI.items():
        for title in titles:
            q = urllib.parse.quote(title)
            url = (
                f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts"
                f"&explaintext=1&format=json&redirects=1&titles={q}"
            )
            safe = re.sub(r"\W+", "_", f"{lang}_{title}")
            raw = _fetch(url, f"wiki_{safe}.json")
            if not raw:
                continue
            try:
                pages = json.loads(raw)["query"]["pages"]
                extract = next(iter(pages.values())).get("extract", "")
            except Exception:
                continue
            # Drop section headers ("== History =="); keep prose lines.
            lines = [ln for ln in extract.split("\n") if ln.strip() and not ln.strip().startswith("=")]
            paras = _paragraphs("\n\n".join(lines))
            for pi, para in enumerate(paras[:max_paras_per_article]):
                units.append(Unit(f"wikipedia_{lang}", "encyclopedic", lang, f"{safe}_{pi}", para))
    return units


# ── Project Gutenberg (free text, literary, public domain) ────────────────────

_GUTENBERG = [
    (1342, "Pride and Prejudice"),
    (2701, "Moby Dick"),
    (1661, "Adventures of Sherlock Holmes"),
    (11, "Alice in Wonderland"),
]


def gutenberg(max_paras_per_book: int = 12, excerpt_chars: int = 16000) -> list[Unit]:
    units = []
    for book_id, name in _GUTENBERG:
        url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
        raw = _fetch(url, f"gutenberg_{book_id}.txt")
        if not raw:
            continue
        m = re.search(r"\*\*\* START OF.*?\*\*\*", raw, re.S)
        body = raw[m.end() :] if m else raw
        m2 = re.search(r"\*\*\* END OF", body)
        body = body[: m2.start()] if m2 else body
        paras = _paragraphs(body[:excerpt_chars])
        safe = re.sub(r"\W+", "_", name)
        for pi, para in enumerate(paras[:max_paras_per_book]):
            units.append(Unit("gutenberg", "literary", "en", f"{safe}_{pi}", para))
    return units


# ── Legal opinions (free text, vendored) ──────────────────────────────────────


def legal() -> list[Unit]:
    units = []
    eval_dir = _REPO_ROOT / "eval"
    for f in sorted(eval_dir.glob("*.txt")):
        paras = _paragraphs(f.read_text(encoding="utf-8", errors="replace"), max_chars=2200)
        for pi, para in enumerate(paras[:15]):
            units.append(Unit("legal", "legal", "en", f"{f.stem}_{pi}", para))
    return units


def load_all() -> list[Unit]:
    units: list[Unit] = []
    for name, fn in [
        ("golden_rules", golden_rules),
        ("universal_dependencies", universal_dependencies),
        ("wikipedia", wikipedia),
        ("gutenberg", gutenberg),
        ("legal", legal),
    ]:
        _log(f"[corpora] loading {name} ...")
        try:
            got = fn()
        except Exception as e:
            _log(f"  ! {name} failed: {e}")
            got = []
        _log(f"  -> {len(got)} units")
        units.extend(got)
    return units


if __name__ == "__main__":
    units = load_all()
    from collections import Counter

    by_corpus = Counter(u.corpus for u in units)
    by_lang = Counter(u.language for u in units)
    print(f"\nTOTAL units: {len(units)}")
    print("by corpus:", dict(by_corpus))
    print("by language:", dict(by_lang))
    print("with gold:", sum(1 for u in units if u.gold is not None))
    print("\nsample:", json.dumps(asdict(units[0]), ensure_ascii=False)[:300])
