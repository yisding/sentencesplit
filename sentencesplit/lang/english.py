# -*- coding: utf-8 -*-
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class English(Common, Standard):
    iso_code = "en"

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = (
            "A Being Did For He How However I In It Millions More She That The There They We What When Where Who Why".split(
                " "
            )
        )
