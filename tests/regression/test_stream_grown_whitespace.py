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


def test_trailing_whitespace_after_last_sentence_is_not_lost():
    out = _drain_incrementally(["Done.", "  "], language="en")
    assert "".join(out) == "Done.  "
