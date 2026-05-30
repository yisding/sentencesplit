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


def test_split_mode_must_be_valid():
    with pytest.raises(ValueError, match="split_mode must be one of"):
        sentencesplit.Segmenter(language="en", split_mode="fast")


def test_split_mode_defaults_to_balanced():
    assert sentencesplit.Segmenter(language="en").split_mode == "balanced"
    # "balanced" is accepted explicitly and is the historically tuned behavior.
    assert sentencesplit.Segmenter(language="en", split_mode="balanced").split_mode == "balanced"


@pytest.mark.parametrize(
    "text,expected_conservative,expected_aggressive",
    [
        (
            "I live on 1st st. It is nice.",
            ["I live on 1st st. It is nice."],
            ["I live on 1st st. ", "It is nice."],
        ),
        (
            "We stayed near Mt. It was cold.",
            ["We stayed near Mt. It was cold."],
            ["We stayed near Mt. It was cold."],
        ),
        (
            "He met Dr. Adams. They talked.",
            ["He met Dr. Adams. ", "They talked."],
            ["He met Dr. Adams. ", "They talked."],
        ),
        (
            "Mr. Brown arrived. We waited.",
            ["Mr. Brown arrived. ", "We waited."],
            ["Mr. Brown arrived. ", "We waited."],
        ),
    ],
)
def test_split_mode_controls_high_ambiguity_abbreviations(text, expected_conservative, expected_aggressive):
    conservative_seg = sentencesplit.Segmenter(language="en", split_mode="conservative")
    aggressive_seg = sentencesplit.Segmenter(language="en", split_mode="aggressive")

    assert conservative_seg.segment(text) == expected_conservative
    assert aggressive_seg.segment(text) == expected_aggressive


def test_split_mode_ampm_dial_applies_to_german_override():
    # German overrides AbbreviationReplacer.replace(); the conservative a.m./p.m.
    # dial must still apply (it shares the base helper).
    text = "Das Treffen ist um 3 p.m. Bitte kommen Sie früh."
    assert len(sentencesplit.Segmenter(language="de", split_mode="conservative").segment(text)) == 1
    for mode in ("balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="de", split_mode=mode).segment(text)) == 2


def test_split_mode_number_abbrev_dial_applies_to_en_es_zh_override():
    # en_es_zh overrides scan_for_replacements; the conservative number-abbrev
    # dial must apply there too, while "Vol. IV" stays joined in every mode.
    text = "See Fig. Several panels follow."
    assert len(sentencesplit.Segmenter(language="en_es_zh", split_mode="conservative").segment(text)) == 1
    for mode in ("balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="en_es_zh", split_mode=mode).segment(text)) == 2
    for mode in ("conservative", "balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="en_es_zh", split_mode=mode).segment("See Vol. IV for details.")) == 1


@pytest.mark.parametrize(
    "text,joined,split",
    [
        # 3-part initialism before a capitalized word is structurally identical
        # to "Initials + Surname"; aggressive resolves the ambiguity by splitting.
        ("We discussed H.B.S. Applications are due.", ["We discussed H.B.S. Applications are due."], 2),
        ("I visited U.S.A. Microsoft is based there.", ["I visited U.S.A. Microsoft is based there."], 2),
        # The accepted trade-off: a real name splits in aggressive mode too.
        (
            "A.S.E. Ackermann and team published the findings in 2007.",
            ["A.S.E. Ackermann and team published the findings in 2007."],
            2,
        ),
    ],
)
def test_split_mode_initialism_before_capital(text, joined, split):
    # conservative and balanced keep the surname reading (joined); aggressive splits.
    for mode in ("conservative", "balanced"):
        assert sentencesplit.Segmenter(language="en", split_mode=mode).segment(text) == joined
    aggressive = sentencesplit.Segmenter(language="en", split_mode="aggressive").segment(text)
    assert len(aggressive) == split


def test_split_mode_initialism_with_strong_cue_splits_in_all_modes():
    # A determiner ("the S.A.T.") or sentence-starter ("from H.B.S. She") is a
    # strong boundary cue, so the split happens regardless of mode.
    for mode in ("conservative", "balanced", "aggressive"):
        seg = sentencesplit.Segmenter(language="en", split_mode=mode)
        assert [s.strip() for s in seg.segment("I studied for the S.A.T. Tomorrow is test day.")] == [
            "I studied for the S.A.T.",
            "Tomorrow is test day.",
        ]


@pytest.mark.parametrize(
    "text,n_conservative,n_balanced,n_aggressive",
    [
        # Mixed multi-period abbreviation before a capital: conservative joins
        # (surname reading), balanced/aggressive split.
        ("She earned a Ph.D. Smith advised her.", 1, 2, 2),
        # Pure initialism before a capital: only aggressive splits; conservative
        # and balanced keep it joined ("A.I." protected before "Systems").
        ("Work on A.I. Systems are improving.", 1, 1, 2),
    ],
)
def test_split_mode_multi_period_abbreviation(text, n_conservative, n_balanced, n_aggressive):
    counts = {
        "conservative": n_conservative,
        "balanced": n_balanced,
        "aggressive": n_aggressive,
    }
    for mode, n in counts.items():
        seg = sentencesplit.Segmenter(language="en", split_mode=mode)
        assert len(seg.segment(text)) == n


def test_split_mode_inline_ordinal_vs_numbered_list():
    # A single-line run of ordinals before lowercase words is prose in
    # conservative/balanced (joined); aggressive treats it as a numbered list.
    text = "Im Laufe des 19. und frühen 20. Jahrhunderts wuchs die Stadt."
    for mode in ("conservative", "balanced"):
        assert len(sentencesplit.Segmenter(language="de", split_mode=mode).segment(text)) == 1
    assert len(sentencesplit.Segmenter(language="de", split_mode="aggressive").segment(text)) > 1


def test_split_mode_ampm_before_capital():
    # conservative keeps a.m./p.m. joined before a capital; balanced/aggressive
    # split. A trailing timezone ("p.m. EST") stays one unit in every mode.
    text = "The meeting is at 3 p.m. Please arrive early."
    assert len(sentencesplit.Segmenter(language="en", split_mode="conservative").segment(text)) == 1
    for mode in ("balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="en", split_mode=mode).segment(text)) == 2
    tz = "The call is at 3 p.m. EST. Join on time."
    assert [s.strip() for s in sentencesplit.Segmenter(language="en", split_mode="aggressive").segment(tz)] == [
        "The call is at 3 p.m. EST.",
        "Join on time.",
    ]


def test_split_mode_exclamation_before_lowercase():
    # "!" before a lowercase word is mid-sentence emphasis in conservative and
    # balanced (joined); aggressive treats it as a boundary.
    text = "Wow! amazing stuff happened today."
    for mode in ("conservative", "balanced"):
        assert len(sentencesplit.Segmenter(language="en", split_mode=mode).segment(text)) == 1
    assert len(sentencesplit.Segmenter(language="en", split_mode="aggressive").segment(text)) == 2


def test_split_mode_ellipsis_before_capital():
    # "..." before a capital: conservative reads it as a trailing-thought
    # ellipsis (joined); balanced and aggressive treat it as a boundary.
    text = "Wait... She left the store."
    assert len(sentencesplit.Segmenter(language="en", split_mode="conservative").segment(text)) == 1
    for mode in ("balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="en", split_mode=mode).segment(text)) == 2


def test_split_mode_multi_sentence_quotation_resplit():
    q3 = (
        '"Indeed, I should have thought a little more. Just a trifle more, I fancy, Watson. And in practice again, I observe."'
    )
    q2 = '"I have read your case with interest. It seems a remarkable one indeed to me."'
    # conservative never resplits a quotation; balanced needs >=3 interior
    # sentences; aggressive lowers the bar to 2.
    assert len(sentencesplit.Segmenter(language="en", split_mode="conservative").segment(q3)) == 1
    assert len(sentencesplit.Segmenter(language="en", split_mode="balanced").segment(q3)) == 3
    assert len(sentencesplit.Segmenter(language="en", split_mode="aggressive").segment(q3)) == 3
    assert len(sentencesplit.Segmenter(language="en", split_mode="balanced").segment(q2)) == 1
    assert len(sentencesplit.Segmenter(language="en", split_mode="aggressive").segment(q2)) == 2


def test_split_mode_number_abbreviation_before_capital():
    # "Fig. Several" / "No. The": conservative joins (continuation reading),
    # balanced and aggressive split. A Roman numeral ("Vol. IV") stays joined
    # in every mode — that is structural, not a tunable lean.
    text = "See Fig. Several panels follow."
    assert len(sentencesplit.Segmenter(language="en", split_mode="conservative").segment(text)) == 1
    for mode in ("balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="en", split_mode=mode).segment(text)) == 2
    for mode in ("conservative", "balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="en", split_mode=mode).segment("See Vol. IV for details.")) == 1


def test_split_mode_court_prepositive_abbreviation():
    # en_legal STARTER_AWARE prepositive "Cir."/"Bankr.": conservative joins
    # everything, balanced splits only before a known starter ("The"),
    # aggressive splits before any capital ("Bankr. Court").
    expectations = {
        "conservative": {
            "The 9th Cir. The panel reversed.": 1,
            "The Bankr. Court approved the plan.": 1,
        },
        "balanced": {
            "The 9th Cir. The panel reversed.": 2,
            "The Bankr. Court approved the plan.": 1,
        },
        "aggressive": {
            "The 9th Cir. The panel reversed.": 2,
            "The Bankr. Court approved the plan.": 2,
        },
    }
    for mode, cases in expectations.items():
        seg = sentencesplit.Segmenter(language="en_legal", split_mode=mode)
        for text, n in cases.items():
            assert len(seg.segment(text)) == n, (mode, text)


def test_split_mode_propagates_to_helper_segmenters():
    seg = sentencesplit.Segmenter(language="en", split_mode="aggressive")

    assert seg.segment_clean("I live on 1st st. It is nice.") == ["I live on 1st st.", "It is nice."]
    assert [span.sent for span in seg.segment_spans("I live on 1st st. It is nice.")] == [
        "I live on 1st st. ",
        "It is nice.",
    ]


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


def test_exception_with_doc_type_pdf_and_clean_false():
    """
    Test to force clean=True when doc_type="pdf"
    """
    with pytest.raises(ValueError) as e:
        sentencesplit.Segmenter(language="en", clean=False, doc_type="pdf")
    assert str(e.value) == (
        "`doc_type='pdf'` should have `clean=True` & `char_span` should be False since original text will be modified."
    )


def test_exception_with_doc_type_pdf_and_both_clean_char_span_true():
    """
    Test to raise ValueError exception when doc_type="pdf" and
    both clean=True and char_span=True
    """
    with pytest.raises(ValueError) as e:
        sentencesplit.Segmenter(language="en", clean=True, doc_type="pdf", char_span=True)
    assert str(e.value) == "char_span must be False if clean is True. Since `clean=True` will modify original text."


PDF_TEST_DATA = [
    ("This is a sentence\ncut off in the middle because pdf.", ["This is a sentence cut off in the middle because pdf."]),
    (
        "Organising your care early \nmeans you'll have months to build a good relationship with your midwife or doctor, ready for \nthe birth.",
        [
            "Organising your care early means you'll have months to build a good relationship with your midwife or doctor, ready for the birth."
        ],
    ),
    (
        "10. Get some rest \n \nYou have the best chance of having a problem-free pregnancy and a healthy baby if you follow \na few simple guidelines:",
        [
            "10. Get some rest",
            "You have the best chance of having a problem-free pregnancy and a healthy baby if you follow a few simple guidelines:",
        ],
    ),
    (
        "• 9. Stop smoking \n• 10. Get some rest \n \nYou have the best chance of having a problem-free pregnancy and a healthy baby if you follow \na few simple guidelines:  \n\n1. Organise your pregnancy care early",
        [
            "• 9. Stop smoking",
            "• 10. Get some rest",
            "You have the best chance of having a problem-free pregnancy and a healthy baby if you follow a few simple guidelines:",
            "1. Organise your pregnancy care early",
        ],
    ),
    (
        "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next. First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs. She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.\n'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        [
            "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next.",
            "First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs.",
            "She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.",
            "'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        ],
    ),
    (
        "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next. First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs. She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.\r'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        [
            "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next.",
            "First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs.",
            "She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.",
            "'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        ],
    ),
]


@pytest.mark.parametrize("text,expected_sents", PDF_TEST_DATA)
def test_en_pdf_type(text, expected_sents):
    """SBD tests from Pragmatic Segmenter for doctype:pdf"""
    seg = sentencesplit.Segmenter(language="en", clean=True, doc_type="pdf")
    segments = seg.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
