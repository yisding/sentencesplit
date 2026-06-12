"""Regression tests for the package-rooted exception hierarchy.

The library raises a small hierarchy rooted at ``SentenceSplitError`` while
still subclassing the matching builtin (``ValueError``), so existing callers
that catch ``ValueError`` keep working. The unknown-language re-raise also
chains the underlying ``KeyError`` via ``raise ... from``.
"""

import pytest

from sentencesplit import Segmenter, SentenceSplitError
from sentencesplit.exceptions import InvalidConfigurationError, UnknownLanguageError


def test_misconfigured_segmenter_is_value_error_and_base_error():
    with pytest.raises(SentenceSplitError) as exc_info:
        Segmenter(split_mode="bogus")
    err = exc_info.value
    assert isinstance(err, ValueError)
    assert isinstance(err, SentenceSplitError)
    assert isinstance(err, InvalidConfigurationError)


def test_misconfigured_segmenter_catchable_as_value_error():
    with pytest.raises(ValueError):
        Segmenter(split_mode="bogus")


def test_unknown_language_raises_unknown_language_error():
    with pytest.raises(UnknownLanguageError) as exc_info:
        Segmenter(language="zz")
    err = exc_info.value
    assert isinstance(err, ValueError)
    assert isinstance(err, SentenceSplitError)
    assert isinstance(err.__cause__, KeyError)


def test_unknown_language_catchable_as_value_error_and_base():
    with pytest.raises(ValueError):
        Segmenter(language="zz")
    with pytest.raises(SentenceSplitError):
        Segmenter(language="zz")
