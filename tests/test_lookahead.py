import pytest

import sentencesplit
from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.segmenter import _DIGIT_LOOKAHEAD_STEM, _LANGUAGE_LOOKAHEAD_STEMS
from sentencesplit.utils import SegmentLookahead, TextSpan

_LOOKAHEAD_TEST_TOKENS = {
    "ar": "ا",
    "hy": "Ա",
    "ja": "あ",
    "zh": "甲",
}
_LOOKAHEAD_TEST_PUNCTUATION = ("។", "。", "؟", "։", "՜", "?", "!", "？", "！", ".")


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
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert seg.should_wait_for_more(text) is expected


def test_segment_with_lookahead_returns_segments_and_wait_state():
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)

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
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)

    result = seg.segment_with_lookahead(text)

    assert result.segments == expected_segments
    assert result.should_wait_for_more is expected_wait
    assert seg.should_wait_for_more(text) is expected_wait


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_lookahead_probes_are_normalized_for_supported_languages(language_code):
    seg = sentencesplit.Segmenter(language=language_code, clean=False, char_span=False)

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


def test_segment_with_lookahead_char_span_returns_textspans():
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=True)

    result = seg.segment_with_lookahead("Hello. The model is GPT 3.")

    assert all(isinstance(span, TextSpan) for span in result.segments)
    assert [span.sent for span in result.segments] == ["Hello. ", "The model is GPT 3."]
    assert result.should_wait_for_more is True


def test_segment_with_lookahead_handles_empty_and_none_inputs():
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)

    assert seg.segment_with_lookahead("") == SegmentLookahead([], should_wait_for_more=False)
    assert seg.segment_with_lookahead(None) == SegmentLookahead([], should_wait_for_more=False)


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
    seg = sentencesplit.Segmenter(language=language, clean=False, char_span=False)

    assert [s.strip() for s in seg.segment(text)] == expected


def test_should_wait_for_more_clean_mode_period_sentence():
    seg = sentencesplit.Segmenter(language="en", clean=True, char_span=False)

    assert seg.should_wait_for_more("This is the finale.") is False


def test_should_wait_for_more_pdf_mode_period_sentence():
    seg = sentencesplit.Segmenter(language="en", clean=True, doc_type="pdf", char_span=False)

    assert seg.should_wait_for_more("This is the finale.\n") is False


def _lookahead_sample_for_language(code, language_module):
    token = _LOOKAHEAD_TEST_TOKENS.get(code, "A")
    punct = next(
        (p for p in _LOOKAHEAD_TEST_PUNCTUATION if p in language_module.Punctuations), language_module.Punctuations[0]
    )
    return token, punct


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_segment_with_lookahead_across_all_languages(language_code):
    token, punct = _lookahead_sample_for_language(language_code, LANGUAGE_CODES[language_code])
    seg = sentencesplit.Segmenter(language=language_code, clean=False, char_span=False)

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
    token, punct = _lookahead_sample_for_language(language_code, LANGUAGE_CODES[language_code])
    text = f"{token}{punct} {token}{punct}"

    seg = sentencesplit.Segmenter(language=language_code, clean=False, char_span=False)
    assert "".join(seg.segment(text)) == text


@pytest.mark.parametrize("language_code", sorted(LANGUAGE_CODES))
def test_char_spans_tile_original_text_across_all_languages(language_code):
    """char_span output must contiguously tile the original text (no gaps,
    overlaps, or dropped characters) for every registered language."""
    token, punct = _lookahead_sample_for_language(language_code, LANGUAGE_CODES[language_code])
    text = f"{token}{punct} {token}{punct}"

    seg = sentencesplit.Segmenter(language=language_code, clean=False, char_span=True)
    spans = seg.segment(text)
    prev_end = 0
    for span in spans:
        assert span.start == prev_end
        assert text[span.start : span.end] == span.sent
        prev_end = span.end
    assert prev_end == len(text)
    assert "".join(s.sent for s in spans) == text
