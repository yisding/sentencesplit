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
        "彼は『本当に大丈夫？まだ早い！でも進もう。』と答えた。",
        ["彼は『本当に大丈夫？まだ早い！でも進もう。』と答えた。"],
    ),
    (
        "注意書き【静かにして。急がないで！確認した？】を読んだ。",
        ["注意書き【静かにして。急がないで！確認した？】を読んだ。"],
    ),
    (
        "引用《この仕様は古い。更新する？いますぐ！》を残した。",
        ["引用《この仕様は古い。更新する？いますぐ！》を残した。"],
    ),
    (
        "注釈〈ここで止まる？いや、続ける！了解。〉を付けた。",
        ["注釈〈ここで止まる？いや、続ける！了解。〉を付けた。"],
    ),
    (
        "補足〔先に試す。失敗した？やり直そう！〕を追加した。",
        ["補足〔先に試す。失敗した？やり直そう！〕を追加した。"],
    ),
    (
        "彼女は“それは違う。なぜ？本当だ！”と言って去った。",
        ["彼女は“それは違う。なぜ？本当だ！”と言って去った。"],
    ),
    (
        "『了解。』次へ。",
        ["『了解。』", "次へ。"],
    ),
    (
        "“了解。”次へ。",
        ["“了解。”", "次へ。"],
    ),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_JA_RULES_TEST_CASES)
def test_ja_sbd(ja_default_fixture, text, expected_sents):
    """Japanese language SBD tests"""
    segments = ja_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


JA_TEST_CASES_CLEAN = [("これは父の\n家です。", ["これは父の家です。"])]


@pytest.mark.parametrize("text,expected_sents", JA_TEST_CASES_CLEAN)
def test_ja_sbd_clean(ja_with_clean_no_span_fixture, text, expected_sents):
    """Japanese language SBD tests with clean=True"""
    segments = ja_with_clean_no_span_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
