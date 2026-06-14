# -*- coding: utf-8 -*-
"""Regression: re-registering a language must rebuild its abbreviation data.

``_evict_profile`` is documented to make a re-registration "rebuilt fresh", but
it only dropped the cached ``LanguageProfile`` — the per-``Abbreviation``-class
Aho-Corasick data in ``AbbreviationReplacer._data_cache`` survived, so a class
re-registered after its abbreviation list changed kept the stale automaton.
"""

from sentencesplit import Segmenter
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.english import English
from sentencesplit.languages import register_language, unregister_language


def test_reregistration_rebuilds_abbreviation_data():
    class CustomAbbr(English.Abbreviation):
        ABBREVIATIONS = list(English.Abbreviation.ABBREVIATIONS)

    class CustomEn(English):
        Abbreviation = CustomAbbr

    code = "zz"
    try:
        register_language(code, CustomEn)
        # Build and cache the abbreviation automaton for CustomAbbr.
        Segmenter(language=code).segment("Dr. Smith arrived.")
        assert "zorp" not in AbbreviationReplacer._data_cache[CustomAbbr].abbr_set

        # Change the abbreviation set and re-register the (same) class.
        CustomAbbr.ABBREVIATIONS.append("zorp")
        register_language(code, CustomEn)

        # The next use must rebuild the automaton fresh from the new list.
        Segmenter(language=code).segment("Zorp. Smith arrived.")
        assert "zorp" in AbbreviationReplacer._data_cache[CustomAbbr].abbr_set
    finally:
        unregister_language(code)
