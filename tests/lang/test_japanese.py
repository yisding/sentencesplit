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
    (
        "彼は「本当に来るの？」と聞いた。私は『行きます！』と答えた。",
        ["彼は「本当に来るの？」と聞いた。", "私は『行きます！』と答えた。"],
    ),
    (
        "リリースはver.2.1です。次は2.2を予定しています。",
        ["リリースはver.2.1です。", "次は2.2を予定しています。"],
    ),
    (
        "今日はAIとU.S.の事例を調査する。明日まとめる。",
        ["今日はAIとU.S.の事例を調査する。", "明日まとめる。"],
    ),
    (
        "まず確認する……次に実装する。最後に共有する！",
        ["まず確認する……次に実装する。", "最後に共有する！"],
    ),
    (
        "本当に大丈夫？！たぶん大丈夫。",
        ["本当に大丈夫？！", "たぶん大丈夫。"],
    ),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_JA_RULES_TEST_CASES)
def test_ja_sbd(ja_default_fixture, text, expected_sents):
    """Japanese language SBD tests"""
    segments = ja_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


JA_TEST_CASES_CLEAN = [("これは父の\n家です。", ["これは父の家です。"]), ("この計画は\nまだ続きます。", ["この計画はまだ続きます。"])]


@pytest.mark.parametrize("text,expected_sents", JA_TEST_CASES_CLEAN)
def test_ja_sbd_clean(ja_with_clean_no_span_fixture, text, expected_sents):
    """Japanese language SBD tests with clean=True"""
    segments = ja_with_clean_no_span_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
