#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Generic, Literal, Optional, TypeVar, get_args

# Mode parameter type aliases. The runtime ``*_MODES`` tuples below remain the
# source of truth for validation; these Literal aliases let type checkers catch
# mode typos at call sites without touching any runtime behaviour.
SplitMode = Literal["conservative", "balanced", "aggressive"]
DocType = Optional[Literal["pdf"]]
BufferingMode = Literal["conservative", "balanced", "aggressive"]

# Zero-width / format characters that ``str.isspace()`` / ``str.strip()`` do not
# flag or remove (ZWSP, ZWNJ, ZWJ, BOM). A lone one at a sentence boundary (e.g. a
# Wikipedia U+200B reference marker) otherwise survives as a phantom empty
# sentence or is folded into the next one. Defined once here so the processor and
# segmenter share a single source of truth.
ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\ufeff"


class Rule:
    def __init__(self, pattern: str, replacement: str, flags: int = 0) -> None:
        self.pattern = pattern
        self.replacement = replacement
        self.flags = flags
        self.regex: re.Pattern[str] = re.compile(pattern, flags)

    def __repr__(self) -> str:  # pragma: no cover
        return '<{} pattern="{}" and replacement="{}">'.format(self.__class__.__name__, self.pattern, self.replacement)


# Split-bias modes, ordered from most join-leaning (under-split) to most
# split-leaning (over-split). "balanced" is the default and reproduces the
# library's historically tuned behaviour; "conservative" leans every tunable
# ambiguity toward keeping text joined, "aggressive" toward splitting it.
SPLIT_MODES = get_args(SplitMode)
_SPLIT_MODE_RANK = {mode: rank for rank, mode in enumerate(SPLIT_MODES)}


def split_mode_rank(mode: str) -> int:
    """Return the bias rank of *mode*: 0 = conservative, 1 = balanced, 2 = aggressive.

    Tunable decision points compare against this rank instead of hard-coding a
    single lean, e.g. ``leans_split = split_mode_rank(mode) >= 2``.
    """
    return _SPLIT_MODE_RANK[mode]


def ensure_compiled(pattern: str | re.Pattern[str], flags: int = 0) -> re.Pattern[str]:
    """Return a compiled regex, compiling if *pattern* is a string."""
    if isinstance(pattern, re.Pattern):
        return pattern
    return re.compile(pattern, flags)


def apply_rules(text: str, *rules: Rule) -> str:
    """Apply a series of compiled regex rules to text."""
    for rule in rules:
        text = rule.regex.sub(rule.replacement, text)
    return text


def _next_nonspace_char(text: str, start: int = 0) -> str:
    """Return the first non-whitespace character in *text* at or after *start*, or empty string."""
    if start < 0:
        start = max(len(text) + start, 0)
    for index in range(start, len(text)):
        char = text[index]
        if not char.isspace():
            return char
    return ""


def _is_latin_upper(char: str) -> bool:
    """True for ASCII uppercase or non-ASCII Latin uppercase (e.g. É, Ñ), but not Greek/Cyrillic."""
    if not char or not char.isupper():
        return False
    return char.isascii() or unicodedata.name(char, "").startswith("LATIN")


def _next_nonspace_char_is_upper(text: str, start: int = 0) -> bool:
    char = _next_nonspace_char(text, start)
    return _is_latin_upper(char)


def _next_nonspace_char_is_non_ascii_upper(text: str, start: int = 0) -> bool:
    """True only for non-ASCII *Latin* uppercase (e.g. É, Ñ), not Greek/Cyrillic."""
    char = _next_nonspace_char(text, start)
    return bool(char) and char.isupper() and not char.isascii() and unicodedata.name(char, "").startswith("LATIN")


def _next_nonspace_char_starts_sentence(text: str, start: int = 0) -> bool:
    char = _next_nonspace_char(text, start)
    return _is_latin_upper(char)


@dataclass
class TextSpan:
    """Sentence text and its start & end character offsets within original text."""

    sent: str
    start: int
    end: int


_SegmentT = TypeVar("_SegmentT", str, TextSpan)


@dataclass
class SegmentLookahead(Generic[_SegmentT]):
    """Segmentation result plus a trailing-boundary lookahead verdict.

    Generic over the element type: ``SegmentLookahead[str]`` from
    ``segment_with_lookahead`` and ``SegmentLookahead[TextSpan]`` from
    ``segment_spans_with_lookahead``.
    """

    segments: list[_SegmentT]
    should_wait_for_more: bool
