"""Lock the Latin-uppercase Unicode contract against UCD drift.

The only Unicode-database-dependent branches in the library live in the
Latin-uppercase helper ``_is_latin_upper`` in ``sentencesplit.utils`` (it calls
``unicodedata.name`` to decide whether a non-ASCII uppercase character belongs to
the Latin script). Pin its Latin-vs-non-Latin behaviour so segmentation stays
deterministic across the Unicode database bundled with CPython 3.11-3.14:

- accented Latin uppercase (É, Ñ, Ä, Ö, Ç) must count as Latin-uppercase,
- non-Latin uppercase (Greek Α U+0391, Cyrillic Б U+0411) must not,
- lowercase (é, ñ) must not.
"""

import pytest

from sentencesplit.utils import _is_latin_upper


@pytest.mark.parametrize(
    "char",
    [
        "A",  # ASCII uppercase
        "É",  # U+00C9 LATIN CAPITAL LETTER E WITH ACUTE
        "Ñ",  # U+00D1 LATIN CAPITAL LETTER N WITH TILDE
        "Ä",  # U+00C4 LATIN CAPITAL LETTER A WITH DIAERESIS
        "Ö",  # U+00D6 LATIN CAPITAL LETTER O WITH DIAERESIS
        "Ç",  # U+00C7 LATIN CAPITAL LETTER C WITH CEDILLA
    ],
)
def test_latin_uppercase_is_true(char):
    assert _is_latin_upper(char) is True


@pytest.mark.parametrize(
    "char",
    [
        "Α",  # GREEK CAPITAL LETTER ALPHA (Α)
        "Б",  # CYRILLIC CAPITAL LETTER BE (Б)
    ],
)
def test_non_latin_uppercase_is_false(char):
    assert _is_latin_upper(char) is False


@pytest.mark.parametrize(
    "char",
    [
        "a",  # ASCII lowercase
        "é",  # U+00E9 LATIN SMALL LETTER E WITH ACUTE
        "ñ",  # U+00F1 LATIN SMALL LETTER N WITH TILDE
    ],
)
def test_lowercase_is_false(char):
    assert _is_latin_upper(char) is False


def test_empty_string_is_false():
    assert _is_latin_upper("") is False
