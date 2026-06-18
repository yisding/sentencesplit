# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Burmese(Common, Standard):
    iso_code = "my"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[။၏!\?]|.*?$")
    Punctuations = ["။", "၏", "?", "!"]

    # Burmese overrides zero scan methods and uses no elision, so it rides the
    # base PeriodClassifier (BASE_POLICY) inherited from Standard directly —
    # identical shape to Amharic. It inherits Standard.Abbreviation (the
    # English-derived lists) and the Burmese script is unicameral (no letter
    # case), so it is NOT one of the CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE
    # languages; that flag stays off and capital (Latin) followers flow through
    # the split-mode ambiguity dial. Burmese terminates sentences with native
    # punctuation (။ pote ma, ၏ wa, plus ! ?), so the Latin "." is never a
    # terminator; the classifier just protects abbreviation periods (e.g.
    # embedded "Dr.", "U.S.").
