# -*- coding: utf-8 -*-
# Grammer rules from https://gopract.com/Pages/Marathi-Grammar-Viramchinah.aspx
import re

from sentencesplit.lang.common import Common, Standard


class Marathi(Common, Standard):
    iso_code = "mr"

    # Marathi is written in Devanagari and ends sentences with the danda ("।",
    # U+0964) / double danda ("॥", U+0965), like Hindi. Modern Marathi also uses
    # the Latin ".", "!" and "?", so all are accepted as terminators.
    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[।॥.!?]|.*?$")
    Punctuations = ["।", "॥", ".", "!", "?"]

    class AbbreviationReplacer(Standard.AbbreviationReplacer):
        # Marathi overrides zero scan methods and uses no elision, so it rides the
        # base PeriodClassifier (BASE_POLICY) directly — identical shape to Hindi.
        # It inherits Standard.Abbreviation (the English-derived lists), and is NOT
        # one of the CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE languages, so that flag
        # stays off and capital followers flow through the split-mode ambiguity dial,
        # matching the legacy per-line protection on Marathi text.
        USE_PERIOD_CLASSIFIER = True
