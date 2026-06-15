# -*- coding: utf-8 -*-
"""Shared segment-normalization helpers.

These functions encode how a plain (non-span) sentence string is normalized at a
boundary: dropping stray zero-width/format characters and locating the terminal
punctuation mark. They are pure (no segmenter state) and parameterized by the
language's ``Punctuations`` set, so both :class:`~sentencesplit.segmenter.Segmenter`
and :class:`~sentencesplit.stream_segmenter.StreamSegmenter` can call them directly
instead of streaming reaching into the other's private methods.
"""

from __future__ import annotations

import re

from sentencesplit.utils import ZERO_WIDTH_CHARS

# Zero-width / format characters that str.isspace() does not flag. A lone one
# (e.g. a Wikipedia U+200B reference marker) at a boundary survives str.strip()
# and is otherwise emitted as a phantom sentence or folded into the next one.
_ZERO_WIDTH_CHARS = frozenset(ZERO_WIDTH_CHARS)
_ZERO_WIDTH_TRANSLATION = {ord(c): None for c in _ZERO_WIDTH_CHARS}
_ZERO_WIDTH_CLASS = re.escape("".join(_ZERO_WIDTH_CHARS))
# Fast presence test so the per-segment closer scan can early-out on the common
# case of text with no zero-width/format characters at all.
_ZERO_WIDTH_SEARCH_RE = re.compile(f"[{_ZERO_WIDTH_CLASS}]")
# Closing quotes/brackets that may trail a sentence-terminal mark.
_TRAILING_SENTENCE_CLOSERS = frozenset("\"')]}»”’）】》」』")


def strip_zero_width(text: str, punctuations=None) -> str:
    """Drop boundary zero-width/format characters from a (plain, non-span) segment.

    Only the leading/trailing run of whitespace-or-zero-width is cleaned, and
    even there whitespace is kept — just the stray zero-width artifact (e.g. a
    lone U+200B Wikipedia reference marker) is removed. Interior zero-width
    joiners are preserved, so emoji sequences (👩‍💻) and scripts that use
    U+200C/U+200D within a word (e.g. Hindi, Persian) are not corrupted.
    """

    def _is_boundary_trim(ch: str) -> bool:
        return ch.isspace() or ch in _ZERO_WIDTH_CHARS

    start, end = 0, len(text)
    while start < end and _is_boundary_trim(text[start]):
        start += 1
    while end > start and _is_boundary_trim(text[end - 1]):
        end -= 1
    lead = text[:start].translate(_ZERO_WIDTH_TRANSLATION)
    trail = text[end:].translate(_ZERO_WIDTH_TRANSLATION)
    core = text[start:end]
    if punctuations:
        core = strip_zero_width_before_sentence_closers(core, punctuations)
    return lead + core + trail


def strip_zero_width_before_sentence_closers(text: str, punctuations) -> str:
    # The only edit this makes is dropping a zero-width run that sits between a
    # sentence terminator and a closing quote/bracket; with no zero-width char
    # present it rebuilds the string unchanged, so skip the char-by-char scan.
    if not _ZERO_WIDTH_SEARCH_RE.search(text):
        return text
    chars = []
    punctuation_set = frozenset(punctuations)
    index = 0
    text_len = len(text)
    while index < text_len:
        char = text[index]
        if char not in _ZERO_WIDTH_CHARS:
            chars.append(char)
            index += 1
            continue

        run_start = index
        while index < text_len and text[index] in _ZERO_WIDTH_CHARS:
            index += 1

        previous_char = chars[-1] if chars else ""
        next_char = text[index] if index < text_len else ""
        if previous_char in punctuation_set and next_char in _TRAILING_SENTENCE_CLOSERS:
            continue
        chars.append(text[run_start:index])
    return "".join(chars)


def terminal_punctuation(text: str, punctuations) -> tuple[int, str] | None:
    """Locate the sentence-terminal punctuation mark at the end of ``text``.

    Skips a trailing run of closing quotes/brackets and zero-width characters,
    then returns ``(index, mark)`` if the next char back is one of the language's
    ``punctuations``; otherwise ``None``.
    """
    idx = len(text) - 1
    while idx >= 0 and (text[idx] in _TRAILING_SENTENCE_CLOSERS or text[idx] in _ZERO_WIDTH_CHARS):
        idx -= 1
    if idx < 0:
        return None
    punct = text[idx]
    if punct not in punctuations:
        return None
    return idx, punct
