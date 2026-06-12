from __future__ import annotations

import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import sentencesplit
import sentencesplit.language_profile as language_profile
import sentencesplit.languages as languages
from sentencesplit.abbreviation_replacer import AbbreviationReplacer

_CONCURRENT_CASES = (
    ("en", "Dr. Smith went home. He slept.", ["Dr. Smith went home.", "He slept."]),
    ("es", "Hola mundo. Adios mundo.", ["Hola mundo.", "Adios mundo."]),
    ("zh", "\u7b2c\u4e00\u53e5\u3002\u7b2c\u4e8c\u53e5\u3002", ["\u7b2c\u4e00\u53e5\u3002", "\u7b2c\u4e8c\u53e5\u3002"]),
    (
        "ja",
        "\u3053\u308c\u306f\u6587\u3067\u3059\u3002\u6b21\u306e\u6587\u3067\u3059\u3002",
        ["\u3053\u308c\u306f\u6587\u3067\u3059\u3002", "\u6b21\u306e\u6587\u3067\u3059\u3002"],
    ),
    ("de", "Das ist gut. Weiter geht es.", ["Das ist gut.", "Weiter geht es."]),
    ("fr", "Bonjour le monde. Au revoir.", ["Bonjour le monde.", "Au revoir."]),
)


@contextmanager
def _cold_lazy_state(codes: set[str]):
    with languages._LANGUAGE_LOCK:
        registry_snapshot = dict.copy(languages.LANGUAGE_CODES)
        removed_snapshot = set(languages.LANGUAGE_CODES._removed)
        loaded_snapshot = dict(languages._loaded_cache)
        languages._loaded_cache.clear()
        for code in codes:
            if code in languages._LANGUAGE_MODULES:
                dict.pop(languages.LANGUAGE_CODES, code, None)
                languages.LANGUAGE_CODES._removed.discard(code)

    with language_profile._PROFILE_CACHE_LOCK:
        language_profile._PROFILE_CACHE.clear()

    with AbbreviationReplacer._cache_lock:
        AbbreviationReplacer._data_cache.clear()
        AbbreviationReplacer._boundary_regex_cache.clear()

    try:
        yield
    finally:
        with languages._LANGUAGE_LOCK:
            languages._loaded_cache.clear()
            languages._loaded_cache.update(loaded_snapshot)
            dict.clear(languages.LANGUAGE_CODES)
            dict.update(languages.LANGUAGE_CODES, registry_snapshot)
            languages.LANGUAGE_CODES._removed = removed_snapshot


def test_free_threaded_build_keeps_gil_disabled_when_available():
    if sysconfig.get_config_var("Py_GIL_DISABLED") == 1:
        assert sys._is_gil_enabled() is False


def test_segmenter_concurrent_cold_cache_smoke():
    codes = {code for code, _, _ in _CONCURRENT_CASES}

    def run(index: int) -> str:
        code, text, expected = _CONCURRENT_CASES[index % len(_CONCURRENT_CASES)]
        actual = [segment.strip() for segment in sentencesplit.Segmenter(language=code).segment(text)]
        assert actual == expected
        return code

    with _cold_lazy_state(codes):
        with ThreadPoolExecutor(max_workers=32) as pool:
            results = list(pool.map(run, range(2000)))

    assert set(results) == codes
