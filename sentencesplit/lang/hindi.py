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
