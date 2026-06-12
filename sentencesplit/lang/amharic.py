# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Amharic(Common, Standard):
    iso_code = "am"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[፧።!\?]|.*?$")
    Punctuations = ["።", "፧", "?", "!"]
