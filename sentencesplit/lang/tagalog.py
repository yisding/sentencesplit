# -*- coding: utf-8 -*-
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard


class Tagalog(Common, Standard):
    iso_code = "tl"

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = [
            "bb",  # Binibini
            "bbg",  # Binibining
            "bin",  # Binibini
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
            "sta",
            "st",
        ]
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
        ]
        NUMBER_ABBREVIATIONS = ["blg", "bp", "hal", "no"]
