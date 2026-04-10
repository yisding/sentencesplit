#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


class Rule:
    def __init__(self, pattern: str, replacement: str, flags: int = 0) -> None:
        self.pattern = pattern
        self.replacement = replacement
        self.flags = flags
        self.regex: re.Pattern[str] = re.compile(pattern, flags)

    def __repr__(self) -> str:  # pragma: no cover
        return '<{} pattern="{}" and replacement="{}">'.format(self.__class__.__name__, self.pattern, self.replacement)


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


_CJK_SENTENCE_START_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff]")


def _next_nonspace_char(text: str, start: int = 0) -> str:
    """Return the first non-whitespace character in *text* at or after *start*, or empty string."""
    for char in text[start:]:
        if not char.isspace():
            return char
    return ""


def _next_nonspace_char_is_upper(text: str, start: int = 0) -> bool:
    char = _next_nonspace_char(text, start)
    return bool(char) and char.isupper()


def _next_nonspace_char_is_non_ascii_upper(text: str, start: int = 0) -> bool:
    """True only for non-ASCII *Latin* uppercase (e.g. É, Ñ), not Greek/Cyrillic."""
    char = _next_nonspace_char(text, start)
    return bool(char) and char.isupper() and not char.isascii() and unicodedata.name(char, "").startswith("LATIN")


def _next_nonspace_char_starts_sentence(text: str, start: int = 0) -> bool:
    char = _next_nonspace_char(text, start)
    return bool(char) and (char.isupper() or bool(_CJK_SENTENCE_START_RE.match(char)))


@dataclass
class TextSpan:
    """Sentence text and its start & end character offsets within original text."""

    sent: str
    start: int
    end: int


@dataclass
class SegmentLookahead:
    segments: list[str] | list[TextSpan]
    should_wait_for_more: bool
