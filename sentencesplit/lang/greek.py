# -*- coding: utf-8 -*-
import re

from sentencesplit.lang.common import Common, Standard


class Greek(Common, Standard):
    iso_code = "el"

    SENTENCE_BOUNDARY_REGEX = re.compile(r".*?[\.;!\?]|.*?$")
    Punctuations = [".", "!", ";", "?"]

    class AbbreviationReplacer(Standard.AbbreviationReplacer):
        CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE = True
        PROTECT_ALLCAPS_IMPRINT_SUFFIXES = True
        # Latin boundary abbreviations inside Greek text are commonly embedded
        # names ("U.S. Embassy"). Greek uppercase boundaries are handled by the
        # non-Latin multi-period rule below, so only aggressive mode splits
        # ambiguous Latin uppercase followers here.
        BOUNDARY_ABBREVIATION_SPLIT_MIN_RANK = 2
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
