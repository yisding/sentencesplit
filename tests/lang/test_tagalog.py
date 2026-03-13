# -*- coding: utf-8 -*-
import pytest

TAGALOG_RULES_TEST_CASES = [
    ("Kumusta ka? Mabuti naman ako.", ["Kumusta ka?", "Mabuti naman ako."]),
    ("Nakilala ko si G. Dela Cruz. Mabait siya.", ["Nakilala ko si G. Dela Cruz.", "Mabait siya."]),
    ("Dumating si Bb. Reyes sa pulong.", ["Dumating si Bb. Reyes sa pulong."]),
    (
        "Nagbigay ng pahayag si Gng. Santos! Nagpasalamat ang lahat.",
        ["Nagbigay ng pahayag si Gng. Santos!", "Nagpasalamat ang lahat."],
    ),
    ("Nakatira siya sa Blg. 12 sa Kalye Rizal.", ["Nakatira siya sa Blg. 12 sa Kalye Rizal."]),
    ("Pakiusap, tingnan ang hal. 25 bago ka magsagot.", ["Pakiusap, tingnan ang hal. 25 bago ka magsagot."]),
    (
        "Si Dr. Ramos at si Engr. Dizon ay dumalo sa pulong.",
        ["Si Dr. Ramos at si Engr. Dizon ay dumalo sa pulong."],
    ),
    (
        "Nagkita sina G. at Gng. Dela Cruz sa parke. Umuwi sila nang maaga.",
        ["Nagkita sina G. at Gng. Dela Cruz sa parke.", "Umuwi sila nang maaga."],
    ),
    (
        "Ang susunod na pagpupulong ay sa Set. 15, 2025 sa bulwagan.",
        ["Ang susunod na pagpupulong ay sa Set. 15, 2025 sa bulwagan."],
    ),
    (
        "Ipinanganak siya noong Okt. 2, 1990. Lumipat sila noong Nob. 3, 2001.",
        ["Ipinanganak siya noong Okt. 2, 1990.", "Lumipat sila noong Nob. 3, 2001."],
    ),
    (
        "Dumalo si Bb. Ma. Santos sa programa.",
        ["Dumalo si Bb. Ma. Santos sa programa."],
    ),
    (
        "Dumating si Sr. dela Torre. Pagkatapos ay nagsimula ang programa.",
        ["Dumating si Sr. dela Torre.", "Pagkatapos ay nagsimula ang programa."],
    ),
    ("Ayon sa Kgg. na hukom, tuloy ang pagdinig.", ["Ayon sa Kgg. na hukom, tuloy ang pagdinig."]),
    ("Tingnan ang No. 12 sa talaan.", ["Tingnan ang No. 12 sa talaan."]),
    ("Sinusunod nito ang Bp. 220 sa proyekto.", ["Sinusunod nito ang Bp. 220 sa proyekto."]),
    ("Nakatira sila sa Sta. Ana, Manila.", ["Nakatira sila sa Sta. Ana, Manila."]),
    (
        "Si Juan dela Cruz Jr. ay dumating. Nagsimula ang pulong.",
        ["Si Juan dela Cruz Jr. ay dumating.", "Nagsimula ang pulong."],
    ),
    ("Tingnan ang Hal. 5 sa aklat.", ["Tingnan ang Hal. 5 sa aklat."]),
    # Sta. is prepositive — period protected before place names
    (
        "Pumunta siya sa Sta. Cruz. Pagkatapos ay umuwi siya.",
        ["Pumunta siya sa Sta. Cruz.", "Pagkatapos ay umuwi siya."],
    ),
    ("Pumunta siya sa Sta. Mesa. Doon siya nakatira.", ["Pumunta siya sa Sta. Mesa.", "Doon siya nakatira."]),
    ("Galing siya sa Sta. Rosa at Sta. Cruz.", ["Galing siya sa Sta. Rosa at Sta. Cruz."]),
    # Abbreviation before question/exclamation mark
    ("Nakilala mo ba si Dr. Ramos?", ["Nakilala mo ba si Dr. Ramos?"]),
    ("Dumating na si Gng. Santos!", ["Dumating na si Gng. Santos!"]),
    # Multiple number abbreviations in one sentence
    ("Tingnan ang No. 12 at Blg. 5.", ["Tingnan ang No. 12 at Blg. 5."]),
    # Abbreviation at end of text (no trailing sentence)
    ("Nakilala ko si G. Dela Cruz.", ["Nakilala ko si G. Dela Cruz."]),
    # Regular word "bin" should not prevent sentence split
    ("Ilagay mo sa bin. Pagkatapos ay umalis ka.", ["Ilagay mo sa bin.", "Pagkatapos ay umalis ka."]),
]


@pytest.mark.parametrize("text,expected_sents", TAGALOG_RULES_TEST_CASES)
def test_tl_sbd(tl_default_fixture, text, expected_sents):
    """Tagalog language SBD tests"""
    segments = tl_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
