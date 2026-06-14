# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.arabic_script import ArabicScriptProfile


class Arabic(ArabicScriptProfile, Common, Standard):
    iso_code = "ar"

    # NOTE: Unlike pragmatic_segmenter / pySBD, the Arabic comma "،" (U+060C) is
    # deliberately NOT a sentence terminator. It is a within-sentence separator
    # (lists, coordinated clauses); treating it as a boundary fragmented ordinary
    # text — sometimes mid-phrase — and split plain comma lists into pseudo-
    # sentences. We diverge from the upstream Golden Rule in favor of grammatical
    # sentence boundaries, matching Persian (which never treated "،" as one).
    Punctuations = ["?", "!", ":", ".", "؟"]
    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[:\.!\?؟]|.*?\Z|.*?$")

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
            "كج",
            "كلم",
            "م",
            "م.ب",
            "ه",
        ]
        PREPOSITIVE_ABBREVIATIONS = []
        NUMBER_ABBREVIATIONS = []
