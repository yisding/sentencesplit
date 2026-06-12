# -*- coding: utf-8 -*-
from sentencesplit.lang.common import Common, Standard


class English(Common, Standard):
    iso_code = "en"

    class AbbreviationReplacer(Standard.AbbreviationReplacer):
        CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE = True
        PROTECT_ALLCAPS_IMPRINT_SUFFIXES = True
