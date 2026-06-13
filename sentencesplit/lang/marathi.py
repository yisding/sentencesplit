# -*- coding: utf-8 -*-
# Grammer rules from https://gopract.com/Pages/Marathi-Grammar-Viramchinah.aspx
import re

from sentencesplit.lang.common import Common, Standard


class Marathi(Common, Standard):
    iso_code = "mr"

    # Marathi is written in Devanagari and ends sentences with the danda ("।",
    # U+0964) / double danda ("॥", U+0965), like Hindi. Modern Marathi also uses
    # the Latin ".", "!" and "?", so all are accepted as terminators.
    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[।॥.!?]|.*?$")
    Punctuations = ["।", "॥", ".", "!", "?"]
