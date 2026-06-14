# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Greek(Common, Standard):
    iso_code = "el"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[\.;!\?]|.*?$")
    Punctuations = [".", "!", ";", "?"]

    class AbbreviationReplacer(Standard.AbbreviationReplacer):
        # Greek overrides zero scan methods and uses no elision, so it rides the
        # base PeriodClassifier (BASE_POLICY) directly. The classifier reads the
        # CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE flag off this replacer (a Greek
        # capital follower of a plain abbreviation is a real boundary). The other
        # Greek flags — PROTECT_ALLCAPS_IMPRINT_SUFFIXES, NON_LATIN_CAPITAL_STARTS_SENTENCE
        # — plus the Unicode MULTI_PERIOD_ABBREVIATION_REGEX drive only the later
        # passes (replace_multi_period_abbreviations, the all-caps imprint /
        # uppercase-initialism restores) that V2 leaves untouched, so no policy
        # hook is needed.
        CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE = True
        PROTECT_ALLCAPS_IMPRINT_SUFFIXES = True
        # Greek does not capitalize common nouns mid-sentence, so a capital after
        # a multi-period abbreviation's period ("π.Χ. Ήταν …") is a real sentence
        # boundary even for a pure single-letter initialism.
        NON_LATIN_CAPITAL_STARTS_SENTENCE = True

    # The shared MULTI_PERIOD_ABBREVIATION_REGEX only matches ASCII letters, so
    # Greek multi-period abbreviations such as "μ.Χ." (A.D.) and "Ε.Ε." (E.U.)
    # are never recognised and their internal periods are treated as sentence
    # boundaries. Allow Greek (and Latin) letters via a Unicode letter class.
    MULTI_PERIOD_ABBREVIATION_REGEX = re.compile(r"(?<!\w)(?:[^\W\d_]{1,3}\.)+[^\W\d_]\.", re.IGNORECASE | re.UNICODE)

    class Abbreviation(Standard.Abbreviation):
        # Greek-specific abbreviations appended to the inherited Standard list
        # (which the inherited PREPOSITIVE/NUMBER sets still reference).
        # Multi-period abbreviations are stored as the lowercased form minus the
        # trailing period (e.g. "μ.χ" for "μ.Χ."); replace_multi_period_abbreviations
        # protects the internal dots. Matching is re.IGNORECASE.
        ABBREVIATIONS = Standard.Abbreviation.ABBREVIATIONS + [
            "μ.χ",  # μ.Χ. (A.D.)
            "π.χ",  # π.Χ. (B.C.) / π.χ. (e.g.)
            "ε.ε",  # Ε.Ε. (E.U.)
            "κ.λπ",  # κ.λπ. (etc.)
            "κ.ά",  # κ.ά. (et al.)
            "κ.τ.λ",  # κ.τ.λ. (etc.)
            "αρ",  # αρ. (no.)
            "σελ",  # σελ. (p.)
            "βλ",  # βλ. (see)
        ]
