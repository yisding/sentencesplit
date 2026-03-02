# -*- coding: utf-8 -*-
import pytest

GOLDEN_ZH_RULES_TEST_CASES = [
    (
        "安永已聯繫周怡安親屬，協助辦理簽證相關事宜，周怡安家屬1月1日晚間搭乘東方航空班機抵達上海，他們步入入境大廳時神情落寞、不發一語。周怡安來自台中，去年剛從元智大學畢業，同年9月加入安永。",
        [
            "安永已聯繫周怡安親屬，協助辦理簽證相關事宜，周怡安家屬1月1日晚間搭乘東方航空班機抵達上海，他們步入入境大廳時神情落寞、不發一語。",
            "周怡安來自台中，去年剛從元智大學畢業，同年9月加入安永。",
        ],
    ),
    ("我们明天一起去看《摔跤吧！爸爸》好吗？好！", ["我们明天一起去看《摔跤吧！爸爸》好吗？", "好！"]),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_ZH_RULES_TEST_CASES)
def test_zsh_sbd(zh_default_fixture, text, expected_sents):
    """Chinese language SBD tests from Pragmatic Segmenter"""
    segments = zh_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


def test_zh_mixed_cjk_latin(zh_default_fixture):
    """CJK boundary regex handles embedded Latin text correctly."""
    text = "版本号是3.14。下一句话。"
    segments = [s.strip() for s in zh_default_fixture.segment(text)]
    assert segments == ["版本号是3.14。", "下一句话。"]


def test_zh_char_spans(zh_no_clean_with_span_fixture):
    """Char spans round-trip correctly for Chinese text."""
    text = "这是第一句。这是第二句。"
    spans = zh_no_clean_with_span_fixture.segment(text)
    assert text == "".join(s.sent for s in spans)
    assert spans[0].start == 0
    assert spans[-1].end == len(text)
