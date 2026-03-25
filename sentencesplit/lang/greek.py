# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class Greek(Common, Standard):
    iso_code = "el"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[\.;!\?]|.*?$")
    Punctuations = [".", "!", ";", "?"]

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []
