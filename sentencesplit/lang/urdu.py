# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Urdu(Common, Standard):
    # Urdu intentionally does NOT mix in ArabicScriptProfile (unlike Arabic and
    # Persian). That profile only protects ":" (colon between digits), "،" (the
    # Arabic comma inside lists) and a literal "." inside abbreviations — none of
    # which are sentence-boundary characters for Urdu, whose terminators are the
    # danda "۔", "؟", "?" and "!". The mixin would therefore be inert here. If
    # ":", "،" or "." are ever added to Punctuations below, revisit this.
    iso_code = "ur"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[۔؟!\?]|.*?$")
    Punctuations = ["?", "!", "۔", "؟"]
