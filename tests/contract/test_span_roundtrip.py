"""Span-faithful round-trip contract for ``segment_spans()`` (N5).

``segment_spans()`` is the canonical, lossless spans API: every emitted span
must be an exact ``[start, end)`` slice of the source, and reassembling all
spans must reproduce the source verbatim. These invariants are enforced both
with explicit dirty-input fixtures and with Hypothesis property tests across
every registered language.

Hypothesis is a DEV-ONLY dependency (declared in the ``dev`` dependency group).
The zero-dependency core must never import it; that promise is guarded by
``tests/test_zero_dependencies.py``.

Design call (RTL / directional-format characters): the canonical
``segment_spans()`` path is byte-for-byte exact and strips
nothing, so directional-format characters (RTL override U+202E, LRM/RLM, …) are
preserved there with full fidelity. The *plain* ``segment()`` path is
deliberately lossy at boundaries: it strips only the zero-width set
(``_ZERO_WIDTH_CHARS`` = ZWSP/ZWNJ/ZWJ/BOM) so a lone reference marker is not
emitted as a phantom sentence. We intentionally do **not** extend that stripping
to RTL/directional-format characters — they carry rendering semantics and are
not invisible artifacts, and callers that need exactness use ``segment_spans()``.
``test_plain_segment_does_not_strip_directional_format_chars`` locks that call.
"""

from __future__ import annotations

import pytest

import sentencesplit
from sentencesplit.utils import TextSpan
from tests.helpers import (
    ALL_CODES,
    BOM,
    COMBINING_ACUTE,
    DIRTY_CHARS,
    LRM,
    NBSP,
    RLM,
    RTL_OVERRIDE,
    ZWJ,
    ZWNJ,
    ZWSP,
    assert_span_contract,
)
from tests.helpers import text_strategy as _text_strategy

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
except ImportError:  # pragma: no cover - dev-only dependency
    pytest.skip("hypothesis is a dev-only dependency", allow_module_level=True)

# Dirty-character constants, ``ALL_CODES``, and the per-language
# ``_text_strategy`` are promoted into ``tests/helpers.py`` and imported above
# so both the span round-trip contract and the core ``segment()`` property
# tests share one source.


# --------------------------------------------------------------------------- #
# 1. Property-based round-trip across every registered language.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", ALL_CODES)
@settings(max_examples=150, deadline=None)
@given(data=st.data())
def test_segment_spans_roundtrip_property(code, data):
    text = data.draw(_text_strategy(code))
    seg = sentencesplit.Segmenter(language=code, clean=False)
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)


@settings(max_examples=400, deadline=None)
@given(text=st.text(max_size=80))
def test_segment_spans_roundtrip_arbitrary_unicode(text):
    """Unconstrained Unicode (any code point) must still round-trip exactly."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)


@settings(max_examples=300, deadline=None)
@given(text=st.text(alphabet=list("Hello world.!? \n\t") + DIRTY_CHARS, max_size=60))
def test_segment_str_is_prefix_projection_of_spans(text):
    """``segment()`` (plain strings) is the zero-width-stripped, non-empty
    projection of the canonical ``segment_spans()`` output."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)
    assert all(isinstance(s, str) for s in seg.segment(text))


# --------------------------------------------------------------------------- #
# 2. Explicit dirty-input fixtures (non-generated, human-auditable).
# --------------------------------------------------------------------------- #
_DIRTY_FIXTURES = [
    pytest.param("Hello." + ZWSP + " World.", id="zwsp-at-boundary"),
    pytest.param("Hello." + ZWSP + "World.", id="zwsp-interior"),
    pytest.param("Hello." + NBSP + "World.", id="nbsp"),
    pytest.param(BOM + "Hello. World.", id="bom-leading"),
    pytest.param("Hello. World." + BOM, id="bom-trailing"),
    pytest.param("a" + COMBINING_ACUTE + " cat. A dog.", id="combining-mark-letter"),
    pytest.param("Wait." + COMBINING_ACUTE + " Go.", id="combining-mark-on-punct"),
    pytest.param("Hello." + RTL_OVERRIDE + " World.", id="rtl-override"),
    pytest.param(RTL_OVERRIDE + "Hello. World.", id="rtl-override-leading"),
    pytest.param("Hello." + LRM + RLM + " World.", id="lrm-rlm"),
    pytest.param("a." + ZWNJ + "b. c.", id="zwnj-interior"),
    pytest.param("Hi." + ZWJ + " Bye.", id="zwj-at-boundary"),
    pytest.param(ZWSP + ZWSP + ZWSP, id="zwsp-only-sequence"),
    pytest.param("   ", id="whitespace-only"),
    pytest.param("\n\n", id="newlines-only"),
    pytest.param(NBSP + ZWSP + BOM, id="dirty-only-mix"),
    pytest.param("", id="empty"),
    pytest.param("One sentence only", id="single-no-terminal"),
    pytest.param("One. Two. Three.", id="multi-sentence"),
    pytest.param("  Leading.  Trailing.  ", id="leading-trailing-ws"),
]


@pytest.mark.parametrize("text", _DIRTY_FIXTURES)
def test_segment_spans_dirty_input_contract(text):
    seg = sentencesplit.Segmenter(language="en", clean=False)
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)


@pytest.mark.parametrize("text", _DIRTY_FIXTURES)
@pytest.mark.parametrize("code", ["en", "zh", "ja", "ar", "hi", "en_es_zh"])
def test_segment_spans_dirty_input_contract_multilang(code, text):
    seg = sentencesplit.Segmenter(language=code, clean=False)
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)


# --------------------------------------------------------------------------- #
# 3. segment() vs segment_spans() consistency.
# --------------------------------------------------------------------------- #
def test_plain_segment_str_roundtrip_for_clean_text():
    """For text without boundary zero-width artifacts, plain ``segment()`` is
    also lossless: ``"".join(segment(text)) == text``."""
    text = "  Hello.  World.  "
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = seg.segment(text)
    assert all(isinstance(s, str) for s in segments)
    assert "".join(segments) == text
    # And it agrees with the canonical spans API.
    spans = seg.segment_spans(text)
    assert "".join(span.sent for span in spans) == text


def test_segment_spans_returns_textspans():
    text = "My name is Jonas E. Smith. Please turn to p. 55."
    seg = sentencesplit.Segmenter(language="en", clean=False)
    canonical = seg.segment_spans(text)
    assert all(isinstance(s, TextSpan) for s in canonical)
    assert "".join(s.sent for s in canonical) == text


def test_plain_segment_does_not_strip_directional_format_chars():
    """Design call: RTL/directional-format chars are NOT in the zero-width strip
    set, so they survive even on the lossy plain ``segment()`` path."""
    text = "Hello." + RTL_OVERRIDE + " World."
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = seg.segment(text)
    assert "".join(segments) == text
    assert any(RTL_OVERRIDE in s for s in segments)


def test_plain_segment_strips_zero_width_only_segment():
    """Conversely, a lone zero-width artifact IS dropped on the plain path (no
    phantom sentence), while segment_spans() keeps it byte-for-byte."""
    text = ZWSP
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert seg.segment(text) == []
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)
    assert spans == [TextSpan(ZWSP, 0, 1)]


# --------------------------------------------------------------------------- #
# 4. Whitespace-only round-trip across languages (the latent _match_spans bug).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", ALL_CODES)
@pytest.mark.parametrize("text", ["\n", "   ", "\t", NBSP, ZWSP, NBSP + ZWSP + "  "])
def test_segment_spans_whitespace_only_roundtrips(code, text):
    seg = sentencesplit.Segmenter(language=code, clean=False)
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)


# --------------------------------------------------------------------------- #
# 5. Empty / None handling stays correct.
# --------------------------------------------------------------------------- #
def test_segment_spans_empty_and_none():
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert seg.segment_spans("") == []
    assert seg.segment_spans(None) == []
