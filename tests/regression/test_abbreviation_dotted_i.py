# -*- coding: utf-8 -*-
"""Regression: the abbreviation period-prefilter must handle U+0130 'İ'.

The automaton is keyed on '<abbr>.' as a pre-filter, but it is searched on
``text.lower()``. U+0130 'İ' (LATIN CAPITAL LETTER I WITH DOT ABOVE) is the only
Unicode character whose ``.lower()`` changes length — it expands to 'i' + a
combining dot above (U+0307). So an abbreviation occurrence ending in 'İ' and
followed by a period becomes '...i̇.' when lowered, and the '<abbr>.' key (e.g.
'vi.') no longer matches: the abbreviation is missed and the period over-splits.
Abbreviations ending in 'i' therefore keep the bare key (the original behavior).
"""

import unicodedata

from sentencesplit import Segmenter


def test_dotted_capital_i_does_not_break_abbreviation_prefilter():
    # 'vi' is a German NUMBER_ABBREVIATION (Roman numeral). The 'İ' spelling must
    # segment identically to the plain-ASCII 'vi' control: one joined sentence.
    ascii_control = Segmenter(language="de").segment("Band vi. Der Rest folgt.")
    dotted_i = Segmenter(language="de").segment("Band vİ. Der Rest folgt.")
    assert len(dotted_i) == len(ascii_control) == 1, dotted_i
    assert dotted_i == ["Band vİ. Der Rest folgt."], dotted_i


def test_dotted_capital_i_is_still_the_only_length_changing_lowercase():
    # The fix assumes 'İ' is the sole char whose .lower() is multi-char (so only
    # 'i'-ending abbreviations are affected). If a future Unicode update adds
    # another, this fails loudly so the prefilter logic can be revisited.
    expanding = [chr(c) for c in range(0x110000) if len(chr(c).lower()) != 1]
    assert expanding == ["İ"], expanding
    assert "İ".lower() == "i" + unicodedata.lookup("COMBINING DOT ABOVE")
