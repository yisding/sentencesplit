# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Hindi(Common, Standard):
    iso_code = "hi"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[।\|!\?]|.*?$")
    Punctuations = ["।", "|", ".", "!", "?"]
