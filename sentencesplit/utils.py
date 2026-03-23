#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass


class Rule:
    def __init__(self, pattern: str, replacement: str, flags: int = 0) -> None:
        self.pattern = pattern
        self.replacement = replacement
        self.flags = flags
        self.regex: re.Pattern[str] = re.compile(pattern, flags)

    def __repr__(self) -> str:  # pragma: no cover
        return '<{} pattern="{}" and replacement="{}">'.format(self.__class__.__name__, self.pattern, self.replacement)


def apply_rules(text: str, *rules: Rule) -> str:
    """Apply a series of compiled regex rules to text."""
    for rule in rules:
        text = rule.regex.sub(rule.replacement, text)
    return text


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
