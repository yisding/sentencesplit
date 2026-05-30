# -*- coding: utf-8 -*-
from sentencesplit.lang.common import Common, Standard


class English(Common, Standard):
    iso_code = "en"

    # English uses Standard.AbbreviationReplacer unchanged (same SENTENCE_STARTERS),
    # so no nested override is needed. en_legal / en_es_zh that reference
    # English.AbbreviationReplacer.SENTENCE_STARTERS resolve it via the MRO.
