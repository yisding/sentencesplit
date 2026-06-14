from collections import Counter

import pytest

import sentencesplit
from sentencesplit.lang.common import Common, Standard, canonical_abbreviations
from sentencesplit.language_profile import LanguageProfile
from sentencesplit.languages import LANGUAGE_CODES, Language, list_languages, register_language, unregister_language


class _Stub:
    """Sentinel class used in mutation tests to stand in for a real language."""


class _DemoLanguageA(Common, Standard):
    iso_code = "zz"
    LATIN_UPPERCASE_RESPLIT = False


class _DemoLanguageB(Common, Standard):
    iso_code = "zz"
    LATIN_UPPERCASE_RESPLIT = True


# All registered languages should have duplicate-free, whitespace-trimmed
# abbreviation lists.
DEDUPED_ABBREVIATION_LANGUAGE_CODES = tuple(sorted(LANGUAGE_CODES))


def test_lang_code2instance_mapping():
    for code, language_module in LANGUAGE_CODES.items():
        assert Language.get_language_code(code) == language_module


def test_registered_language_iso_codes_match_registry_keys():
    for code, language_module in LANGUAGE_CODES.items():
        assert language_module.iso_code == code


def test_list_languages_returns_sorted_registry_codes():
    codes = list_languages()
    assert codes == sorted(LANGUAGE_CODES.keys())
    # Sorted, with no duplicates.
    assert codes == sorted(set(codes))
    # Built-ins and the special profiles are all discoverable.
    for expected in ("en", "es", "zh", "ja", "en_es_zh", "en_legal"):
        assert expected in codes


def test_list_languages_reflects_runtime_registration(restore_language_codes):
    LANGUAGE_CODES["zz"] = _Stub
    assert "zz" in list_languages()
    del LANGUAGE_CODES["en"]
    assert "en" not in list_languages()


def test_register_and_unregister_language_helpers_reflect_in_public_api(restore_language_codes):
    register_language("zz", _DemoLanguageA)

    assert Language.get_language_code("zz") is _DemoLanguageA
    assert "zz" in list_languages()
    assert sentencesplit.Segmenter(language="zz").language_module is _DemoLanguageA

    unregister_language("zz")

    assert "zz" not in list_languages()
    with pytest.raises(ValueError, match="Provide valid language ID"):
        Language.get_language_code("zz")


def test_register_language_override_uses_new_profile(restore_language_codes):
    register_language("zz", _DemoLanguageA)
    assert LanguageProfile.from_language(Language.get_language_code("zz")).latin_uppercase_resplit is False

    register_language("zz", _DemoLanguageB)

    assert Language.get_language_code("zz") is _DemoLanguageB
    assert LanguageProfile.from_language(Language.get_language_code("zz")).latin_uppercase_resplit is True


@pytest.mark.parametrize("code", DEDUPED_ABBREVIATION_LANGUAGE_CODES)
def test_language_abbreviations_do_not_repeat_literals(code):
    abbreviations = LANGUAGE_CODES[code].Abbreviation.ABBREVIATIONS
    counts = Counter(abbreviations)
    duplicates = sorted(abbreviation for abbreviation, count in counts.items() if count > 1)
    assert duplicates == []


@pytest.mark.parametrize("code", tuple(sorted(LANGUAGE_CODES)))
def test_language_abbreviations_are_whitespace_trimmed(code):
    """Abbreviation entries must not carry stray leading/trailing whitespace."""
    abbreviations = LANGUAGE_CODES[code].Abbreviation.ABBREVIATIONS
    untrimmed = sorted(a for a in abbreviations if a != a.strip())
    assert untrimmed == []


@pytest.mark.parametrize("code", tuple(sorted(LANGUAGE_CODES)))
def test_single_token_abbreviations_have_no_trailing_dot(code):
    """Single-token abbreviations must NOT be stored with a trailing dot.

    The Aho-Corasick automaton keys each abbreviation as ``<abbr>.`` (it appends a
    period; see ``abbreviation_replacer._AbbreviationData.__init__``). A single-token
    abbreviation stored WITH a trailing dot is therefore keyed ``<abbr>..`` and is
    never enumerated as a candidate by the period classifier — so its period is
    never protected via the main path. This is the exact rot mode the V2 cleanup
    closed; it must stay closed for every registered language (including future
    additions).

    Only single-token entries are checked: an entry with an INTERNAL dot
    (initialisms like ``s.r.o``, ``p.m.``) or any whitespace (multi-token entries
    like ``et al``, ``sp. z o.o``) is structural — handled by
    ``MULTI_PERIOD_ABBREVIATION_REGEX`` / ``classify_special``, not the automaton —
    and is intentionally left dotted/spaced.
    """
    abbreviations = LANGUAGE_CODES[code].Abbreviation.ABBREVIATIONS
    offenders = [
        a for a in abbreviations if (s := a.strip()).endswith(".") and s.count(".") == 1 and not any(c.isspace() for c in s)
    ]
    assert offenders == []


@pytest.mark.parametrize("code", tuple(sorted(LANGUAGE_CODES)))
def test_abbreviations_are_canonical_form(code):
    """Every ABBREVIATIONS list must be stored in its canonical form.

    The canonical form is ``sorted(set(...))`` over the lowercased entries (see
    ``sentencesplit.lang.common.canonical_abbreviations``): lowercased,
    de-duplicated, and sorted. Languages build their list THROUGH that helper, so
    this lint is the guard that a future hand-edited addition (a stray uppercase
    entry, an out-of-order or duplicate literal) is caught instead of silently
    rotting. Lowercasing is behavior-neutral for the V2 engine: the automaton keys
    on ``stripped.lower()``, ``match_re`` is ``re.IGNORECASE``, and the
    abbr/prepositive/number sets are all lowercased.
    """
    abbreviations = list(LANGUAGE_CODES[code].Abbreviation.ABBREVIATIONS)
    assert abbreviations == canonical_abbreviations(abbreviations)


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
