# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Burmese(Common, Standard):
    iso_code = "my"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[။၏!\?]|.*?$")
    Punctuations = ["။", "၏", "?", "!"]
