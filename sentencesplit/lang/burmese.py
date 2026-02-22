# -*- coding: utf-8 -*-
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class Burmese(Common, Standard):
    iso_code = "my"

    SENTENCE_BOUNDARY_REGEX = r".*?[။၏!\?]|.*?$"
    Punctuations = ["။", "၏", "?", "!"]

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []
