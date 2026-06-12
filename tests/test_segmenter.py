import pytest

import sentencesplit
from sentencesplit.utils import TextSpan


def test_list_languages_matches_module_level_function():
    from sentencesplit.languages import list_languages

    codes = sentencesplit.Segmenter.list_languages()
    assert codes == list_languages()
    # Callable on an instance too, and every listed code is constructible.
    seg = sentencesplit.Segmenter(language="en")
    assert seg.list_languages() == codes
    for expected in ("en", "zh", "en_es_zh", "en_legal"):
        assert expected in codes


def test_no_input(default_en_no_clean_no_span_fixture, text=""):
    segments = default_en_no_clean_no_span_fixture.segment(text)
    assert segments == []


def test_none_input(default_en_no_clean_no_span_fixture, text=None):
    segments = default_en_no_clean_no_span_fixture.segment(text)
    assert segments == []


def test_newline_input(default_en_no_clean_no_span_fixture, text="\n"):
    segments = default_en_no_clean_no_span_fixture.segment(text)
    assert segments == []


def test_segmenter_doesnt_mutate_input(
    default_en_no_clean_no_span_fixture, text="My name is Jonas E. Smith. Please turn to p. 55."
):
    segments = default_en_no_clean_no_span_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert text == "My name is Jonas E. Smith. Please turn to p. 55."


def test_segment_spans_helper_returns_textspans(text="My name is Jonas E. Smith. Please turn to p. 55."):
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    spans = seg.segment_spans(text)
    assert all(isinstance(span, TextSpan) for span in spans)
    assert text == "".join([seg_span.sent for seg_span in spans])


def test_segment_spans_is_canonical_and_ignores_char_span_flag():
    """segment_spans() is the canonical spans API: identical output whether the
    instance was built with char_span True or False. The char_span flag is
    deprecated but kept for back-compat — segment(char_span=True) must equal it."""
    text = "My name is Jonas E. Smith. Please turn to p. 55."
    plain_seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    span_seg = sentencesplit.Segmenter(language="en", clean=False, char_span=True)

    canonical = plain_seg.segment_spans(text)
    assert span_seg.segment_spans(text) == canonical
    # Back-compat: the deprecated char_span=True flag still yields the same spans.
    assert span_seg.segment(text) == canonical
    # Round-trip contract.
    assert "".join(s.sent for s in canonical) == text


def test_segment_spans_whitespace_only_input_roundtrips():
    """Regression: whitespace-only input used to return [] from segment_spans(),
    dropping the source bytes and breaking the round-trip. It must now tile the
    whole source (the trailing-remainder branch of _match_spans)."""
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    for text in ("\n", "   ", "\t\t", " \n "):
        spans = seg.segment_spans(text)
        assert "".join(s.sent for s in spans) == text
        assert spans and spans[0].start == 0 and spans[-1].end == len(text)
    # But the plain segment() path still drops whitespace-only content (no
    # phantom sentence), unchanged from prior behaviour.
    assert seg.segment("\n") == []


def test_no_clean_segment_preserves_leading_whitespace():
    text = "\n  Hello.  World."
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)

    segments = seg.segment(text)

    assert segments == ["\n  Hello.  ", "World."]
    assert "".join(segments) == text


def test_segment_spans_preserve_leading_whitespace():
    text = "\n  Hello.  World."
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)

    spans = seg.segment_spans(text)

    assert spans == [
        TextSpan("\n  Hello.  ", 0, 11),
        TextSpan("World.", 11, 17),
    ]
    assert "".join(span.sent for span in spans) == text


def test_segment_clean_helper_matches_clean_segmenter(text="This is the U.S. Senate my friends. <em>Yes.</em>"):
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    clean_seg = sentencesplit.Segmenter(language="en", clean=True, char_span=False)
    assert seg.segment_clean(text) == clean_seg.segment(text)


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "My name is Jonas E. Smith. Please turn to p. 55.",
            [
                ("My name is Jonas E. Smith. ", 0, 27),
                ("Please turn to p. 55.", 27, 48),
            ],
        )
    ],
)
def test_sbd_char_span(en_no_clean_with_span_fixture, text, expected):
    """Test sentences with character offsets"""
    segments = en_no_clean_with_span_fixture.segment(text)
    expected_text_spans = [TextSpan(sent_w_span[0], sent_w_span[1], sent_w_span[2]) for sent_w_span in expected]
    assert segments == expected_text_spans
    # clubbing sentences and matching with original text
    assert text == "".join([seg.sent for seg in segments])


def test_same_sentence_different_char_span(en_no_clean_with_span_fixture):
    """Test same sentences with different char offsets & check for non-destruction"""
    text = """From the AP comes this story :
President Bush on Tuesday nominated two individuals to replace retiring jurists on federal courts in the Washington area.
***
After you are elected in 2004, what will your memoirs say about you, what will the title be, and what will the main theme say?
***
"THE PRESIDENT: I appreciate that.
(Laughter.)
My life is too complicated right now trying to do my job.
(Laughter.)"""
    expected_text_spans = [
        TextSpan(sent="From the AP comes this story :\n", start=0, end=31),
        TextSpan(
            sent="President Bush on Tuesday nominated two individuals to replace retiring jurists on federal courts in the Washington area.\n",
            start=31,
            end=153,
        ),
        TextSpan(sent="***\n", start=153, end=157),
        TextSpan(
            sent="After you are elected in 2004, what will your memoirs say about you, what will the title be, and what will the main theme say?\n",
            start=157,
            end=284,
        ),
        TextSpan(sent="***\n", start=284, end=288),
        TextSpan(sent='"THE PRESIDENT: I appreciate that.\n', start=288, end=323),
        TextSpan(sent="(Laughter.)\n", start=323, end=335),
        TextSpan(sent="My life is too complicated right now trying to do my job.\n", start=335, end=393),
        TextSpan(sent="(Laughter.)", start=393, end=404),
    ]
    segments_w_spans = en_no_clean_with_span_fixture.segment(text)
    assert segments_w_spans == expected_text_spans
    # check for non-destruction
    # clubbing sentences and matching with original text
    assert text == "".join([seg.sent for seg in segments_w_spans])


def test_nondestructive_when_processed_sentence_cannot_be_matched_exactly():
    text = 'S";!fR-.\'UOEV(txU(yZci2(3WsgIExZ(XQBEFL[megJ3HXr\nA]6jx.SnLA-w",'
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    spans_seg = sentencesplit.Segmenter(language="en", clean=False, char_span=True)

    segments = seg.segment(text)
    spans = spans_seg.segment(text)

    assert "".join(segments) == text
    assert "".join(span.sent for span in spans) == text


def test_nondestructive_when_processed_sentence_diverges_from_original_text():
    # Crafted input where processor rewrites bytes so a processed sentence
    # cannot be located in the original by either substring or
    # whitespace-flexible regex matching (triggers _unmatched_span /
    # _next_sentence_start / fallback fill-in branches in _match_spans).
    text = "].;YZ2Yb{♟,(cc♟0X\nX\tb2c\n♬\t2[♟?2♬),)1.3Z\n♟]2"
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    spans_seg = sentencesplit.Segmenter(language="en", clean=False, char_span=True)

    segments = seg.segment(text)
    spans = spans_seg.segment(text)

    # The key invariant under the fallback branches: even when individual
    # processed sentences cannot be matched verbatim, concatenating the
    # emitted segments (and their spans) reproduces the original text.
    assert "".join(segments) == text
    assert "".join(span.sent for span in spans) == text


# NOTE: Segmenter._wait_with_full_probe (segmenter.py lines 161-168) is a
# defensive branch that only fires when analysis_text.rfind(last_segment) == -1
# -- i.e., when processing/cleaning rewrites the last segment text so it is no
# longer a substring of analysis_text. We were unable to construct an input
# that reaches it in practice; leaving it as an unreachable fallback to audit
# later rather than fabricating a synthetic test.


def test_segment_spans_raises_with_clean_true():
    seg = sentencesplit.Segmenter(language="en", clean=True, char_span=False)
    with pytest.raises(ValueError, match="requires clean=False"):
        seg.segment_spans("Anything.")


def test_segment_spans_handles_empty_and_none_input():
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert seg.segment_spans("") == []
    assert seg.segment_spans(None) == []


def test_segment_clean_handles_empty_and_none_input():
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert seg.segment_clean("") == []
    assert seg.segment_clean(None) == []


def test_exception_with_both_clean_and_span_true():
    """Test to not allow clean=True and char_span=True"""
    with pytest.raises(ValueError) as e:
        sentencesplit.Segmenter(language="en", clean=True, char_span=True)
    assert str(e.value) == "char_span must be False if clean is True. Since `clean=True` will modify original text."
