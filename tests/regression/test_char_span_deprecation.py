# -*- coding: utf-8 -*-
"""Regression: the deprecated ``char_span`` flag must warn at runtime.

The ``char_span`` constructor flag is documented as deprecated in favour of
:meth:`Segmenter.segment_spans`, but historically emitted nothing at runtime —
the deprecation lived only in the docstring. These tests pin that
``char_span=True`` raises a :class:`DeprecationWarning`, both via the
:class:`Segmenter` constructor directly and via the :class:`StreamSegmenter`
wrapper that forwards the flag, while ``char_span=False`` stays silent.
"""

from __future__ import annotations

import warnings

import pytest

import sentencesplit
from sentencesplit.stream_segmenter import StreamSegmenter


def test_segmenter_char_span_true_warns():
    with pytest.warns(DeprecationWarning, match="char_span is deprecated"):
        sentencesplit.Segmenter(language="en", char_span=True)


def test_segmenter_char_span_false_is_silent():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        # Must not raise: no DeprecationWarning when the flag is off.
        sentencesplit.Segmenter(language="en", char_span=False)


def test_stream_segmenter_char_span_true_warns():
    with pytest.warns(DeprecationWarning, match="char_span is deprecated"):
        StreamSegmenter(language="en", char_span=True)


def test_stream_segmenter_char_span_false_is_silent():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        StreamSegmenter(language="en", char_span=False)


def test_stream_segmenter_char_span_true_warns_once():
    """The forwarded flag must surface exactly one DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        StreamSegmenter(language="en", char_span=True)
    char_span_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(char_span_warnings) == 1
