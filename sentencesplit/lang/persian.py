# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard
from sentencesplit.utils import Rule


class Persian(Common, Standard):
    iso_code = "fa"

    Punctuations = ["?", "!", ":", ".", "؟"]
    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[:\.!\?؟]|.*?\Z|.*?$")

    # Rubular: http://rubular.com/r/RX5HpdDIyv
    ReplaceColonBetweenNumbersRule = Rule(r"(?<=\d):(?=\d)", "♭")

    # Rubular: http://rubular.com/r/kPRgApNHUg
    ReplaceNonSentenceBoundaryCommaRule = Rule(r"،(?=\s\S+،)", "♬")

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

        def __init__(self, text, lang):
            super().__init__(text, lang)

        def scan_for_replacements(self, txt, am, index, character_array, stripped=None, escaped=None):
            txt = re.sub(r"(?<={0})\.".format(am), "∯", txt)
            return txt
