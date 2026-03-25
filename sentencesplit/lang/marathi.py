# -*- coding: utf-8 -*-
# Grammer rules from https://gopract.com/Pages/Marathi-Grammar-Viramchinah.aspx
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class Marathi(Common, Standard):
    iso_code = "mr"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[.!?]|.*?$")
    Punctuations = [".", "!", "?"]

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []
