# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Hindi(Common, Standard):
    iso_code = "hi"

    # The danda (।) is the standard Hindi sentence terminator. "." is intentionally
    # excluded from both the boundary regex and Punctuations so Latin abbreviations
    # and decimals in mixed Hindi/English text are not over-split. (Previously "."
    # was listed in Punctuations but absent from SENTENCE_BOUNDARY_REGEX, so it
    # could never produce a boundary anyway — this just makes the two consistent.)
    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[।\|!\?]|.*?$")
    Punctuations = ["।", "|", "!", "?"]

    class AbbreviationReplacer(Standard.AbbreviationReplacer):
        # Hindi overrides zero scan methods and uses no elision, so it rides the
        # base PeriodClassifier (BASE_POLICY) directly — identical shape to Dutch.
        # It inherits Standard.Abbreviation (the English-derived lists), and is NOT
        # one of the CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE languages, so that flag
        # stays off and capital followers flow through the split-mode ambiguity dial,
        # matching the legacy per-line protection on Hindi text.
        USE_PERIOD_CLASSIFIER = True
