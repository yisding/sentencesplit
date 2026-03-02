# -*- coding: utf-8 -*-
import pytest

GOLDEN_JA_RULES_TEST_CASES = [
    ("これはペンです。それはマーカーです。", ["これはペンです。", "それはマーカーです。"]),
    ("それは何ですか？ペンですか？", ["それは何ですか？", "ペンですか？"]),
    ("良かったね！すごい！", ["良かったね！", "すごい！"]),
    (
        "自民党税制調査会の幹部は、「引き下げ幅は３．２９％以上を目指すことになる」と指摘していて、今後、公明党と合意したうえで、３０日に決定する与党税制改正大綱に盛り込むことにしています。２％台後半を目指すとする方向で最終調整に入りました。",
        [
            "自民党税制調査会の幹部は、「引き下げ幅は３．２９％以上を目指すことになる」と指摘していて、今後、公明党と合意したうえで、３０日に決定する与党税制改正大綱に盛り込むことにしています。",
            "２％台後半を目指すとする方向で最終調整に入りました。",
        ],
    ),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_JA_RULES_TEST_CASES)
def test_ja_sbd(ja_default_fixture, text, expected_sents):
    """Japanese language SBD tests"""
    segments = ja_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


JA_TEST_CASES_CLEAN = [
    ("これは父の\n家です。", ["これは父の家です。"]),
    ("東京タワーは\nきれいです。", ["東京タワーはきれいです。"]),
    ("彼が\n来ました。", ["彼が来ました。"]),
    (
        "買い物リスト：\n・りんご\n・みかん",
        ["買い物リスト：", "・りんご", "・みかん"],
    ),
    # Headings / short paragraphs without terminal punctuation must stay separate
    ("第一章\n概要", ["第一章", "概要"]),
    ("見出し\n本文", ["見出し", "本文"]),
    # List guard: の is a continuation particle, but ・ list marker prevents joining
    ("りんごの\n・みかん", ["りんごの", "・みかん"]),
]


@pytest.mark.parametrize("text,expected_sents", JA_TEST_CASES_CLEAN)
def test_ja_sbd_clean(ja_with_clean_no_span_fixture, text, expected_sents):
    """Japanese language SBD tests with clean=True"""
    segments = ja_with_clean_no_span_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


def test_ja_mixed_cjk_latin(ja_default_fixture):
    """CJK boundary regex handles embedded Latin text correctly."""
    text = "リリースはver.2.1です。次は2.2です。"
    segments = [s.strip() for s in ja_default_fixture.segment(text)]
    assert segments == ["リリースはver.2.1です。", "次は2.2です。"]


def test_ja_char_spans(ja_no_clean_with_span_fixture):
    """Char spans round-trip correctly for Japanese text."""
    text = "これはペンです。それはマーカーです。"
    spans = ja_no_clean_with_span_fixture.segment(text)
    assert text == "".join(s.sent for s in spans)
    assert spans[0].start == 0
    assert spans[-1].end == len(text)
