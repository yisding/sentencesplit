# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Urdu(Common, Standard):
    # Urdu intentionally does NOT mix in ArabicScriptProfile (unlike Arabic and
    # Persian). That profile only protects ":" (colon between digits), "،" (the
    # Arabic comma inside lists) and a literal "." inside abbreviations — none of
    # which are sentence-boundary characters for Urdu, whose terminators are the
    # danda "۔", "؟", "?" and "!". The mixin would therefore be inert here. If
    # ":", "،" or "." are ever added to Punctuations below, revisit this.
    iso_code = "ur"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[۔؟!\?]|.*?$")
    Punctuations = ["?", "!", "۔", "؟"]

    class AbbreviationReplacer(Standard.AbbreviationReplacer):
        # Urdu overrides zero scan methods and uses no elision (it inherits
        # Standard.Abbreviation with ELISION_CHARACTERS == ""), so it rides the
        # base PeriodClassifier (BASE_POLICY) directly — identical shape to
        # Burmese/Amharic. It inherits Standard.Abbreviation (the English-derived
        # lists) and the Arabic script Urdu uses is unicameral (no letter case),
        # so it is NOT one of the CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE languages;
        # that flag stays off and capital (Latin) followers flow through the
        # split-mode ambiguity dial, matching the legacy per-line protection on
        # Urdu text. Urdu terminates sentences with the danda "۔", "؟", plus the
        # ASCII "!" and "?", so the Latin "." is never a terminator; the
        # classifier just protects abbreviation periods (e.g. embedded "Dr.",
        # "U.S.") exactly as the legacy path did.
        USE_PERIOD_CLASSIFIER = True
