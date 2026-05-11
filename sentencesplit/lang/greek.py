# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Greek(Common, Standard):
    iso_code = "el"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[\.;!\?]|.*?$")
    Punctuations = [".", "!", ";", "?"]
