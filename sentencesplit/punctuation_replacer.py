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


def replace_punctuation(match, match_type: str | None = None) -> str:
    text = match.group()

    for old, new in _PUNCT_SUBS:
        text = text.replace(old, new)

    if match_type != "single":
        text = text.replace("'", "&⎋&")

    return text
