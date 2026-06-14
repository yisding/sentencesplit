# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Amharic(Common, Standard):
    iso_code = "am"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[፧።!\?]|.*?$")
    Punctuations = ["።", "፧", "?", "!"]

    # Amharic overrides zero scan methods and uses no elision, so it rides the
    # base PeriodClassifier (BASE_POLICY) inherited from Standard directly —
    # identical shape to Armenian/Hindi/Marathi/Tagalog. It inherits
    # Standard.Abbreviation (the English-derived lists) and is NOT one of the
    # CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE languages, so that flag stays off and
    # capital followers flow through the split-mode ambiguity dial. Amharic
    # terminates sentences with native punctuation (። arat netela, ፧ netela
    # tibeb, plus ! ?), so the Latin "." is never a terminator; the classifier
    # just protects abbreviation periods (e.g. embedded "Dr.", "U.S.").
