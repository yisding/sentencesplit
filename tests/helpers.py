from __future__ import annotations

from collections.abc import Sequence

from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.utils import TextSpan


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
