from collections import Counter

import pytest

from sentencesplit.languages import LANGUAGE_CODES, Language


class _Stub:
    """Sentinel class used in mutation tests to stand in for a real language."""


DEDUPED_ABBREVIATION_LANGUAGE_CODES = ("ar", "da", "es", "fr", "nl", "sk")


def test_lang_code2instance_mapping():
    for code, language_module in LANGUAGE_CODES.items():
        assert Language.get_language_code(code) == language_module


def test_registered_language_iso_codes_match_registry_keys():
    for code, language_module in LANGUAGE_CODES.items():
        assert language_module.iso_code == code


@pytest.mark.parametrize("code", DEDUPED_ABBREVIATION_LANGUAGE_CODES)
def test_language_abbreviations_do_not_repeat_literals(code):
    abbreviations = LANGUAGE_CODES[code].Abbreviation.ABBREVIATIONS
    counts = Counter(abbreviations)
    duplicates = sorted(abbreviation for abbreviation, count in counts.items() if count > 1)
    assert duplicates == []


def test_specialized_abbreviations_are_registered_abbreviations():
    for code, language_module in LANGUAGE_CODES.items():
        abbreviation = language_module.Abbreviation
        registered = set(abbreviation.ABBREVIATIONS)
        specialized = set(abbreviation.PREPOSITIVE_ABBREVIATIONS) | set(abbreviation.NUMBER_ABBREVIATIONS)
        assert sorted(specialized - registered) == []


def test_exception_on_no_lang_code_provided():
    with pytest.raises(ValueError) as e:
        Language.get_language_code("")
    assert "Provide valid language ID i.e. ISO code." in str(e.value)


def test_exception_on_unsupported_lang_code_provided():
    with pytest.raises(ValueError) as e:
        Language.get_language_code("elvish")
    assert "Provide valid language ID i.e. ISO code." in str(e.value)


@pytest.fixture
def restore_language_codes():
    """Snapshot LANGUAGE_CODES state and restore it after the test runs.

    Tests in this module mutate the global registry (set/del/pop/setdefault)
    and must leave it in its original state so unrelated tests keep working.
    """
    snapshot = dict.copy(dict(LANGUAGE_CODES))
    removed_snapshot = set(LANGUAGE_CODES._removed)
    yield
    LANGUAGE_CODES._removed = set()
    dict.clear(LANGUAGE_CODES)
    dict.update(LANGUAGE_CODES, snapshot)
    LANGUAGE_CODES._removed = removed_snapshot


def test_setitem_overrides_builtin(restore_language_codes):
    LANGUAGE_CODES["en"] = _Stub
    assert LANGUAGE_CODES["en"] is _Stub


def test_setitem_adds_new_code(restore_language_codes):
    LANGUAGE_CODES["zz"] = _Stub
    assert "zz" in LANGUAGE_CODES
    assert LANGUAGE_CODES["zz"] is _Stub


def test_delitem_removes_builtin_and_stays_removed(restore_language_codes):
    del LANGUAGE_CODES["en"]
    assert "en" not in LANGUAGE_CODES
    assert LANGUAGE_CODES.get("en") is None
    assert "en" not in list(LANGUAGE_CODES)
    with pytest.raises(KeyError):
        LANGUAGE_CODES["en"]


def test_pop_returns_and_removes(restore_language_codes):
    expected = LANGUAGE_CODES["en"]
    popped = LANGUAGE_CODES.pop("en")
    assert popped is expected
    assert "en" not in LANGUAGE_CODES


def test_pop_returns_default_for_missing():
    assert LANGUAGE_CODES.pop("xx", "default") == "default"


def test_pop_raises_keyerror_for_missing_without_default():
    with pytest.raises(KeyError):
        LANGUAGE_CODES.pop("xx")


def test_setdefault_returns_existing():
    english = LANGUAGE_CODES["en"]
    assert LANGUAGE_CODES.setdefault("en", None) is english


def test_setdefault_inserts_for_missing(restore_language_codes):
    assert LANGUAGE_CODES.setdefault("zz", _Stub) is _Stub
    assert "zz" in LANGUAGE_CODES
    assert LANGUAGE_CODES["zz"] is _Stub


def test_or_merges_with_dict():
    merged = LANGUAGE_CODES | {"yy": _Stub}
    assert type(merged) is dict
    assert merged["yy"] is _Stub
    for code in LANGUAGE_CODES:
        assert merged[code] is LANGUAGE_CODES[code]


def test_ror_merges_from_dict():
    # Right-side LANGUAGE_CODES values should win on conflict ("en" exists in
    # both operands; the registry's English class must be preserved).
    merged = {"yy": _Stub, "en": _Stub} | LANGUAGE_CODES
    assert type(merged) is dict
    assert merged["yy"] is _Stub
    assert merged["en"] is LANGUAGE_CODES["en"]


def test_repr_and_eq_behave_like_dict():
    assert repr(LANGUAGE_CODES) == repr(dict(LANGUAGE_CODES))
    assert LANGUAGE_CODES == dict(LANGUAGE_CODES)
    # __eq__ should return NotImplemented for non-dict comparisons so Python's
    # comparison protocol can fall back correctly.
    assert LANGUAGE_CODES.__eq__([]) is NotImplemented


def test_copy_returns_plain_dict():
    c = LANGUAGE_CODES.copy()
    assert isinstance(c, dict)
    assert type(c) is dict
    assert c == dict(LANGUAGE_CODES)


def test_contains_handles_non_string_key():
    # __contains__ must not raise on non-string keys.
    assert 123 not in LANGUAGE_CODES
    assert None not in LANGUAGE_CODES


def test_get_returns_default_for_missing():
    sentinel = object()
    assert LANGUAGE_CODES.get("xx", sentinel) is sentinel


def test_len_and_iteration_consistent_after_mutations(restore_language_codes):
    baseline_len = len(LANGUAGE_CODES)
    del LANGUAGE_CODES["en"]
    assert len(LANGUAGE_CODES) == baseline_len - 1
    LANGUAGE_CODES["zz"] = _Stub
    assert len(LANGUAGE_CODES) == baseline_len
    # values()/items() must reflect the same membership as iteration.
    iter_codes = list(LANGUAGE_CODES)
    assert "en" not in iter_codes
    assert "zz" in iter_codes
    assert len(LANGUAGE_CODES.values()) == len(iter_codes)
    assert [code for code, _ in LANGUAGE_CODES.items()] == iter_codes
