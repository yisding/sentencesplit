# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.arabic_script import ArabicScriptProfile


class Arabic(ArabicScriptProfile, Common, Standard):
    iso_code = "ar"

    Punctuations = ["?", "!", ":", ".", "؟", "،"]
    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[:\.!\?؟،]|.*?\Z|.*?$")

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = [
            "ا",
            "ا. د",
            "ا.د",
            "ا.ش.ا",
            "إلخ",
            "ت.ب",
            "ج.ب",
            "جم",
            "ج.م.ع",
            "س.ت",
            "سم",
            "ص.ب.",
            "ص.ب",
            "كج.",
            "كلم.",
            "م",
            "م.ب",
            "ه",
        ]
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = []
