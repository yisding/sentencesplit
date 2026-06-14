# -*- coding: utf-8 -*-
"""Regression: single-token abbreviations must not be stored with a trailing dot.

The Aho-Corasick prefilter keys an abbreviation as ``<abbr>.`` (it appends a
period). An entry already stored *with* a trailing dot (e.g. ``"обл."``, ``"np."``)
was therefore keyed ``<abbr>..`` and never enumerated as a candidate by the V2
period classifier, so its period was never protected — the abbreviation silently
over-split. The cleanup converged single-token abbreviations on the dominant
no-trailing-dot convention (kk/pl/ar/sk) and a guard
(``tests/test_languages.py::test_single_token_abbreviations_have_no_trailing_dot``)
keeps it that way. These cases lock in the resulting behaviour.

Internal-dot initialisms (``s.r.o``) and multi-token abbreviations (``т. б.``)
are intentionally left dotted — they are handled by the multi-period machinery,
not the automaton — so they are not part of this convention.
"""

from sentencesplit import Segmenter


def test_polish_dotted_abbreviations_protected_before_lowercase():
    # Before the fix these split after the abbreviation period; now the period is
    # protected because the (formerly invisible) abbreviation is enumerated.
    assert Segmenter("pl").segment("Zrobił to ok. piętnaście minut temu.") == ["Zrobił to ok. piętnaście minut temu."]
    assert Segmenter("pl").segment("Patrz rozdz. trzeci, str. 5.") == ["Patrz rozdz. trzeci, str. 5."]


def test_polish_abbreviation_still_splits_before_capital():
    # The fix must not over-protect: a capitalized follower is still a sentence
    # start, so "np." before "To" remains a boundary.
    assert Segmenter("pl").segment("Mam np. psa. To wszystko.") == ["Mam np. psa. ", "To wszystko."]


def test_arabic_dotted_abbreviation_protected():
    # كلم. (km) was stored with a trailing dot and never enumerated; now protected.
    assert Segmenter("ar").segment("المسافة 5 كلم. ثم توقف.") == ["المسافة 5 كلم. ثم توقف."]


def test_kazakh_dotted_abbreviation_net_neutral_after_pass_removal():
    # The bespoke whole-text Kazakh pass was retired in favour of KK_POLICY's wide
    # Cyrillic+Latin lowercase follower class. The formerly-dotted stems must stay
    # protected before a Cyrillic-lowercase / digit / "(" follower exactly as before.
    assert Segmenter("kk").segment("Ол обл. қала орталығында тұрады.") == ["Ол обл. қала орталығында тұрады."]
    assert Segmenter("kk").segment("Бұл обл. 2014 жылы құрылды.") == ["Бұл обл. 2014 жылы құрылды."]
    assert Segmenter("kk").segment("тех. (жаңа) нұсқа шықты.") == ["тех. (жаңа) нұсқа шықты."]


def test_kazakh_always_dotless_stem_not_over_protected():
    # "см" was always stored without a dot, so it must NOT inherit the wide
    # follower class — "См. рис." before a digit still splits (legacy-identical),
    # proving KK_POLICY widens only the 39 formerly-dotted stems.
    assert Segmenter("kk").segment("См. рис. 3 ниже.") == ["См. рис. ", "3 ниже."]
