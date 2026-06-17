# -*- coding: utf-8 -*-
"""Regression: Kazakh MULTI_PERIOD_ABBREVIATION_REGEX is sentinel-aware.

A declared dotless Kazakh multi-period abbreviation ("т.с.с") gets its trailing
period protected to the "∯" sentinel by the per-line PeriodClassifier (when a
REGULAR-branch follower follows) BEFORE ``replace_multi_period_abbreviations``
runs. The pass must still re-find the token to protect its INTERIOR dots, so the
regex separators/terminator accept "∯" as well as ".", mirroring the base
``Common.MULTI_PERIOD_ABBREVIATION_REGEX`` and Kazakh's own
``protect_multi_period_abbreviations_before_parenthesis``. The previous ``[.]``-only
form could only re-find such a token via a lucky shorter-prefix match.
"""

from sentencesplit import Segmenter
from sentencesplit.lang.kazakh import Kazakh


def test_regex_matches_sentinel_protected_token() -> None:
    # The whole token (trailing period already protected to "∯") matches directly.
    assert Kazakh.MULTI_PERIOD_ABBREVIATION_REGEX.match("т.с.с∯") is not None
    # The all-literal form keeps matching too.
    assert Kazakh.MULTI_PERIOD_ABBREVIATION_REGEX.match("т.с.с.") is not None


def test_dotless_multiperiod_interior_dots_protected() -> None:
    # "т.с.с" before a space+paren / space+digit follower must stay one token: every
    # interior period is protected, so no sentence is split inside the abbreviation.
    seg = Segmenter("kk")
    assert seg.segment("Бұл т.с.с. (мысал) еді.") == ["Бұл т.с.с. (мысал) еді."]
    assert seg.segment("Көрсеткіш т.с.с. 5 еді.") == ["Көрсеткіш т.с.с. 5 еді."]
