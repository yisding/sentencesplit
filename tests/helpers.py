from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.utils import TextSpan

if TYPE_CHECKING:  # pragma: no cover - typing only
    from hypothesis import strategies as st


def assert_segments(segmenter, text: str, expected: Sequence[str], *, strip: bool = True) -> None:
    segments = segmenter.segment(text)
    if strip:
        segments = [segment.strip() for segment in segments]
    assert segments == expected


def assert_span_contract(text: str, spans: Sequence[TextSpan]) -> None:
    for span in spans:
        assert isinstance(span, TextSpan)
        assert text[span.start : span.end] == span.sent

    if not spans:
        assert text == ""
        return

    for span in spans:
        assert 0 <= span.start < span.end <= len(text)

    assert spans[0].start == 0
    assert spans[-1].end == len(text)

    prev_end = 0
    for span in spans:
        assert span.start == prev_end
        prev_end = span.end

    assert "".join(span.sent for span in spans) == text


_LOOKAHEAD_TEST_TOKENS = {
    "ar": "ا",
    "hy": "Ա",
    "ja": "あ",
    "zh": "甲",
}
_LOOKAHEAD_TEST_PUNCTUATION = ("។", "。", "؟", "։", "՜", "?", "!", "？", "！", ".")

# Latin-script languages should exercise their native "." boundary first. Some
# language profiles also include CJK punctuation, but using that for Latin tests
# misses the period-specific lookahead path.
_LATIN_FIRST_PUNCTUATION = (".", "？", "！", "。", "។", "؟", "։", "՜", "?", "!")
_SCRIPT_TERMINAL_PUNCTUATION = ("។", "。", "？", "！", "؟", "։", "՜", "?", "!", ".")
_LATIN_SAMPLE_WORDS = ("Foo", "Bar", "Baz")


def lookahead_sample_for_language(code: str) -> tuple[str, str]:
    language_module = LANGUAGE_CODES[code]
    token = _LOOKAHEAD_TEST_TOKENS.get(code, "A")
    punct = next(
        (punctuation for punctuation in _LOOKAHEAD_TEST_PUNCTUATION if punctuation in language_module.Punctuations),
        language_module.Punctuations[0],
    )
    return token, punct


def stream_sample_for_language(code: str) -> tuple[str | None, str]:
    """Return ``(token, punctuation)`` for language-wide streaming tests.

    ``token`` is ``None`` for Latin-script languages, which should build samples
    from multi-letter Latin words so the single-initial abbreviation heuristic
    does not swallow ``A.``-style test input.
    """
    language_module = LANGUAGE_CODES[code]
    token = _LOOKAHEAD_TEST_TOKENS.get(code)
    if token is None:
        punct = next(
            (punctuation for punctuation in _LATIN_FIRST_PUNCTUATION if punctuation in language_module.Punctuations),
            language_module.Punctuations[0],
        )
        return None, punct

    punct = next(
        (punctuation for punctuation in _SCRIPT_TERMINAL_PUNCTUATION if punctuation in language_module.Punctuations),
        language_module.Punctuations[0],
    )
    return token, punct


def two_sentence_stream_sample(code: str) -> str:
    token, punct = stream_sample_for_language(code)
    if token is None:
        first, second, _ = _LATIN_SAMPLE_WORDS
        return f"{first}{punct} {second}{punct}"
    return f"{token}{token}{punct} {token}{token}{punct}"


def three_sentence_stream_sample(code: str) -> str:
    token, punct = stream_sample_for_language(code)
    if token is None:
        first, second, third = _LATIN_SAMPLE_WORDS
        return f"{first}{punct} {second}{punct} {third}"
    return f"{token}{token}{punct} {token}{token}{punct} {token}{token}"


# --------------------------------------------------------------------------- #
# Per-script Hypothesis input strategies (promoted from test_span_roundtrip).
#
# Shared by the span round-trip contract (``test_span_roundtrip.py``) and the
# core ``segment()`` property tests (``test_properties.py``). The constants and
# the pure-Python ``_alphabet_for`` / ``_terminals_for`` helpers carry no
# Hypothesis dependency; only ``text_strategy`` needs ``hypothesis.strategies``
# and imports it lazily, so ``tests/helpers.py`` stays importable in a
# zero-dependency (no-Hypothesis) environment.
# --------------------------------------------------------------------------- #

# Every registered code (24 languages + en_es_zh + en_legal). The language-
# agnostic contracts exercise the full registry as free safety.
ALL_CODES = sorted(LANGUAGE_CODES.keys())

# Dirty / format characters that survive str.strip() and have historically
# corrupted spans / boundaries if mishandled.
ZWSP = "​"  # zero-width space
ZWNJ = "‌"  # zero-width non-joiner
ZWJ = "‍"  # zero-width joiner
NBSP = " "  # no-break space
BOM = "﻿"  # byte-order mark / zero-width no-break space
COMBINING_ACUTE = "́"  # combining acute accent (decomposed 'a' tail)
RTL_OVERRIDE = "‮"  # right-to-left override (directional format)
LRM = "‎"  # left-to-right mark
RLM = "‏"  # right-to-left mark

DIRTY_CHARS = [ZWSP, ZWNJ, ZWJ, NBSP, BOM, COMBINING_ACUTE, RTL_OVERRIDE, LRM, RLM]

# Per-script alphabets used to build realistic generated inputs. Languages not
# listed fall back to the Latin alphabet, which is harmless for these contracts.
_SCRIPT_ALPHABETS = {
    "ar": "مرحبا كيف حالك",
    "fa": "سلام چطوری دوست",
    "ur": "سلام کیا حال ہے",
    "zh": "你好世界甲乙丙",
    "ja": "こんにちはあいうえお漢字",
    "hi": "नमस्ते अच्छा है",
    "mr": "नमस्कार छान आहे",
    "el": "Αλφα βητα γαμμα δελτα",
    "ru": "Привет как дела",
    "bg": "Здравей как си",
    "kk": "Сәлем қалайсың",
    "hy": "Բարև ինչպես ես",
    "am": "ሰላም እንዴት ነህ",
    "my": "မင်္ဂလာပါ နေကောင်းလား",
    "en_es_zh": "Hola hello 你好 world mundo 世界",
}

# Script-appropriate terminal punctuation so generated text actually splits.
_SCRIPT_TERMINALS = {
    "ar": "؟ . ",
    "fa": "؟ . ",
    "ur": "۔ ؟ ",
    "zh": "。 ！ ？ ",
    "ja": "。 ！ ？ ",
    "hi": "। ! ? ",
    "mr": "। ! ? ",
    "el": ". ; ! ",
    "am": "። ! ? ",
    "my": "။ ၊ ? ",
    "hy": "։ ՜ ՞ ",
}


def _alphabet_for(code: str) -> str:
    return _SCRIPT_ALPHABETS.get(code, "Hello world the quick brown fox")


def _terminals_for(code: str) -> str:
    return _SCRIPT_TERMINALS.get(code, ". ! ? ")


def text_strategy(code: str) -> st.SearchStrategy[str]:
    """Build a per-language Hypothesis text strategy.

    Mixes script letters, script-appropriate terminals, whitespace, and the full
    dirty-character set into short strings (including the empty string and
    whitespace-only / dirty-only strings). ``hypothesis`` is imported lazily so
    this module stays importable without it.
    """
    from hypothesis import strategies as st

    pool = list(_alphabet_for(code)) + list(_terminals_for(code))
    pool += ["\n", "\t", " ", "  "]
    pool += DIRTY_CHARS
    # Repeat the terminal/whitespace tokens so boundaries are actually exercised.
    pool += [". ", "! ", "? ", "\n", " "]
    char_st = st.sampled_from(pool)
    return st.lists(char_st, min_size=0, max_size=24).map("".join)
