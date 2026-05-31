# -*- coding: utf-8 -*-
"""Regression: StreamSegmenter must not emit standalone inter-sentence whitespace.

Reported on PR #36 (Codex P1 + charliecreates blocking): when a consumer drains
after a chunk that ends exactly on a sentence boundary, the trailing space that
arrives in the *next* chunk was emitted as its own ``" "`` item, and the first
sentence lost its trailing space — e.g. ``feed("Hello.")`` drain, ``feed(" World.")``
yielded ``["Hello.", " ", "World."]``.

Fix (option A): whitespace that grows onto an already-emitted sentence is carried
and prepended to the *next* emitted sentence, so consumers only ever receive
real, non-empty sentences while the byte stream is preserved exactly.
"""

from __future__ import annotations

import pytest

from sentencesplit import Segmenter, StreamSegmenter


def _drain_incrementally(chunks, **kwargs):
    """Feed each chunk and drain completed sentences after every feed."""
    ss = StreamSegmenter(**kwargs)
    out: list = []
    for chunk in chunks:
        ss.feed(chunk)
        out.extend(ss.get_completed_sentences())
    out.extend(ss.flush())
    return out


@pytest.mark.parametrize("mode", ["conservative", "balanced", "aggressive"])
def test_no_standalone_whitespace_emitted_on_drain(mode):
    out = _drain_incrementally(["Hello.", " World."], language="en", buffering_mode=mode)
    # No emitted item is whitespace-only / empty.
    assert all(s.strip() for s in out), out
    # Byte stream preserved exactly.
    assert "".join(out) == "Hello. World."
    # The inter-sentence space rides on the following sentence (option A).
    assert out == ["Hello.", " World."]


def test_first_sentence_keeps_its_text_no_orphan_space():
    out = _drain_incrementally(["The cat sat.", " The dog ran."], language="en")
    assert all(s.strip() for s in out)
    assert "".join(out) == "The cat sat. The dog ran."


def test_char_by_char_drain_preserves_bytes_and_granularity():
    text = "One. Two. Three."
    out = _drain_incrementally(list(text), language="en")
    assert "".join(out) == text
    assert all(s.strip() for s in out), out


def test_char_span_drain_spans_are_byte_faithful_and_non_overlapping():
    text = "Hello. World."
    ss = StreamSegmenter(language="en", char_span=True)
    spans: list = []
    for ch in text:
        ss.feed(ch)
        spans.extend(ss.get_completed_sentences())
    spans.extend(ss.flush())
    # Each span slices to its own text; spans tile without overlap or gaps.
    assert all(text[s.start : s.end] == s.sent for s in spans), spans
    assert [(s.start, s.end) for s in spans] == sorted((s.start, s.end) for s in spans)
    for a, b in zip(spans, spans[1:]):
        assert a.end <= b.start
    assert "".join(s.sent for s in spans) == text


def test_feed_full_then_flush_still_matches_non_streaming():
    # The documented feed(full)+flush contract is unchanged by the fix.
    text = "Hello. World."
    ss = StreamSegmenter(language="en")
    ss.feed(text)
    out = ss.get_completed_sentences() + ss.flush()
    assert out == Segmenter(language="en").segment(text)


def test_plain_trailing_whitespace_after_drain_is_not_a_fragment():
    # The sentence was drained before its trailing spaces arrived; plain mode
    # drops the standalone trailing whitespace rather than emitting a " "
    # fragment (plain output is not byte-faithful — it also strips zero-width).
    out = _drain_incrementally(["Done.", "  "], language="en")
    assert out == ["Done."]
    assert all(s.strip() for s in out)


def test_char_span_trailing_whitespace_is_preserved_byte_faithfully():
    # char_span IS byte-faithful: the trailing whitespace is preserved (as a
    # TextSpan), unlike plain mode which drops it.
    from sentencesplit.utils import TextSpan

    ss = StreamSegmenter(language="en", char_span=True)
    out: list = []
    ss.feed("Done.")
    out.extend(ss.get_completed_sentences())
    ss.feed("  ")
    out.extend(ss.get_completed_sentences())
    out.extend(ss.flush())
    assert all(isinstance(x, TextSpan) for x in out)
    assert "".join(x.sent for x in out) == "Done.  "


def test_char_span_flush_trailing_whitespace_stays_textspan():
    """char_span=True must never surface a bare str — even trailing carried
    whitespace at flush() must come back as a TextSpan (PR #36 follow-up)."""
    from sentencesplit.utils import TextSpan

    text = "Done.  "
    ss = StreamSegmenter(language="en", char_span=True)
    out: list = []
    ss.feed("Done.")
    out.extend(ss.get_completed_sentences())
    ss.feed("  ")
    out.extend(ss.get_completed_sentences())
    out.extend(ss.flush())
    assert out, "expected at least one emission"
    assert all(isinstance(x, TextSpan) for x in out), [type(x).__name__ for x in out]
    assert "".join(x.sent for x in out) == text
    for x in out:
        assert text[x.start : x.end] == x.sent


_DIRTY_INPUTS = [
    "A.​ B.",  # zero-width space between sentences
    "One.​ Two.​ Three.",
    "X.﻿ Y.",  # BOM
    "P. Q.",  # NBSP
    "Plain text. No tricks here. Done.",
]


@pytest.mark.parametrize("text", _DIRTY_INPUTS)
def test_plain_no_offset_drift_on_zero_width(text):
    """Plain-mode normalization must not drift offsets (PR #36 follow-up): a
    zero-width char shortens the normalized segment vs the raw buffer, which used
    to mis-slice the next sentence (feed('A.\\u200b B.') -> ['A. ', ' B.'])."""
    ref = Segmenter(language="en").segment(text)
    # Fed whole, streaming plain output matches non-streaming exactly.
    assert _drain_incrementally([text], language="en") == ref
    # Fed char-by-char: no orphan/empty items, and content matches segment()
    # (inter-sentence whitespace may ride the next sentence per option A).
    by_char = _drain_incrementally(list(text), language="en")
    assert all(s.strip() for s in by_char), by_char
    assert "".join(by_char).split() == "".join(ref).split()


@pytest.mark.parametrize("text", _DIRTY_INPUTS)
def test_char_span_byte_faithful_char_by_char_on_dirty_input(text):
    """char_span streaming stays byte-faithful char-by-char even on dirty input:
    every span slices to its own text and reassembly reproduces the source."""
    from sentencesplit.utils import TextSpan

    ss = StreamSegmenter(language="en", char_span=True)
    spans: list = []
    for ch in text:
        ss.feed(ch)
        spans.extend(ss.get_completed_sentences())
    spans.extend(ss.flush())
    assert all(isinstance(s, TextSpan) for s in spans)
    assert all(text[s.start : s.end] == s.sent for s in spans), spans
    assert "".join(s.sent for s in spans) == text
    for a, b in zip(spans, spans[1:]):
        assert a.end <= b.start


def test_char_span_overflow_trailing_whitespace_stays_textspan():
    """The shared end-of-stream whitespace path (max_buffer_size overflow) must
    also honour the span contract."""
    from sentencesplit.utils import TextSpan

    ss = StreamSegmenter(language="en", char_span=True, max_buffer_size=4)
    collected: list = []
    for ch in "Hi.   ":  # terminal then a long whitespace tail that overflows
        out = ss.feed(ch)
        if out:
            collected.extend(out)
        collected.extend(ss.get_completed_sentences())
    collected.extend(ss.flush())
    assert all(isinstance(x, TextSpan) for x in collected), [type(x).__name__ for x in collected]
