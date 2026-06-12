# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Armenian(Common, Standard):
    iso_code = "hy"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[։՜:]|.*?$")
    Punctuations = ["։", "՜", ":"]
