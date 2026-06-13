# -*- coding: utf-8 -*-
"""Regression tests for Bulgarian Cyrillic multi-period abbreviation handling.

The shared ``MULTI_PERIOD_ABBREVIATION_REGEX`` (common.py) and
``WithMultiplePeriodsAndEmailRule`` (standard.py) only match ASCII ``[A-Za-z]``,
so the interior period of Cyrillic multi-period abbreviations such as ``б.р.``
was never sentinel-protected and the boundary regex shattered the token, e.g.
``Това е б.р.`` -> ``Това е б.`` + ``р.``.

Bulgarian declares 14 multi-period abbreviations; 7 of them broke because no
single-letter standalone abbreviation protected their leading segment:
``б.р``, ``б.ред``, ``бел.а``, ``бел.пр``, ``к.с``, ``н.с``, ``щ.д``.

A Unicode-aware ``MULTI_PERIOD_ABBREVIATION_REGEX`` override (mirroring Greek's
fix) protects the interior periods so the abbreviation stays a single token.
"""

import pytest

import sentencesplit

# Each previously-broken multi-period abbreviation must stay intact (a single
# sentence) when it ends a clause that continues with more text.
BULGARIAN_BROKEN_MULTI_PERIOD_CASES = [
    ("b_r", "Това е б.р. Следва текст.", ["Това е б.р. Следва текст."]),
    ("b_red", "Това е б.ред. Следва текст.", ["Това е б.ред. Следва текст."]),
    ("bel_a", "Това е бел.а. Следва текст.", ["Това е бел.а. Следва текст."]),
    ("bel_pr", "Това е бел.пр. Следва текст.", ["Това е бел.пр. Следва текст."]),
    ("k_s", "Това е к.с. Следва текст.", ["Това е к.с. Следва текст."]),
    ("n_s", "Това е н.с. Следва текст.", ["Това е н.с. Следва текст."]),
    ("sht_d", "Това е щ.д. Следва текст.", ["Това е щ.д. Следва текст."]),
]


@pytest.mark.parametrize("case_id,text,expected", BULGARIAN_BROKEN_MULTI_PERIOD_CASES)
def test_bulgarian_cyrillic_multi_period_abbreviation_kept_intact(case_id, text, expected):
    seg = sentencesplit.Segmenter(language="bg", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


# Abbreviations that already segmented correctly must keep working (no
# over-protection or regression introduced by the Unicode-aware regex).
BULGARIAN_PREVIOUSLY_OK_CASES = [
    ("p_s", "Това е p.s. Следва текст.", ["Това е p.s. Следва текст."]),
    ("kv_m", "Това е кв.м. Следва текст.", ["Това е кв.м. Следва текст."]),
    ("kub_m", "Това е куб.м. Следва текст.", ["Това е куб.м. Следва текст."]),
    ("m_g", "Това е м.г. Следва текст.", ["Това е м.г. Следва текст."]),
    ("t_g", "Това е т.г. Следва текст.", ["Това е т.г. Следва текст."]),
    ("t_e", "Това е т.е. Следва текст.", ["Това е т.е. Следва текст."]),
    ("t_n", "Това е т.н. Следва текст.", ["Това е т.н. Следва текст."]),
    ("t_nar", "Това е т.нар. Следва текст.", ["Това е т.нар. Следва текст."]),
]


@pytest.mark.parametrize("case_id,text,expected", BULGARIAN_PREVIOUSLY_OK_CASES)
def test_bulgarian_previously_ok_abbreviations_still_intact(case_id, text, expected):
    seg = sentencesplit.Segmenter(language="bg", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_bulgarian_real_sentence_boundary_still_splits():
    """A genuine sentence boundary (not an abbreviation) must still split."""
    seg = sentencesplit.Segmenter(language="bg", clean=False)
    text = "Това е изречение. Следва текст."
    assert [s.strip() for s in seg.segment(text)] == ["Това е изречение.", "Следва текст."]
