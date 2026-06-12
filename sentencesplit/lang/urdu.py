# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Urdu(Common, Standard):
    iso_code = "ur"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[۔؟!\?]|.*?$")
    Punctuations = ["?", "!", "۔", "؟"]
