# -*- coding: utf-8 -*-
from sentencesplit.lang.common import Common, Standard, canonical_abbreviations


class Tagalog(Common, Standard):
    iso_code = "tl"

    # Tagalog overrides zero scan methods and uses no elision, so it rides the
    # base PeriodClassifier (BASE_POLICY) inherited from Standard directly. Its
    # prepositive/number abbreviation lists (Dr./G./Gng./Sta./No./Blg./…) are
    # handled by the base classifier's prepositive and number branches. Tagalog
    # is NOT one of the CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE languages, so that
    # flag stays off and capital followers flow through the split-mode ambiguity
    # dial.

    class Abbreviation(Standard.Abbreviation):
        # Stored in canonical form (lowercased, de-duplicated, sorted); see
        # ``canonical_abbreviations`` and the
        # ``test_abbreviations_are_canonical_form`` lint.
        ABBREVIATIONS = canonical_abbreviations(
            [
                "bb",  # Binibini
                "bbg",  # Binibining
                "blg",  # Bilang
                "bp",  # Batas Pambansa
                "dis",  # Disyembre
                "dr",
                "engr",
                "g",  # Ginoo (single-letter; kept prepositive since it's always a title)
                "gat",
                "gng",  # Ginang
                "hal",  # Halimbawa
                "hul",  # Hulyo
                "hun",  # Hunyo
                "jr",
                "kgg",  # Kagalang-galang
                "kon",  # Konde/Konsehal (context-dependent)
                "ma",  # Maria (name abbreviation)
                "no",  # Numero
                "nob",  # Nobyembre
                "okt",  # Oktubre
                "pang",
                "pn",  # Panginoon
                "prop",
                "set",  # Setyembre
                "sr",
                "st",
                "sta",
            ]
        )
        PREPOSITIVE_ABBREVIATIONS = [
            "bb",
            "dr",
            "engr",
            "g",
            "gat",
            "gng",
            "kgg",
            "kon",
            "ma",
            "pn",
            "sr",
            "sta",
        ]
        NUMBER_ABBREVIATIONS = ["blg", "bp", "hal", "no"]
