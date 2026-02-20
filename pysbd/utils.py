#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Pattern


class Rule:
    def __init__(self, pattern: str, replacement: str, flags: int = 0) -> None:
        self.pattern = pattern
        self.replacement = replacement
        self.flags = flags
        self.regex: Pattern[str] = re.compile(pattern, flags)

    def __repr__(self) -> str:  # pragma: no cover
        return '<{} pattern="{}" and replacement="{}">'.format(self.__class__.__name__, self.pattern, self.replacement)


def apply_rules(text: str, *rules: Rule) -> str:
    """Apply a series of compiled regex rules to text."""
    for rule in rules:
        text = rule.regex.sub(rule.replacement, text)
    return text


class TextSpan:
    def __init__(self, sent: str, start: int, end: int) -> None:
        """
        Sentence text and its start & end character offsets within original text

        Parameters
        ----------
        sent : str
            Sentence text
        start : int
            start character offset of a sentence in original text
        end : int
            end character offset of a sentence in original text
        """
        self.sent = sent
        self.start = start
        self.end = end

    def __repr__(self) -> str:  # pragma: no cover
        return "{0}(sent={1}, start={2}, end={3})".format(self.__class__.__name__, repr(self.sent), self.start, self.end)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.sent == other.sent and self.start == other.start and self.end == other.end
        return False
