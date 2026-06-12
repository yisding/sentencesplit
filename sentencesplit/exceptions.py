# -*- coding: utf-8 -*-
"""Package-rooted exception hierarchy for sentencesplit.

All library-raised errors derive from :class:`SentenceSplitError`, so callers
can catch every sentencesplit failure with a single ``except``. The
discriminating subclasses also subclass the matching builtin
(:class:`ValueError`) so that pre-existing ``except ValueError`` callers keep
working unchanged.
"""

from __future__ import annotations


class SentenceSplitError(Exception):
    """Base class for all errors raised by sentencesplit."""


class InvalidConfigurationError(SentenceSplitError, ValueError):
    """Raised for invalid Segmenter/StreamSegmenter configuration."""


class UnknownLanguageError(SentenceSplitError, ValueError):
    """Raised when the requested language code is not available."""
