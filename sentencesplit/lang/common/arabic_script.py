# -*- coding: utf-8 -*-
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.period_classifier import AR_POLICY
from sentencesplit.utils import Rule


class ArabicScriptProfile:
    """Shared hooks for Arabic-script languages (Arabic, Persian).

    Mixed in before ``Common, Standard`` so it provides the colon boundary rule
    (protecting ``10:30``-style times) and an abbreviation replacer that protects
    the period after a matched abbreviation. Languages still set their own
    ``Punctuations`` and ``SENTENCE_BOUNDARY_REGEX``. Neither language treats the
    Arabic comma ``،`` as a sentence terminator, so no comma rule is needed.
    """

    # Rubular: http://rubular.com/r/RX5HpdDIyv
    ReplaceColonBetweenNumbersRule = Rule(r"(?<=\d):(?=\d)", "♭")

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2 single-pass classifier (Phase 5). ``AR_POLICY`` reproduces the legacy
        # bare-period protect (any follower) as an ``AbbrPolicy`` hook: the matched
        # abbreviation occurs at a word boundary and its period is always
        # non-terminal (Arabic script has no letter case, so no capital-follower
        # cue). The pre-escaped abbreviation in the classifier's lookbehind keeps a
        # dotted form like "e.g" from wildcard-matching an unrelated "egg."
        # (tests/regression/test_arabic_script_abbreviation_metachar.py).
        ABBR_POLICY = AR_POLICY
