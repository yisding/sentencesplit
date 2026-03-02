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
    (
        "他说：「今天先这样。」然后离开。",
        ["他说：「今天先这样。」", "然后离开。"],
    ),
    (
        "她问《计划A（试行版）！》什么时候发布？预计明天。",
        ["她问《计划A（试行版）！》什么时候发布？", "预计明天。"],
    ),
    (
        "版本号是3.14。下一个里程碑是4.0。",
        ["版本号是3.14。", "下一个里程碑是4.0。"],
    ),
    (
        "这个功能支持AI、U.S.标准。真的很实用！",
        ["这个功能支持AI、U.S.标准。", "真的很实用！"],
    ),
    (
        "先看第一部分……再看第二部分。最后总结！",
        ["先看第一部分……再看第二部分。", "最后总结！"],
    ),
    (
        "今天上线了吗？！还没有。",
        ["今天上线了吗？！", "还没有。"],
    ),
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


def test_zh_fullwidth_double_punctuation(zh_default_fixture):
    """All 4 full-width double punctuation combos split correctly."""
    # ？！
    assert [s.strip() for s in zh_default_fixture.segment("真的？！下一句。")] == ["真的？！", "下一句。"]
    # ！？
    assert [s.strip() for s in zh_default_fixture.segment("真的！？下一句。")] == ["真的！？", "下一句。"]
    # ？？
    assert [s.strip() for s in zh_default_fixture.segment("真的？？下一句。")] == ["真的？？", "下一句。"]
    # ！！
    assert [s.strip() for s in zh_default_fixture.segment("真的！！下一句。")] == ["真的！！", "下一句。"]


def test_zh_corner_quote_spans(zh_no_clean_with_span_fixture):
    """Char spans round-trip correctly with corner brackets."""
    text = "他说：「今天先这样。」然后离开。"
    spans = zh_no_clean_with_span_fixture.segment(text)
    assert text == "".join(s.sent for s in spans)
