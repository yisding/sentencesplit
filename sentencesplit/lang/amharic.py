# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class Amharic(Common, Standard):
    iso_code = "am"

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[፧።!\?]|.*?$")
    Punctuations = ["።", "፧", "?", "!"]
