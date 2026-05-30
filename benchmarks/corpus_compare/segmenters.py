# -*- coding: utf-8 -*-
"""Segmenter adapters for the cross-library comparison harness.

Every adapter exposes a uniform batch interface

    segment_batch(texts: list[str], language: str) -> list[list[str]]

returning, for each input text, a list of sentences normalized as
``s.strip()`` with empties dropped (so comparisons ignore trailing
whitespace differences and focus on *boundary* decisions).

Adapters self-report availability: native libraries that fail to import on
this platform (e.g. blingfire / spaCy / stanza on some ARM boxes) are recorded
with a reason and excluded rather than crashing the run.
"""

from __future__ import annotations

import json
import subprocess
import warnings
from dataclasses import dataclass, field
from pathlib import Path

warnings.filterwarnings("ignore")

_HERE = Path(__file__).resolve().parent


def _norm(sentences) -> list[str]:
    return [s.strip() for s in sentences if s and s.strip()]


def _probe_import(module: str) -> tuple[bool, str]:
    """Import ``module`` in a *subprocess* so a hard crash (e.g. SIGILL from a
    native BLAS kernel mis-tuned for this CPU) can't take down the harness.

    Returns (ok, reason). A negative return code means the child died on a
    signal (e.g. -4 == SIGILL) — impossible to catch with try/except in-process,
    which is exactly why we isolate it here.
    """
    import sys

    proc = subprocess.run(
        [sys.executable, "-c", f"import warnings; warnings.filterwarnings('ignore'); import {module}"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode == 0:
        return True, ""
    if proc.returncode < 0:
        return False, f"crashed importing {module} (signal {-proc.returncode}; native/ARM incompatibility)"
    tail = (proc.stderr.strip().splitlines() or [""])[-1]
    return False, f"import {module} failed (exit {proc.returncode}): {tail[:140]}"


@dataclass
class Segmenter:
    name: str
    kind: str  # "rule-based" | "statistical" | "neural"
    description: str
    _batch_fn: object = field(repr=False, default=None)
    available: bool = True
    unavailable_reason: str = ""
    # ISO 639-1 codes the adapter will attempt. None => "any language".
    languages: set[str] | None = None

    def supports(self, language: str) -> bool:
        if not self.available:
            return False
        return self.languages is None or language in self.languages

    def segment_batch(self, texts: list[str], language: str) -> list[list[str]]:
        return self._batch_fn(texts, language)


# ── sentencesplit (this library) ──────────────────────────────────────────────


def _make_sentencesplit() -> Segmenter:
    try:
        import sentencesplit

        cache: dict[str, object] = {}

        def seg(texts, language):
            key = language
            if key not in cache:
                cache[key] = sentencesplit.Segmenter(language=language, clean=False, char_span=False)
            s = cache[key]
            return [_norm(s.segment(t)) for t in texts]

        return Segmenter("sentencesplit", "rule-based", "This library (pySBD-derived, rule-based).", seg)
    except Exception as e:  # pragma: no cover - import guard
        return Segmenter("sentencesplit", "rule-based", "This library.", None, available=False, unavailable_reason=repr(e))


# ── pysbd (direct Python ancestor) ────────────────────────────────────────────

# pysbd's supported language set (mirrors pragmatic_segmenter).
_PYSBD_LANGS = {
    "en", "es", "de", "fr", "it", "ru", "zh", "ja", "ar", "hi", "nl", "pl",
    "el", "fa", "my", "ur", "am", "hy", "da", "sk", "kk", "mr", "bg",
}  # fmt: skip


def _make_pysbd() -> Segmenter:
    try:
        import pysbd

        cache: dict[str, object] = {}

        def seg(texts, language):
            if language not in cache:
                cache[language] = pysbd.Segmenter(language=language, clean=False)
            s = cache[language]
            return [_norm(s.segment(t)) for t in texts]

        return Segmenter(
            "pysbd",
            "rule-based",
            "Python Sentence Boundary Disambiguation (port of pragmatic_segmenter).",
            seg,
            languages=set(_PYSBD_LANGS),
        )
    except Exception as e:
        return Segmenter("pysbd", "rule-based", "pySBD.", None, available=False, unavailable_reason=repr(e))


# ── NLTK Punkt (statistical) ──────────────────────────────────────────────────

# ISO 639-1 -> NLTK punkt model name.
_PUNKT_LANGS = {
    "en": "english", "de": "german", "fr": "french", "es": "spanish",
    "it": "italian", "nl": "dutch", "pl": "polish", "ru": "russian",
    "da": "danish", "el": "greek",
}  # fmt: skip


def _make_punkt() -> Segmenter:
    try:
        import nltk

        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)

        def seg(texts, language):
            model = _PUNKT_LANGS.get(language, "english")
            return [_norm(nltk.sent_tokenize(t, language=model)) for t in texts]

        return Segmenter(
            "punkt",
            "statistical",
            "NLTK Punkt unsupervised sentence tokenizer.",
            seg,
            languages=set(_PUNKT_LANGS),
        )
    except Exception as e:
        return Segmenter("punkt", "statistical", "NLTK Punkt.", None, available=False, unavailable_reason=repr(e))


# ── syntok (rule-based, European-language oriented) ───────────────────────────

_SYNTOK_LANGS = {"en", "de", "es", "fr", "it", "nl", "pl", "da"}


def _make_syntok() -> Segmenter:
    try:
        import syntok.segmenter as syntok_segmenter

        def one(text):
            sentences = []
            for paragraph in syntok_segmenter.process(text):
                for sentence in paragraph:
                    sentences.append("".join(t.spacing + t.value for t in sentence).strip())
            return _norm(sentences)

        def seg(texts, language):
            return [one(t) for t in texts]

        return Segmenter(
            "syntok",
            "rule-based",
            "syntok segmenter (tokenizer-driven).",
            seg,
            languages=set(_SYNTOK_LANGS),
        )
    except Exception as e:
        return Segmenter("syntok", "rule-based", "syntok.", None, available=False, unavailable_reason=repr(e))


# ── blingfire / spaCy / stanza (native; often unavailable on ARM) ─────────────


def _make_blingfire() -> Segmenter:
    ok, reason = _probe_import("blingfire")
    if not ok:
        return Segmenter("blingfire", "neural", "BlingFire.", None, available=False, unavailable_reason=reason)
    import blingfire

    def seg(texts, language):
        return [_norm(blingfire.text_to_sentences(t).split("\n")) for t in texts]

    return Segmenter("blingfire", "neural", "Microsoft BlingFire (compiled FST).", seg)


def _make_spacy_sentencizer() -> Segmenter:
    ok, reason = _probe_import("spacy")
    if not ok:
        return Segmenter(
            "spacy_sentencizer", "rule-based", "spaCy sentencizer.", None, available=False, unavailable_reason=reason
        )
    import spacy

    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    def seg(texts, language):
        return [_norm([s.text for s in nlp(t).sents]) for t in texts]

    return Segmenter("spacy_sentencizer", "rule-based", "spaCy rule-based sentencizer.", seg, languages={"en"})


def _make_stanza() -> Segmenter:
    ok, reason = _probe_import("stanza")
    if not ok:
        return Segmenter("stanza", "neural", "Stanza.", None, available=False, unavailable_reason=reason)
    import stanza

    nlp = stanza.Pipeline(lang="en", processors="tokenize", verbose=False)

    def seg(texts, language):
        return [_norm([s.text for s in nlp(t).sentences]) for t in texts]

    return Segmenter("stanza", "neural", "Stanza neural tokenizer.", seg, languages={"en"})


# ── pragmatic_segmenter (Ruby reference implementation) ───────────────────────

# pragmatic_segmenter's supported language set.
_PRAGMATIC_LANGS = set(_PYSBD_LANGS)


def _make_pragmatic() -> Segmenter:
    runner = _HERE / "pragmatic_runner.rb"
    try:
        probe = subprocess.run(
            ["ruby", "-e", "require 'pragmatic_segmenter'"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if probe.returncode != 0:
            raise RuntimeError(probe.stderr.strip()[:200] or "ruby probe failed")

        def seg(texts, language):
            payload = json.dumps({"language": language, "texts": texts})
            proc = subprocess.run(
                ["ruby", str(runner)],
                input=payload,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip()[:300])
            out = json.loads(proc.stdout)["sentences"]
            return [_norm(s) for s in out]

        return Segmenter(
            "pragmatic_segmenter",
            "rule-based",
            "Original Ruby pragmatic_segmenter (reference implementation).",
            seg,
            languages=set(_PRAGMATIC_LANGS),
        )
    except Exception as e:
        return Segmenter(
            "pragmatic_segmenter",
            "rule-based",
            "Ruby pragmatic_segmenter.",
            None,
            available=False,
            unavailable_reason=repr(e),
        )


def build_registry() -> list[Segmenter]:
    """Construct every adapter; unavailable ones carry a reason and are kept for reporting."""
    return [
        _make_sentencesplit(),
        _make_pysbd(),
        _make_pragmatic(),
        _make_punkt(),
        _make_syntok(),
        _make_blingfire(),
        _make_spacy_sentencizer(),
        _make_stanza(),
    ]


if __name__ == "__main__":
    for s in build_registry():
        status = "OK" if s.available else f"UNAVAILABLE ({s.unavailable_reason[:70]})"
        langs = "any" if s.languages is None else ",".join(sorted(s.languages))
        print(f"{s.name:22} {s.kind:12} [{langs[:40]:40}] {status}")
