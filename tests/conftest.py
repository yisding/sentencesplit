from collections.abc import Callable

import pytest

import sentencesplit


@pytest.fixture()
def segmenter_factory() -> Callable[..., sentencesplit.Segmenter]:
    def make_segmenter(language: str = "en", *, clean: bool = False, char_span: bool = False, **kwargs):
        return sentencesplit.Segmenter(language=language, clean=clean, char_span=char_span, **kwargs)

    return make_segmenter


def _segmenter_fixture(name: str, language: str, *, clean: bool = False, char_span: bool = False):
    @pytest.fixture(name=name)
    def fixture(segmenter_factory):
        return segmenter_factory(language=language, clean=clean, char_span=char_span)

    return fixture


default_en_no_clean_no_span_fixture = _segmenter_fixture("default_en_no_clean_no_span_fixture", "en")
en_with_clean_no_span_fixture = _segmenter_fixture("en_with_clean_no_span_fixture", "en", clean=True)
en_no_clean_with_span_fixture = _segmenter_fixture("en_no_clean_with_span_fixture", "en", char_span=True)

hi_default_fixture = _segmenter_fixture("hi_default_fixture", "hi")
mr_default_fixture = _segmenter_fixture("mr_default_fixture", "mr")
zh_default_fixture = _segmenter_fixture("zh_default_fixture", "zh")
es_default_fixture = _segmenter_fixture("es_default_fixture", "es")
es_with_clean_no_span_fixture = _segmenter_fixture("es_with_clean_no_span_fixture", "es", clean=True)
am_default_fixture = _segmenter_fixture("am_default_fixture", "am")
ar_default_fixture = _segmenter_fixture("ar_default_fixture", "ar")
hy_default_fixture = _segmenter_fixture("hy_default_fixture", "hy")
bg_default_fixture = _segmenter_fixture("bg_default_fixture", "bg")
ur_default_fixture = _segmenter_fixture("ur_default_fixture", "ur")
ru_default_fixture = _segmenter_fixture("ru_default_fixture", "ru")
pl_default_fixture = _segmenter_fixture("pl_default_fixture", "pl")
fa_default_fixture = _segmenter_fixture("fa_default_fixture", "fa")
nl_default_fixture = _segmenter_fixture("nl_default_fixture", "nl")
da_default_fixture = _segmenter_fixture("da_default_fixture", "da")
da_with_clean_no_span_fixture = _segmenter_fixture("da_with_clean_no_span_fixture", "da", clean=True)
fr_default_fixture = _segmenter_fixture("fr_default_fixture", "fr")
my_default_fixture = _segmenter_fixture("my_default_fixture", "my")
el_default_fixture = _segmenter_fixture("el_default_fixture", "el")
it_default_fixture = _segmenter_fixture("it_default_fixture", "it")
ja_default_fixture = _segmenter_fixture("ja_default_fixture", "ja")
ja_with_clean_no_span_fixture = _segmenter_fixture("ja_with_clean_no_span_fixture", "ja", clean=True)
de_default_fixture = _segmenter_fixture("de_default_fixture", "de")
de_with_clean_no_span_fixture = _segmenter_fixture("de_with_clean_no_span_fixture", "de", clean=True)
kk_default_fixture = _segmenter_fixture("kk_default_fixture", "kk")
sk_default_fixture = _segmenter_fixture("sk_default_fixture", "sk")
zh_no_clean_with_span_fixture = _segmenter_fixture("zh_no_clean_with_span_fixture", "zh", char_span=True)
ja_no_clean_with_span_fixture = _segmenter_fixture("ja_no_clean_with_span_fixture", "ja", char_span=True)
tl_default_fixture = _segmenter_fixture("tl_default_fixture", "tl")
en_es_zh_default_fixture = _segmenter_fixture("en_es_zh_default_fixture", "en_es_zh")
en_es_zh_no_clean_with_span_fixture = _segmenter_fixture("en_es_zh_no_clean_with_span_fixture", "en_es_zh", char_span=True)
