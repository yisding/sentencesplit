# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.utils import Rule


class ArabicScriptProfile:
    """Shared hooks for Arabic-script languages (Arabic, Persian).

    Mixed in before ``Common, Standard`` so it provides the colon/comma boundary
    rules and an abbreviation replacer that protects the period after a matched
    abbreviation. Languages still set their own ``Punctuations`` and
    ``SENTENCE_BOUNDARY_REGEX`` (which differ, e.g. Arabic includes the comma ،).
    """

    # Rubular: http://rubular.com/r/RX5HpdDIyv
    ReplaceColonBetweenNumbersRule = Rule(r"(?<=\d):(?=\d)", "♭")

    # Rubular: http://rubular.com/r/kPRgApNHUg
    ReplaceNonSentenceBoundaryCommaRule = Rule(r"،(?=\s\S+،)", "♬")

    class AbbreviationReplacer(AbbreviationReplacer):
        def scan_for_replacements(self, txt, am, index, character_array, stripped=None, escaped=None):
            # ``am`` is the matched abbreviation occurrence (with its leading
            # boundary char). It must be escaped before being spliced into the
            # lookbehind: abbreviations such as "e.g"/"i.e"/"ا.د" contain a literal
            # ".", which would otherwise act as a regex wildcard and protect the
            # period after unrelated words (e.g. "egg." after seeing "e.g").
            return re.sub(r"(?<={0})\.".format(re.escape(am)), "∯", txt)
