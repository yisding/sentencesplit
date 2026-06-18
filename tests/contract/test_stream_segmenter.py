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
from tests.helpers import (
    assert_span_contract,
    stream_sample_for_language,
    three_sentence_stream_sample,
    two_sentence_stream_sample,
)


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


def test_boundary_zero_width_after_stable_period_emits():
    stream = StreamSegmenter(language="en")

    stream.feed("This is the finale.\u200b")

    assert stream.get_completed_sentences() == ["This is the finale."]
    assert stream.pending_text() == ""


def test_boundary_zero_width_before_sentence_closer_emits():
    stream = StreamSegmenter(language="en")

    stream.feed('What?\u200b"')

    assert stream.get_completed_sentences() == ['What?"']
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
    full = "Hello. World here. "
    assert_span_contract(full, spans)
    assert [s.sent for s in spans] == ["Hello. ", "World here. "]


def test_char_span_offsets_match_segment_spans():
    text = "My name is Jonas E. Smith. Please turn to p. 55. Done. "
    stream = StreamSegmenter(language="en", char_span=True)
    stream.feed(text)
    spans = stream.get_completed_sentences() + stream.flush()
    expected = sentencesplit.Segmenter(language="en").segment_spans(text)
    assert spans == expected


def test_clean_true_disallows_char_span():
    with pytest.raises(ValueError):
        StreamSegmenter(language="en", clean=True, char_span=True)


def test_clean_true_is_not_supported():
    with pytest.raises(ValueError, match="does not support clean=True"):
        StreamSegmenter(language="en", clean=True)


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


@pytest.mark.parametrize("max_buffer_size", [0, -1])
def test_invalid_max_buffer_size_raises(max_buffer_size):
    with pytest.raises(ValueError, match="max_buffer_size must be a positive integer or None"):
        StreamSegmenter(language="en", max_buffer_size=max_buffer_size)


def test_feed_returns_none_when_no_max_buffer_size():
    stream = StreamSegmenter(language="en")
    assert stream.feed("Hello. ") is None


# --------------------------------------------------------------------------- #
# Buffer compaction: persistent base offset (regression for the overflow span
# corruption + the O(n^2) re-segmentation cost)
# --------------------------------------------------------------------------- #


def test_char_span_offsets_survive_max_buffer_overflow():
    # Regression: on max_buffer_size overflow the buffer was reset to "" and the
    # base offset to 0, so spans emitted *after* an overflow restarted at 0,
    # producing back-jumping/overlapping offsets where full[start:end] != sent.
    # A persistent base offset must keep every span a faithful, monotonic slice
    # of the whole stream.
    stream = StreamSegmenter(language="en", char_span=True, max_buffer_size=15)
    full = ""
    emitted = []
    for chunk in ["aaaaaaaaaaaaaaaaaaaaa", "Hi. ", "Bye. "]:
        full += chunk
        forced = stream.feed(chunk)
        if forced:
            emitted.extend(forced)
        emitted.extend(stream.get_completed_sentences())
    emitted.extend(stream.flush())
    assert_span_contract(full, emitted)


def test_overflow_does_not_drop_or_duplicate_text():
    # The compaction overflow path must still surface every previously-completed
    # sentence plus the forced tail, losing and duplicating nothing.
    stream = StreamSegmenter(language="en", max_buffer_size=15)
    full = ""
    collected = []
    for chunk in ["Short one. ", "now a very long unterminated tail keeps coming and coming"]:
        full += chunk
        forced = stream.feed(chunk)
        if forced:
            collected.extend(forced)
        collected.extend(stream.get_completed_sentences())
    collected.extend(stream.flush())
    assert "".join(collected) == full


@pytest.mark.perf
def test_per_token_cost_is_flat_not_quadratic():
    # Regression: feed() re-segmented the entire growing buffer every call, so
    # per-token cost doubled as the stream doubled (O(n^2) total). Compaction
    # bounds re-segmentation to the unstable tail, so per-token cost stays flat.
    import time

    def per_token_cost(n_tokens):
        stream = StreamSegmenter(language="en")
        tokens = [f"Word{i} thing here. " for i in range(n_tokens)]
        start = time.perf_counter()
        for token in tokens:
            stream.feed(token)
            stream.get_completed_sentences()
            stream.is_complete()  # the natural poll loop must not re-segment
        return (time.perf_counter() - start) / n_tokens

    small = per_token_cost(200)
    large = per_token_cost(800)
    # 4x the tokens. Quadratic per-token cost would scale ~4x; a flat cost stays
    # near 1x. A generous 2.5x bound catches the O(n^2) regression while
    # tolerating timing noise on a busy CI box.
    assert large < small * 2.5, f"per-token cost grew {large / small:.1f}x (4x tokens) — looks quadratic"


def test_is_complete_does_not_change_emission():
    # is_complete() now reuses the cached stability verdict instead of
    # re-segmenting. Polling it between feeds must not perturb what gets emitted.
    text = "First sentence. Second sentence. Third trails off"
    polled = StreamSegmenter(language="en")
    quiet = StreamSegmenter(language="en")
    collected_polled, collected_quiet = [], []
    for chunk in ["First sen", "tence. Sec", "ond sentence. Thi", "rd trails off"]:
        polled.feed(chunk)
        polled.is_complete()
        polled.pending_text()
        collected_polled.extend(polled.get_completed_sentences())
        quiet.feed(chunk)
        collected_quiet.extend(quiet.get_completed_sentences())
    collected_polled.extend(polled.flush())
    collected_quiet.extend(quiet.flush())
    assert collected_polled == collected_quiet
    assert "".join(collected_polled) == text


def test_compaction_preserves_streaming_equals_non_streaming():
    # Compaction must not change emission vs the non-streaming segmenter. With a
    # whole-text feed (the contractual exact-equality case) the segments must
    # match, and confirmed boundaries must have streamed out incrementally (so
    # compaction really fired) rather than all appearing at flush.
    texts = [
        "Hello. The model is GPT 3.1 is fast. Goodbye.",
        "Dr. Smith went to Washington. He arrived at 3 p.m. yesterday.",
        "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten.",
        'He said "hello." Then she left. And finally it ended.',
    ]
    for text in texts:
        stream = StreamSegmenter(language="en")
        stream.feed(text)
        pre_flush = stream.get_completed_sentences()
        streamed = pre_flush + stream.flush()
        assert streamed == sentencesplit.Segmenter(language="en").segment(text)
        # Interior boundaries confirmed before flush -> compaction had something
        # to drop, proving the flat-cost path is exercised on real input.
        assert pre_flush, f"no interior boundary streamed before flush for {text!r}"


def test_compaction_chunked_feed_loses_nothing():
    # Across small chunked feeds (which can dribble a stray trailing space as its
    # own emission — pre-existing, documented behavior), compaction must still
    # neither lose nor duplicate text: the concatenation reproduces the source.
    texts = [
        "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten.",
        "Dr. Smith went to Washington. He arrived at 3 p.m. yesterday. Done.",
    ]
    for text in texts:
        stream = StreamSegmenter(language="en")
        collected = []
        for i in range(0, len(text), 7):
            stream.feed(text[i : i + 7])
            collected.extend(stream.get_completed_sentences())
        collected.extend(stream.flush())
        assert "".join(collected) == text


# --------------------------------------------------------------------------- #
# Per-language coverage
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_streaming_equals_non_streaming_across_all_languages(language_code):
    text = three_sentence_stream_sample(language_code)
    stream = StreamSegmenter(language=language_code)
    stream.feed(text)
    streamed = stream.get_completed_sentences() + stream.flush()
    assert streamed == sentencesplit.Segmenter(language=language_code).segment(text)


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_streaming_char_by_char_across_all_languages(language_code):
    text = two_sentence_stream_sample(language_code)
    stream = StreamSegmenter(language=language_code)
    collected = []
    _feed_char_by_char(stream, text)
    collected.extend(stream.get_completed_sentences())
    collected.extend(stream.flush())
    assert "".join(collected) == text


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_streaming_is_nondestructive_across_all_languages(language_code):
    text = two_sentence_stream_sample(language_code)
    stream = StreamSegmenter(language=language_code, char_span=True)
    stream.feed(text)
    spans = stream.get_completed_sentences() + stream.flush()
    assert_span_contract(text, spans)


# A representative set of Latin-script languages that segment on the native
# period. The per-language samples for these MUST split on a real '.' terminal
# (not collapse onto the CJK full stop), so streaming exercises the native
# Latin '.' boundary + lookahead probe rather than only the CJK path.
_LATIN_PERIOD_LANGUAGES = ("en", "de", "es", "fr", "nl", "ru", "it")


@pytest.mark.parametrize("language_code", _LATIN_PERIOD_LANGUAGES)
def test_latin_languages_stream_on_native_period(language_code):
    token, punct = stream_sample_for_language(language_code)
    # Regression guard for the historical bug where '。' (also present in these
    # languages' Punctuations) was chosen ahead of '.', so the sample never
    # reached the native period terminal.
    assert token is None
    assert punct == "."
    text = three_sentence_stream_sample(language_code)
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


def test_detect_segments_buffer_once_per_delta(monkeypatch):
    """Each feed() must segment the buffer once, not twice.

    ``_detect`` needs both the tail spans and the trailing-boundary lookahead
    verdict. It computes them in a single ``segment_spans_with_lookahead`` pass;
    regressing to separate ``segment_spans`` + ``should_wait_for_more`` calls
    would re-run the whole-buffer ``_match_spans`` mapping twice per delta. Guard
    that by counting ``_match_spans`` invocations: a delta whose tail ends in a
    non-period terminator does no tail probing, so exactly one mapping runs.
    """
    from sentencesplit.segmenter import Segmenter

    calls = {"n": 0}
    original = Segmenter._match_spans

    def counting(self, processed_sents, original_text):
        calls["n"] += 1
        return original(self, processed_sents, original_text)

    monkeypatch.setattr(Segmenter, "_match_spans", counting)

    stream = StreamSegmenter(language="en")
    # Ends in '?', a structurally-unambiguous terminator: no lookahead probing,
    # so the only whole-buffer span mapping is the single combined pass.
    calls["n"] = 0
    stream.feed("Are you sure?")
    assert calls["n"] == 1, calls["n"]


def test_exported_from_package():
    assert sentencesplit.StreamSegmenter is StreamSegmenter
    # N1's list_languages must remain exported alongside the new symbol.
    assert hasattr(sentencesplit, "list_languages")
