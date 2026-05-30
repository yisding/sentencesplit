"""Tests for the first-class streaming wrapper, StreamSegmenter.

StreamSegmenter is additive: it wraps the already-tested
segment_with_lookahead() / should_wait_for_more() primitives and must never
change segment() output. The cornerstone contract is that streaming equals
non-streaming: feeding the whole text in one delta and then flush()-ing yields
exactly Segmenter.segment(full).
"""

from __future__ import annotations

import pytest

import sentencesplit
from sentencesplit import StreamSegmenter
from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.utils import TextSpan

# Script-appropriate (token, terminal-punctuation) samples, mirroring the
# helpers in tests/test_segmenter.py so the per-language streaming tests run on
# input every language's boundary regex actually recognizes.
#
# Languages that segment on the Latin period must exercise that native '.'
# terminal (and its lookahead probe), not collapse onto the CJK full stop just
# because '。' also appears in their Punctuations list. So script-token
# languages (CJK / non-Latin scripts where a Latin '.' is not a real boundary)
# keep a native-terminal preference, while every other (Latin-script) language
# is steered to a real '.'-terminated word sample.
_LOOKAHEAD_TEST_TOKENS = {
    "ar": "ا",
    "hy": "Ա",
    "ja": "あ",
    "zh": "甲",
}
# Latin period first: Latin-script languages should exercise the native '.'
# boundary; the CJK / script terminals are only fallbacks for languages that
# do not segment on a Latin period.
_LATIN_FIRST_PUNCTUATION = (".", "？", "！", "。", "។", "؟", "։", "՜", "?", "!")
# Native-terminal preference for the script-token languages above, where a
# Latin '.' between native-script tokens is not a sentence boundary.
_SCRIPT_TERMINAL_PUNCTUATION = ("។", "。", "？", "！", "؟", "։", "՜", "?", "!", ".")
# Distinct multi-letter words so the sample splits on its terminal rather than
# being swallowed by the single-initial abbreviation heuristic ("A." -> initial).
_LATIN_SAMPLE_WORDS = ("Foo", "Bar", "Baz")


def _sample_for_language(code):
    """Return ``(token, punct)`` for a language.

    ``token`` is ``None`` for Latin-script languages (build the sample from
    distinct words via :func:`_three_sentence_sample`); otherwise it is the
    native-script repeat token. ``punct`` is a terminal the language's boundary
    regex actually recognizes, preferring the native Latin '.' for Latin scripts
    so streaming exercises that real terminal + lookahead path.
    """
    language_module = LANGUAGE_CODES[code]
    token = _LOOKAHEAD_TEST_TOKENS.get(code)
    if token is None:
        punct = next(
            (p for p in _LATIN_FIRST_PUNCTUATION if p in language_module.Punctuations),
            language_module.Punctuations[0],
        )
        return None, punct
    punct = next(
        (p for p in _SCRIPT_TERMINAL_PUNCTUATION if p in language_module.Punctuations),
        language_module.Punctuations[0],
    )
    return token, punct


def _two_sentence_sample(code):
    """Two terminal-separated sentences plus an unterminated tail token."""
    token, punct = _sample_for_language(code)
    if token is None:
        a, b, _ = _LATIN_SAMPLE_WORDS
        return f"{a}{punct} {b}{punct}"
    return f"{token}{token}{punct} {token}{token}{punct}"


def _three_sentence_sample(code):
    """Three sentences: two terminal-separated, then an unterminated tail."""
    token, punct = _sample_for_language(code)
    if token is None:
        a, b, c = _LATIN_SAMPLE_WORDS
        return f"{a}{punct} {b}{punct} {c}"
    return f"{token}{token}{punct} {token}{token}{punct} {token}{token}"


def _feed_char_by_char(stream, text):
    for ch in text:
        stream.feed(ch)


# --------------------------------------------------------------------------- #
# Core contract: streaming == non-streaming
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        "Hello. The model is GPT 3.1 is fast. Goodbye.",
        "Dr. Smith went to Washington. He arrived at 3 p.m. yesterday.",
        "One. Two. Three. Four.",
        "No terminal punctuation here",
        "Single.",
        'He said "hello." Then she left.',
    ],
)
def test_feed_full_then_flush_equals_segment(text):
    stream = StreamSegmenter(language="en")
    stream.feed(text)
    streamed = stream.get_completed_sentences() + stream.flush()
    assert streamed == sentencesplit.Segmenter(language="en").segment(text)


@pytest.mark.parametrize(
    "text",
    [
        "Hello. The model is GPT 3.1 is fast. Goodbye.",
        "Dr. Smith went to Washington. He arrived at 3 p.m. yesterday.",
        "One. Two. Three. Four.",
        "No terminal punctuation here",
    ],
)
def test_char_by_char_then_flush_preserves_text(text):
    # Char-by-char is the pathological case: a trailing space can arrive in its
    # own delta after a stable period, so an interior whitespace may dribble out
    # as its own emission. Exact segment()-equality is only contractual for
    # whole/realistic-chunk feeds (covered above); char-by-char must still lose
    # and duplicate nothing.
    stream = StreamSegmenter(language="en")
    collected = []
    _feed_char_by_char(stream, text)
    collected.extend(stream.get_completed_sentences())
    collected.extend(stream.flush())
    assert "".join(collected) == text


def test_streaming_preserves_text_no_duplication_no_loss():
    text = "First sentence. Second sentence. Third one trails off"
    stream = StreamSegmenter(language="en")
    collected = []
    pre_flush_emissions = 0
    for chunk in ["First sen", "tence. Sec", "ond sentence. Thi", "rd one trails off"]:
        stream.feed(chunk)
        newly = stream.get_completed_sentences()
        pre_flush_emissions += len(newly)
        collected.extend(newly)
    # Streaming property: completed sentences are emitted incrementally as their
    # boundaries become stable, BEFORE end-of-stream — a buffer-everything-until-
    # flush implementation would emit zero here and still pass the join check.
    assert pre_flush_emissions >= 2
    assert collected == ["First sentence. ", "Second sentence. "]
    collected.extend(stream.flush())
    # No duplication, no dropped text: concatenation reproduces the source.
    assert "".join(collected) == text


# --------------------------------------------------------------------------- #
# Emission timing / lookahead-driven buffering
# --------------------------------------------------------------------------- #


def test_abbreviation_delays_emission_conservative():
    stream = StreamSegmenter(language="en", buffering_mode="conservative")
    stream.feed("Hello. Dr.")
    # "Hello. " is a confirmed (interior) boundary; "Dr." is an unstable tail —
    # lookahead waits because a capital could follow — so it is held.
    assert stream.get_completed_sentences() == ["Hello. "]
    assert stream.pending_text() == "Dr."
    # A capital continuation resolves the abbreviation into one sentence rather
    # than splitting after "Dr.".
    stream.feed(" Smith arrived.")
    assert stream.get_completed_sentences() == ["Dr. Smith arrived."]
    assert stream.pending_text() == ""


def test_decimal_continuation_held_until_resolved():
    stream = StreamSegmenter(language="en", buffering_mode="conservative")
    stream.feed("The model is GPT 3.")
    # Ambiguous: could be "GPT 3." (end) or "GPT 3.1" (decimal) — hold it.
    assert stream.get_completed_sentences() == []
    assert stream.pending_text() == "The model is GPT 3."
    # Decimal continuation: still one sentence.
    stream.feed("1 is fast. ")
    assert stream.get_completed_sentences() == ["The model is GPT 3.1 is fast. "]


def test_decimal_vs_sentence_boundary():
    # "GPT 3. Next" is two sentences once a capital follows.
    stream = StreamSegmenter(language="en", buffering_mode="conservative")
    stream.feed("GPT 3. Next thing. ")
    assert stream.get_completed_sentences() == ["GPT 3. ", "Next thing. "]


def test_aggressive_emits_sooner_than_conservative():
    text = "The model is GPT 3."
    conservative = StreamSegmenter(language="en", buffering_mode="conservative")
    aggressive = StreamSegmenter(language="en", buffering_mode="aggressive")
    conservative.feed(text)
    aggressive.feed(text)
    # Conservative holds the ambiguous decimal tail; aggressive trusts the
    # terminal period and emits immediately.
    assert conservative.get_completed_sentences() == []
    assert aggressive.get_completed_sentences() == ["The model is GPT 3."]


def test_aggressive_and_conservative_agree_after_flush():
    text = "The model is GPT 3.1 is fast. Bye."
    for mode in ("conservative", "aggressive", "balanced"):
        stream = StreamSegmenter(language="en", buffering_mode=mode)
        stream.feed(text)
        out = stream.get_completed_sentences() + stream.flush()
        assert "".join(out) == text


# --------------------------------------------------------------------------- #
# State management
# --------------------------------------------------------------------------- #


def test_pending_text_tracks_unemitted_tail():
    stream = StreamSegmenter(language="en")
    stream.feed("One. Two")
    assert stream.get_completed_sentences() == ["One. "]
    assert stream.pending_text() == "Two"
    stream.feed(". ")
    assert stream.get_completed_sentences() == ["Two. "]
    assert stream.pending_text() == ""


def test_is_complete_reflects_tail_stability():
    stream = StreamSegmenter(language="en")
    assert stream.is_complete() is True  # empty buffer is trivially complete
    stream.feed("He is Dr.")
    # An abbreviation tail probes unstable (a capital could follow) -> not complete.
    assert stream.is_complete() is False
    stream.feed(" Smith arrived. ")
    assert stream.is_complete() is True


def test_flush_emits_stable_and_unstable_tail():
    stream = StreamSegmenter(language="en")
    stream.feed("Done. Trailing tail with no period")
    assert stream.get_completed_sentences() == ["Done. "]
    flushed = stream.flush()
    assert flushed == ["Trailing tail with no period"]
    # After flush the buffer is drained.
    assert stream.pending_text() == ""
    assert stream.get_completed_sentences() == []


def test_flush_then_feed_continues_cleanly():
    stream = StreamSegmenter(language="en")
    stream.feed("Partial tail")
    assert stream.flush() == ["Partial tail"]
    # Subsequent feeds start a fresh logical stream segment.
    stream.feed("New sentence. ")
    assert stream.get_completed_sentences() == ["New sentence. "]


def test_reset_clears_state():
    stream = StreamSegmenter(language="en")
    stream.feed("One. Two")
    stream.get_completed_sentences()
    stream.reset()
    assert stream.pending_text() == ""
    assert stream.get_completed_sentences() == []
    assert stream.is_complete() is True
    # Fully reusable after reset.
    stream.feed("Fresh. ")
    assert stream.get_completed_sentences() == ["Fresh. "]


def test_get_completed_sentences_is_drained_not_repeated():
    stream = StreamSegmenter(language="en")
    stream.feed("One. Two. Three")
    first = stream.get_completed_sentences()
    second = stream.get_completed_sentences()
    assert first == ["One. ", "Two. "]
    assert second == []  # already drained


# --------------------------------------------------------------------------- #
# char_span
# --------------------------------------------------------------------------- #


def test_char_span_returns_textspans_with_stream_offsets():
    stream = StreamSegmenter(language="en", char_span=True)
    stream.feed("Hello. ")
    stream.feed("World here. ")
    spans = stream.get_completed_sentences()
    assert all(isinstance(s, TextSpan) for s in spans)
    assert [s.sent for s in spans] == ["Hello. ", "World here. "]
    # Offsets are relative to the whole stream, contiguous and gap-free.
    assert spans[0].start == 0
    assert spans[0].end == spans[1].start
    full = "Hello. World here. "
    for s in spans:
        assert full[s.start : s.end] == s.sent


def test_char_span_offsets_match_segment_spans():
    text = "My name is Jonas E. Smith. Please turn to p. 55. Done. "
    stream = StreamSegmenter(language="en", char_span=True)
    stream.feed(text)
    spans = stream.get_completed_sentences() + stream.flush()
    expected = sentencesplit.Segmenter(language="en", char_span=True).segment(text)
    assert spans == expected


def test_clean_true_disallows_char_span():
    with pytest.raises(ValueError):
        StreamSegmenter(language="en", clean=True, char_span=True)


# --------------------------------------------------------------------------- #
# Edge cases
# --------------------------------------------------------------------------- #


def test_empty_and_none_and_whitespace_feeds():
    stream = StreamSegmenter(language="en")
    stream.feed("")
    stream.feed(None)
    assert stream.get_completed_sentences() == []
    assert stream.pending_text() == ""
    assert stream.is_complete() is True
    stream.feed("   ")
    # Whitespace-only buffer yields no completed sentences.
    assert stream.get_completed_sentences() == []


def test_flush_on_empty_stream_returns_empty():
    stream = StreamSegmenter(language="en")
    assert stream.flush() == []


def test_very_long_tail_without_boundary():
    stream = StreamSegmenter(language="en")
    tail = "word " * 5000
    stream.feed(tail)
    # No boundary anywhere -> nothing completed, everything pending.
    assert stream.get_completed_sentences() == []
    assert stream.pending_text() == tail
    assert stream.flush() == [tail]


def test_max_buffer_size_force_flushes_pending():
    stream = StreamSegmenter(language="en", max_buffer_size=20)
    forced = stream.feed("a" * 50)
    # Overflow forces the pending tail out so the buffer cannot grow unbounded.
    assert forced  # feed returns the force-flushed sentences on overflow
    assert len(stream.pending_text()) <= 20


def test_feed_returns_none_when_no_max_buffer_size():
    stream = StreamSegmenter(language="en")
    assert stream.feed("Hello. ") is None


# --------------------------------------------------------------------------- #
# Per-language coverage
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_streaming_equals_non_streaming_across_all_languages(language_code):
    text = _three_sentence_sample(language_code)
    stream = StreamSegmenter(language=language_code)
    stream.feed(text)
    streamed = stream.get_completed_sentences() + stream.flush()
    assert streamed == sentencesplit.Segmenter(language=language_code).segment(text)


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_streaming_char_by_char_across_all_languages(language_code):
    text = _two_sentence_sample(language_code)
    stream = StreamSegmenter(language=language_code)
    collected = []
    _feed_char_by_char(stream, text)
    collected.extend(stream.get_completed_sentences())
    collected.extend(stream.flush())
    assert "".join(collected) == text


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_streaming_is_nondestructive_across_all_languages(language_code):
    text = _two_sentence_sample(language_code)
    stream = StreamSegmenter(language=language_code, char_span=True)
    stream.feed(text)
    spans = stream.get_completed_sentences() + stream.flush()
    prev_end = 0
    for span in spans:
        assert span.start == prev_end
        assert text[span.start : span.end] == span.sent
        prev_end = span.end
    assert prev_end == len(text)
    assert "".join(s.sent for s in spans) == text


# A representative set of Latin-script languages that segment on the native
# period. The per-language samples for these MUST split on a real '.' terminal
# (not collapse onto the CJK full stop), so streaming exercises the native
# Latin '.' boundary + lookahead probe rather than only the CJK path.
_LATIN_PERIOD_LANGUAGES = ("en", "de", "es", "fr", "nl", "ru", "it")


@pytest.mark.parametrize("language_code", _LATIN_PERIOD_LANGUAGES)
def test_latin_languages_stream_on_native_period(language_code):
    token, punct = _sample_for_language(language_code)
    # Regression guard for the historical bug where '。' (also present in these
    # languages' Punctuations) was chosen ahead of '.', so the sample never
    # reached the native period terminal.
    assert token is None
    assert punct == "."
    text = _three_sentence_sample(language_code)
    assert "。" not in text and "." in text
    stream = StreamSegmenter(language=language_code)
    stream.feed(text)
    completed = stream.get_completed_sentences()
    # The two '.'-terminated leading sentences are confirmed (interior)
    # boundaries and must stream out before flush; the unterminated tail waits.
    assert completed, f"{language_code} streamed nothing before flush on a native '.' sample"
    assert all(s.rstrip().endswith(".") for s in completed)
    streamed = completed + stream.flush()
    assert streamed == sentencesplit.Segmenter(language=language_code).segment(text)


# --------------------------------------------------------------------------- #
# Constructor / config
# --------------------------------------------------------------------------- #


def test_invalid_buffering_mode_raises():
    with pytest.raises(ValueError):
        StreamSegmenter(language="en", buffering_mode="nonsense")


def test_invalid_split_mode_raises():
    # Same constraint surface as Segmenter: invalid split_mode rejected.
    with pytest.raises(ValueError):
        StreamSegmenter(language="en", split_mode="nonsense")


def test_split_mode_changes_streamed_output():
    # A valid split_mode must actually reach Segmenter and change the streamed
    # result, not merely be validated. "Hello... World." is an ambiguous
    # ellipsis boundary: conservative keeps it as one sentence, aggressive
    # splits after the ellipsis. The two modes must diverge end-to-end.
    text = "Hello... World."

    conservative = StreamSegmenter(language="en", split_mode="conservative")
    conservative.feed(text)
    conservative_out = conservative.get_completed_sentences() + conservative.flush()

    aggressive = StreamSegmenter(language="en", split_mode="aggressive")
    aggressive.feed(text)
    aggressive_out = aggressive.get_completed_sentences() + aggressive.flush()

    assert conservative_out == ["Hello... World."]
    assert aggressive_out == ["Hello... ", "World."]
    assert conservative_out != aggressive_out
    # And each still matches its own non-streaming Segmenter (contract holds per
    # mode, so the divergence is the segmenter's, not a streaming artifact).
    assert conservative_out == sentencesplit.Segmenter(language="en", split_mode="conservative").segment(text)
    assert aggressive_out == sentencesplit.Segmenter(language="en", split_mode="aggressive").segment(text)


def test_exported_from_package():
    assert sentencesplit.StreamSegmenter is StreamSegmenter
    # N1's list_languages must remain exported alongside the new symbol.
    assert hasattr(sentencesplit, "list_languages")
