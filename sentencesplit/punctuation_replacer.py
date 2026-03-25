# -*- coding: utf-8 -*-
from __future__ import annotations

# Punctuation replacement pairs (literal str.replace)
_PUNCT_SUBS = [
    (".", "∯"),
    ("。", "&ᓰ&"),
    ("．", "&ᓱ&"),
    ("！", "&ᓳ&"),
    ("!", "&ᓴ&"),
    ("?", "&ᓷ&"),
    ("？", "&ᓸ&"),
]

# Characters that need escaping/unescaping
_ESCAPE_PAIRS = [
    ("(", "\\("),
    (")", "\\)"),
    ("[", "\\["),
    ("]", "\\]"),
    ("-", "\\-"),
]

_NEEDS_ESCAPE = frozenset(c for c, _ in _ESCAPE_PAIRS)


def replace_punctuation(match, match_type: str | None = None) -> str:
    text = match.group()

    # Only escape/unescape if text contains regex-reserved chars
    needs_escape = any(c in text for c in _NEEDS_ESCAPE)
    if needs_escape:
        for orig, escaped in _ESCAPE_PAIRS:
            text = text.replace(orig, escaped)

    for old, new in _PUNCT_SUBS:
        text = text.replace(old, new)

    if match_type != "single":
        text = text.replace("'", "&⎋&")

    if needs_escape:
        for orig, escaped in _ESCAPE_PAIRS:
            text = text.replace(escaped, orig)

    return text
