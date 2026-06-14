# -*- coding: utf-8 -*-
"""Regression guard for ``LANGUAGE_CODES`` view operations on alternative
Python implementations (notably PyPy).

``_LazyLanguageCodes`` overrides ``__len__`` / ``__iter__`` while keeping a real
backing ``dict``. Earlier versions reached into that backing store via the bound
``dict.keys(self)`` view (``len(... | set(dict.keys(self)))`` and
``for code in dict.keys(self)``). On CPython the ``dict_keys`` view reports its
length straight from the C-level storage, so this was harmless. On PyPy the
view's ``__len__`` dispatches back to the instance's overridden ``__len__``,
producing infinite recursion (``RecursionError``) the moment anything called
``len(LANGUAGE_CODES)`` or materialized ``set(LANGUAGE_CODES)`` — which pytest's
``parametrize(sorted(LANGUAGE_CODES))`` does at collection time, taking the whole
suite down.

The fix snapshots the backing store with ``dict.copy(self)`` (a plain ``dict``
that reads the raw storage on every implementation) instead of the bound view.
These assertions exercise the affected paths on every interpreter; on PyPy they
fail loudly with ``RecursionError`` if the anti-pattern returns.
"""

from sentencesplit.languages import (
    LANGUAGE_CODES,
    list_languages,
    register_language,
    unregister_language,
)


def test_len_does_not_recurse():
    # Must not raise RecursionError on PyPy; must equal the iterated count.
    assert len(LANGUAGE_CODES) == len(list(LANGUAGE_CODES))


def test_set_materialization_matches_iteration():
    # ``set(LANGUAGE_CODES)`` size-hints via ``__len__`` and then iterates; both
    # paths previously recursed on PyPy.
    assert set(LANGUAGE_CODES) == set(iter(LANGUAGE_CODES))


def test_builtin_codes_present_in_all_views():
    codes = set(LANGUAGE_CODES)
    for code in ("en", "zh", "ja", "es", "en_es_zh", "en_legal"):
        assert code in codes
        assert code in LANGUAGE_CODES
    assert sorted(LANGUAGE_CODES.keys()) == list_languages()


def test_len_tracks_dynamic_registration():
    before = len(LANGUAGE_CODES)
    assert "qa_dummy" not in LANGUAGE_CODES

    english = LANGUAGE_CODES["en"]
    register_language("qa_dummy", english)
    try:
        assert len(LANGUAGE_CODES) == before + 1
        assert "qa_dummy" in set(LANGUAGE_CODES)
        assert "qa_dummy" in list_languages()
    finally:
        unregister_language("qa_dummy")

    assert len(LANGUAGE_CODES) == before
    assert "qa_dummy" not in set(LANGUAGE_CODES)
