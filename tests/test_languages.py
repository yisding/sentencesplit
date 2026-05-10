from collections import Counter

import pytest

from sentencesplit.languages import LANGUAGE_CODES, Language

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
