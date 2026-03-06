# -*- coding: utf-8 -*-
import pytest

HYBRID_RULES_TEST_CASES = [
    ("Hello World. My name is Jonas.", ["Hello World.", "My name is Jonas."]),
    ("St. Michael's Church is on 5th st. near the light.", ["St. Michael's Church is on 5th st. near the light."]),
    (
        "Hola Srta. Ledesma. Buenos días, soy el Lic. Naser Pastoriza.",
        ["Hola Srta. Ledesma.", "Buenos días, soy el Lic. Naser Pastoriza."],
    ),
    ("他说：「今天先这样。」然后离开。", ["他说：「今天先这样。」", "然后离开。"]),
    (
        "这个功能支持AI、U.S.标准。Really useful!",
        ["这个功能支持AI、U.S.标准。", "Really useful!"],
    ),
    (
        "Hola Srta. Ledesma. 他说：「今天先这样。」 Then he left.",
        ["Hola Srta. Ledesma.", "他说：「今天先这样。」", "Then he left."],
    ),
    (
        'She turned to him, "This is great." 然后离开。',
        ['She turned to him, "This is great."', "然后离开。"],
    ),
    (
        '"Is anyone there?" she called. No one answered.',
        ['"Is anyone there?" she called.', "No one answered."],
    ),
    (
        'He shouted, "Run!" and everyone scattered.',
        ['He shouted, "Run!" and everyone scattered.'],
    ),
    (
        "«Ninguna mente extraordinaria está exenta de un toque de demencia.», dijo Aristóteles.",
        ["«Ninguna mente extraordinaria está exenta de un toque de demencia.», dijo Aristóteles."],
    ),
    (
        "「今天先这样。」他说。然后离开。",
        ["「今天先这样。」他说。", "然后离开。"],
    ),
    ("¿Cómo está hoy? 我很好。See you soon.", ["¿Cómo está hoy?", "我很好。", "See you soon."]),
    ("版本号是3.14。The next release is 4.0.", ["版本号是3.14。", "The next release is 4.0."]),
]


@pytest.mark.parametrize("text,expected_sents", HYBRID_RULES_TEST_CASES)
def test_en_es_zh_sbd(en_es_zh_default_fixture, text, expected_sents):
    segments = en_es_zh_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


def test_en_es_zh_char_spans(en_es_zh_no_clean_with_span_fixture):
    text = "Hola Srta. Ledesma. 他说：「今天先这样。」 Then he left."
    spans = en_es_zh_no_clean_with_span_fixture.segment(text)
    assert text == "".join(s.sent for s in spans)
