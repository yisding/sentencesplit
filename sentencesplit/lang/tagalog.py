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
            "dis",  # Disyembre
            "dr",
            "engr",
            "g",  # Ginoo
            "gat",
            "gng",  # Ginang
            "hal",  # Halimbawa
            "hul",  # Hulyo
            "hun",  # Hunyo
            "jr",
            "kgg",  # Kagalang-galang
            "kon",  # Konde/Konsehal (context-dependent)
            "ma",  # Maria (name abbreviation)
            "bp",  # Blg. ng batas/panukala
            "nob",  # Nobyembre
            "no",  # Numero
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
        NUMBER_ABBREVIATIONS = ["blg", "bp", "no"]
