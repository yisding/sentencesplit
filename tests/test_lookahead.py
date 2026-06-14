import pytest

import sentencesplit
from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.segmenter import _DIGIT_LOOKAHEAD_STEM, _LANGUAGE_LOOKAHEAD_STEMS, _strip_zero_width_before_sentence_closers
from sentencesplit.utils import ZERO_WIDTH_CHARS, SegmentLookahead
from tests.helpers import assert_span_contract, lookahead_sample_for_language, three_sentence_stream_sample


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The model is GPT 3.", True),
        ("The model is GPT 3. ", False),
        ("This is the finale.", False),
        ("This is the finale. ", False),
        ("Dr.", True),
        ("Dr. ", True),
        ("p.", True),
        ("p. ", True),
        ("What?", False),
        # Periods inside closing quotes are ambiguous under probing — the
        # between-punctuation logic absorbs the continuation, so the boundary
        # is unstable and we conservatively wait.
        ('He said "hello."', True),
        ('He said "Dr."', True),
        ("She said 'goodbye.'", True),
        ("End of section (see p.)", True),
    ],
)
def test_should_wait_for_more(text, expected):
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert seg.should_wait_for_more(text) is expected


def test_segment_with_lookahead_returns_segments_and_wait_state():
    seg = sentencesplit.Segmenter(language="en", clean=False)

    result = seg.segment_with_lookahead("The model is GPT 3.")

    assert result == SegmentLookahead(["The model is GPT 3."], should_wait_for_more=True)
    assert result.should_wait_for_more is True


@pytest.mark.parametrize(
    "text,expected_segments,expected_wait",
    [
        ("Hello. The model is GPT 3.", ["Hello. ", "The model is GPT 3."], True),
        ("Hello. The model is GPT 3. ", ["Hello. ", "The model is GPT 3. "], False),
        ("Hello. This is the finale.", ["Hello. ", "This is the finale."], False),
        ("Hello. Dr.", ["Hello. ", "Dr."], True),
        ("Hello. Dr. ", ["Hello. ", "Dr. "], True),
    ],
)
def test_segment_with_lookahead_tracks_only_last_segment(text, expected_segments, expected_wait):
    seg = sentencesplit.Segmenter(language="en", clean=False)

    result = seg.segment_with_lookahead(text)

    assert result.segments == expected_segments
    assert result.should_wait_for_more is expected_wait
    assert seg.should_wait_for_more(text) is expected_wait


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_lookahead_probes_are_normalized_for_supported_languages(language_code):
    seg = sentencesplit.Segmenter(language=language_code, clean=False)

    probes_no_space = seg._lookahead_probes_for_text("A.", 1, ".", has_trailing_whitespace=True)
    probes_with_space = seg._lookahead_probes_for_text("A.", 1, ".", has_trailing_whitespace=False)

    assert probes_no_space
    assert probes_with_space
    assert len(probes_no_space) == len(set(probes_no_space))
    assert len(probes_with_space) == len(set(probes_with_space))
    assert all(not probe.startswith(" ") for probe in probes_no_space)
    assert all(probe.startswith(" ") for probe in probes_with_space)
    assert _DIGIT_LOOKAHEAD_STEM in probes_no_space
    assert f" {_DIGIT_LOOKAHEAD_STEM}" in probes_with_space

    expected_language_stems = _LANGUAGE_LOOKAHEAD_STEMS.get(language_code, ("a", "A"))
    for stem in expected_language_stems:
        assert stem in probes_no_space
        assert f" {stem}" in probes_with_space


def test_segment_spans_with_lookahead_returns_textspans():
    seg = sentencesplit.Segmenter(language="en", clean=False)
    text = "Hello. The model is GPT 3."

    result = seg.segment_spans_with_lookahead(text)

    assert isinstance(result, SegmentLookahead)
    assert_span_contract(text, result.segments)
    assert [span.sent for span in result.segments] == ["Hello. ", "The model is GPT 3."]
    assert result.should_wait_for_more is True


def test_segment_with_lookahead_handles_empty_and_none_inputs():
    seg = sentencesplit.Segmenter(language="en", clean=False)

    assert seg.segment_with_lookahead("") == SegmentLookahead([], should_wait_for_more=False)
    assert seg.segment_with_lookahead(None) == SegmentLookahead([], should_wait_for_more=False)


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_segment_spans_with_lookahead_matches_separate_calls(language_code):
    """The single-pass combined API must equal calling the two APIs separately.

    ``segment_spans_with_lookahead`` derives both the spans and the
    ``should_wait_for_more`` verdict from one segmentation pass; it must be
    byte-for-byte identical to ``segment_spans`` + ``should_wait_for_more`` for
    every supported language (Latin, CJK, Cyrillic, Arabic, Indic, …).
    """
    seg = sentencesplit.Segmenter(language=language_code, clean=False)
    text = three_sentence_stream_sample(language_code)

    result = seg.segment_spans_with_lookahead(text)

    assert result.segments == seg.segment_spans(text)
    assert result.should_wait_for_more is seg.should_wait_for_more(text)
    # The spans must still tile the source exactly (non-destructive).
    assert_span_contract(text, result.segments)


def test_segment_spans_with_lookahead_empty_and_clean_guard():
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert seg.segment_spans_with_lookahead("") == SegmentLookahead([], should_wait_for_more=False)
    assert seg.segment_spans_with_lookahead(None) == SegmentLookahead([], should_wait_for_more=False)

    spans = seg.segment_spans_with_lookahead("Hello. The model is GPT 3.").segments
    assert [s.sent for s in spans] == ["Hello. ", "The model is GPT 3."]

    seg_clean = sentencesplit.Segmenter(language="en", clean=True)
    with pytest.raises(sentencesplit.exceptions.InvalidConfigurationError):
        seg_clean.segment_spans_with_lookahead("Hello world.")


def test_segment_with_lookahead_ignores_zero_width_only_input():
    seg = sentencesplit.Segmenter(language="en", clean=False)

    assert seg.segment_with_lookahead("\u200b") == SegmentLookahead([], should_wait_for_more=False)
    assert seg.should_wait_for_more("\u200b") is False


@pytest.mark.parametrize("zero_width", ZERO_WIDTH_CHARS)
def test_boundary_zero_width_after_stable_period_does_not_wait(zero_width):
    seg = sentencesplit.Segmenter(language="en", clean=False)
    text = f"This is the finale.{zero_width}"

    assert seg.segment_with_lookahead(text) == SegmentLookahead(["This is the finale."], should_wait_for_more=False)
    assert seg.segment(text) == ["This is the finale."]
    assert_span_contract(text, seg.segment_spans(text))


@pytest.mark.parametrize("zero_width", ZERO_WIDTH_CHARS)
def test_boundary_zero_width_after_abbreviation_still_waits(zero_width):
    seg = sentencesplit.Segmenter(language="en", clean=False)
    text = f"Dr.{zero_width}"

    assert seg.segment_with_lookahead(text) == SegmentLookahead(["Dr."], should_wait_for_more=True)
    assert seg.should_wait_for_more(text) is True
    assert_span_contract(text, seg.segment_spans(text))


@pytest.mark.parametrize(
    "text,expected",
    [
        ('What?\u200b"', ['What?"']),
        ("He asked (what?\u200b)", ["He asked (what?)"]),
    ],
)
def test_boundary_zero_width_before_sentence_closers(text, expected):
    seg = sentencesplit.Segmenter(language="en", clean=False)

    assert seg.segment_with_lookahead(text) == SegmentLookahead(expected, should_wait_for_more=False)
    assert seg.segment(text) == expected
    assert seg.should_wait_for_more(text) is False
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)
    assert [span.sent for span in spans] == [text]


def test_boundary_zero_width_before_sentence_closers_is_linear():
    class CountingStr(str):
        def __new__(cls, value):
            instance = super().__new__(cls, value)
            instance.getitem_calls = 0
            return instance

        def __getitem__(self, key):
            self.getitem_calls += 1
            return super().__getitem__(key)

    text = CountingStr("?" + "\u200b" * 2000 + '"')

    assert _strip_zero_width_before_sentence_closers(text, {"?"}) == '?"'
    assert text.getitem_calls < len(text) * 4


@pytest.mark.parametrize(
    "language,text,expected",
    [
        ("en", 'He said "hello." Élodie left.', ['He said "hello."', "Élodie left."]),
        ("fr", 'Il a dit "bonjour." Élodie est partie.', ['Il a dit "bonjour."', "Élodie est partie."]),
        ("fr", "Il est parti (vraiment.) Élodie reste.", ["Il est parti (vraiment.)", "Élodie reste."]),
        ("en", "She earned a Ph.D. Élodie congratulated her.", ["She earned a Ph.D.", "Élodie congratulated her."]),
        ("en", "I left at 6 p.m. Élodie arrived.", ["I left at 6 p.m.", "Élodie arrived."]),
    ],
)
def test_non_ascii_uppercase_sentence_starters_split_correctly(language, text, expected):
    seg = sentencesplit.Segmenter(language=language, clean=False)

    assert [s.strip() for s in seg.segment(text)] == expected


def test_should_wait_for_more_clean_mode_period_sentence():
    seg = sentencesplit.Segmenter(language="en", clean=True)

    assert seg.should_wait_for_more("This is the finale.") is False


def test_should_wait_for_more_pdf_mode_period_sentence():
    seg = sentencesplit.Segmenter(language="en", clean=True, doc_type="pdf")

    assert seg.should_wait_for_more("This is the finale.\n") is False


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_segment_with_lookahead_across_all_languages(language_code):
    token, punct = lookahead_sample_for_language(language_code)
    seg = sentencesplit.Segmenter(language=language_code, clean=False)

    closed_text = token + punct
    closed_result = seg.segment_with_lookahead(closed_text)
    assert closed_result.segments == seg.segment(closed_text)
    assert closed_result.should_wait_for_more is False

    incomplete_text = token
    incomplete_result = seg.segment_with_lookahead(incomplete_text)
    assert incomplete_result.segments == seg.segment(incomplete_text)
    assert incomplete_result.should_wait_for_more is True

    mixed_text = f"{token}{punct} {token}"
    mixed_result = seg.segment_with_lookahead(mixed_text)
    assert mixed_result.segments == seg.segment(mixed_text)
    assert mixed_result.should_wait_for_more is True


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_segmentation_is_nondestructive_across_all_languages(language_code):
    """clean=False segmentation must reproduce the original text exactly for a
    script-appropriate sample in every registered language."""
    token, punct = lookahead_sample_for_language(language_code)
    text = f"{token}{punct} {token}{punct}"

    seg = sentencesplit.Segmenter(language=language_code, clean=False)
    assert "".join(seg.segment(text)) == text


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_segment_spans_tile_original_text_across_all_languages(language_code):
    """segment_spans() output must contiguously tile the original text (no gaps,
    overlaps, or dropped characters) for every registered language."""
    token, punct = lookahead_sample_for_language(language_code)
    text = f"{token}{punct} {token}{punct}"

    seg = sentencesplit.Segmenter(language=language_code, clean=False)
    spans = seg.segment_spans(text)
    assert_span_contract(text, spans)
