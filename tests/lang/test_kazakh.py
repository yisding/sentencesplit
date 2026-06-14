# -*- coding: utf-8 -*-
import pytest

GOLDEN_KK_RULES_TEST_CASES = [
    (
        "Мұхитқа тікелей шыға алмайтын мемлекеттердің ішінде Қазақстан - ең үлкені.",
        ["Мұхитқа тікелей шыға алмайтын мемлекеттердің ішінде Қазақстан - ең үлкені."],
    ),
    (
        "Оқушылар үйі, Достық даңғылы, Абай даналығы, ауыл шаруашылығы – кім? не?",
        ["Оқушылар үйі, Достық даңғылы, Абай даналығы, ауыл шаруашылығы – кім?", "не?"],
    ),
    (
        "Әр түрлі өлшемнің атауы болып табылатын м (метр), см (сантиметр), кг (киллограмм), т (тонна), га (гектар), ц (центнер), т. б. (тағы басқа), тәрізді белгілер де қысқарған сөздер болып табылады.",
        [
            "Әр түрлі өлшемнің атауы болып табылатын м (метр), см (сантиметр), кг (киллограмм), т (тонна), га (гектар), ц (центнер), т. б. (тағы басқа), тәрізді белгілер де қысқарған сөздер болып табылады."
        ],
    ),
    (
        "Мысалы: обкомға (облыстық комитетке) барды, ауаткомда (аудандық атқару комитетінде) болды, педучилищеге (педагогтік училищеге) түсті, медпункттің (медициналық пункттің) алдында т. б.",
        [
            "Мысалы: обкомға (облыстық комитетке) барды, ауаткомда (аудандық атқару комитетінде) болды, педучилищеге (педагогтік училищеге) түсті, медпункттің (медициналық пункттің) алдында т. б."
        ],
    ),
    (
        "Елдің жалпы ішкі өнімі ЖІӨ (номинал) = $225.619 млрд (2014)",
        ["Елдің жалпы ішкі өнімі ЖІӨ (номинал) = $225.619 млрд (2014)"],
    ),
    (
        "Ресейдiң әлеуметтiк-экономикалық жағдайы.XVIII ғасырдың бiрiншi ширегiнде Ресейге тән нәрсе.",
        ["Ресейдiң әлеуметтiк-экономикалық жағдайы.", "XVIII ғасырдың бiрiншi ширегiнде Ресейге тән нәрсе."],
    ),
    (
        "(«Егемен Қазақстан», 7 қыркүйек 2012 жыл. №590-591); Бұл туралы кеше санпедқадағалау комитетінің облыыстық департаменті хабарлады. («Айқын», 23 сəуір 2010 жыл. № 70).",
        [
            "(«Егемен Қазақстан», 7 қыркүйек 2012 жыл. №590-591); Бұл туралы кеше санпедқадағалау комитетінің облыыстық департаменті хабарлады.",
            "(«Айқын», 23 сəуір 2010 жыл. № 70).",
        ],
    ),
    (
        "Иран революциясы (1905 — 11) және азаматтық қозғалыс (1918 — 21) кезінде А. Фарахани, М. Кермани, М. Т. Бехар, т.б. ақындар демократиялық идеяның жыршысы болды.",
        [
            "Иран революциясы (1905 — 11) және азаматтық қозғалыс (1918 — 21) кезінде А. Фарахани, М. Кермани, М. Т. Бехар, т.б. ақындар демократиялық идеяның жыршысы болды."
        ],
    ),
    (
        "Владимир Федосеев: Аттар магиясы енді жоқ http://www.vremya.ru/2003/179/10/80980.html",
        ["Владимир Федосеев: Аттар магиясы енді жоқ http://www.vremya.ru/2003/179/10/80980.html"],
    ),
    ("Бірақ оның енді не керегі бар? — деді.", ["Бірақ оның енді не керегі бар? — деді."]),
    (
        "Сондықтан шапаныма жегізіп отырғаным! - деп, жауап береді.",
        ["Сондықтан шапаныма жегізіп отырғаным! - деп, жауап береді."],
    ),
    (
        "Б.з.б. 6 – 3 ғасырларда конфуцийшілдік, моизм, легизм мектептерінің қалыптасуы нәтижесінде Қытай философиясы пайда болды.",
        [
            "Б.з.б. 6 – 3 ғасырларда конфуцийшілдік, моизм, легизм мектептерінің қалыптасуы нәтижесінде Қытай философиясы пайда болды."
        ],
    ),
    ("'Та марбута' тек сөз соңында екі түрде жазылады:", ["'Та марбута' тек сөз соңында екі түрде жазылады:"]),
]


@pytest.mark.parametrize("text,expected_sents", GOLDEN_KK_RULES_TEST_CASES)
def test_kk_sbd(kk_default_fixture, text, expected_sents):
    """Kazakh language SBD tests"""
    segments = kk_default_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents


def test_kk_single_period_abbreviations_do_not_split_before_numeric_continuation(kk_default_fixture):
    segments = kk_default_fixture.segment("обл. 2014 жылы тех. (жаңа) қызмет ашылды.")

    assert segments == ["обл. 2014 жылы тех. (жаңа) қызмет ашылды."]


def test_kk_capitalized_single_period_abbreviations_do_not_split_before_numeric_continuation(kk_default_fixture):
    segments = kk_default_fixture.segment("Обл. 2014 жылы ашылды.")

    assert segments == ["Обл. 2014 жылы ашылды."]


@pytest.mark.parametrize(
    "text",
    [
        "U.S. елшілігі ашылды.",
        "U.S. 2014 жылы ашылды.",
        "E.U. елдері келісті.",
    ],
)
def test_kk_latin_initialisms_do_not_split_before_kazakh_continuation(kk_default_fixture, text):
    assert kk_default_fixture.segment(text) == [text]


@pytest.mark.parametrize(
    "text",
    [
        "обл. әкімі келді.",
        "тех. қызмет ашылды.",
    ],
)
def test_kk_single_period_abbreviations_do_not_split_before_cyrillic_lowercase(kk_default_fixture, text):
    assert kk_default_fixture.segment(text) == [text]


# --- Parity assertions re-homed from the retired v2 oracle (tests/v2/oracle.py) ---
# The deleted differential oracle froze two Kazakh facts about KK_POLICY's
# follower-class dispatch; they are asserted here directly at segment() level.


def test_kk_obl_wide_follower_keeps_period_joined(kk_default_fixture):
    # "обл. қала" rides the WIDE Kazakh-Cyrillic lowercase follower class
    # (_KK_WIDE_FOLLOWER_STEMS): the period after 'обл.' is non-terminal before
    # the lowercase 'қала', so it stays one sentence — while a genuine boundary
    # ('. ' + capitalized start) still splits.
    assert kk_default_fixture.segment("обл. қала үлкен.") == ["обл. қала үлкен."]
    assert kk_default_fixture.segment("обл. қала. Келесі сөйлем.") == ["обл. қала. ", "Келесі сөйлем."]


def test_kk_smeglyad_ris_are_unprotected(kk_default_fixture):
    # "См." / "рис." are NOT registered Kazakh abbreviations: they fall through to
    # the base ASCII-follower REGULAR branch and are NOT protected (legacy oracle
    # positions were []), so the period after 'рис.' is a boundary before the
    # following digit-led clause. (Contrast 'обл.' above, which IS protected.)
    assert kk_default_fixture.segment("Бұл мысалы. Қараңыз 5-бет. См. рис. 3 ниже.") == [
        "Бұл мысалы. ",
        "Қараңыз 5-бет. ",
        "См. рис. ",
        "3 ниже.",
    ]
