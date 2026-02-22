# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class Urdu(Common, Standard):
    iso_code = "ur"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[۔؟!\?]|.*?$")
    Punctuations = ["?", "!", "۔", "؟"]

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []
