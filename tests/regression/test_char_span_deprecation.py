# -*- coding: utf-8 -*-
"""Regression: the deprecated ``char_span`` flag must warn at runtime.

The ``char_span`` constructor flag is soft-deprecated in favour of
:meth:`Segmenter.segment_spans` (the canonical spans API). It is retained
indefinitely as a convenience alias — no removal is planned — and emits a
*one-time* :class:`DeprecationWarning` on first use per process (a gentle nudge,
not per-construction noise). These tests pin that ``char_span=True`` warns (via
both the :class:`Segmenter` constructor and the :class:`StreamSegmenter` wrapper
that forwards the flag), that ``char_span=False`` stays silent, and that the
warning fires only once per process.
"""

from __future__ import annotations

import warnings

import pytest

import sentencesplit
from sentencesplit import segmenter as _segmenter_mod
from sentencesplit.stream_segmenter import StreamSegmenter


@pytest.fixture(autouse=True)
def _reset_char_span_warning_guard():
    """Reset the once-per-process guard so each test observes a fresh warning."""
    _segmenter_mod._CHAR_SPAN_DEPRECATION_WARNED = False
    yield
    _segmenter_mod._CHAR_SPAN_DEPRECATION_WARNED = False


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


def test_char_span_warns_exactly_once_per_construction():
    """A single char_span=True construction surfaces exactly one warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sentencesplit.Segmenter(language="en", char_span=True)
    char_span_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(char_span_warnings) == 1


def test_char_span_warns_only_once_per_process():
    """Subsequent char_span=True constructions stay silent (one-time nudge)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sentencesplit.Segmenter(language="en", char_span=True)  # first: warns
        sentencesplit.Segmenter(language="en", char_span=True)  # second: silent
        StreamSegmenter(language="en", char_span=True)  # also silent (forwards)
    char_span_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(char_span_warnings) == 1
