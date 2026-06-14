# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Armenian(Common, Standard):
    iso_code = "hy"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[։՜:]|.*?$")
    Punctuations = ["։", "՜", ":"]

    # Armenian overrides zero scan methods and uses no elision, so it rides the
    # base PeriodClassifier (BASE_POLICY) inherited from Standard directly —
    # identical shape to Hindi/Marathi/Tagalog. It inherits Standard.Abbreviation
    # (the English-derived lists), and is NOT one of the
    # CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE languages, so that flag stays off and
    # capital followers flow through the split-mode ambiguity dial. Armenian
    # terminates sentences with native punctuation (։ verjaket, ՜ batsaganchakan,
    # : as full stop), so the Latin "." is never a terminator anyway; the
    # classifier just protects abbreviation periods.
