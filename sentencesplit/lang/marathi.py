# -*- coding: utf-8 -*-
# Grammer rules from https://gopract.com/Pages/Marathi-Grammar-Viramchinah.aspx
import re

from sentencesplit.lang.common import Common, Standard


class Marathi(Common, Standard):
    iso_code = "mr"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[.!?]|.*?$")
    Punctuations = [".", "!", "?"]
