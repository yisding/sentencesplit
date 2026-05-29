# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.arabic_script import ArabicScriptProfile


class Persian(ArabicScriptProfile, Common, Standard):
    iso_code = "fa"

    Punctuations = ["?", "!", ":", ".", "؟"]
    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[:\.!\?؟]|.*?\Z|.*?$")
