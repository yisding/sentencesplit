# -*- coding: utf-8 -*-
"""Regression tests for issues found in the 2026-05 library review.

Each test pins a behaviour that was wrong before the corresponding fix.
"""

from __future__ import annotations

import pytest

import sentencesplit

# ---------------------------------------------------------------------------
# Internal sentinel characters in user input must not corrupt output.
# ---------------------------------------------------------------------------
_SENTINEL_INPUTS = [
    "aJTF．MP9 2\t♬k！UtMXhk{Pr'S♬-b！b",
    "I love this song ♬ so much.",
    "The integral ∯ appears here. Then more.",
    "Look ƪƪƪ at this thing.",
    "A weird ♭ symbol and a ☏ phone. Next sentence.",
    "Has ☉ and ☄ doubles. And more text.",
    "Edge letter ȸ stays. Another one ȹ here.",
    "List marker ♨ and ☝ glyphs. Done.",
]


@pytest.mark.parametrize("text", _SENTINEL_INPUTS)
def test_sentinel_chars_in_input_are_non_destructive(text):
    """clean=False segmentation must tile the original text exactly."""
    seg = sentencesplit.Segmenter(language="en")
    segments = seg.segment(text)
    assert "".join(segments) == text


@pytest.mark.parametrize("text", _SENTINEL_INPUTS)
def test_sentinel_chars_preserved_with_char_spans(text):
    seg = sentencesplit.Segmenter(language="en", char_span=True)
    spans = seg.segment(text)
    assert "".join(s.sent for s in spans) == text
    # spans must tile the original contiguously
    prev_end = 0
    for s in spans:
        assert s.start == prev_end
        assert text[s.start : s.end] == s.sent
        prev_end = s.end
    assert prev_end == len(text)


@pytest.mark.parametrize(
    "text",
    [
        "I love this song ♬ so much.",
        "x ȸ y.",
        "The integral ∯ stands alone.",
        "Look ƪƪƪ at this thing.",
    ],
)
def test_sentinel_chars_preserved_in_clean_mode(text):
    """clean=True must not rewrite a user-typed sentinel into its target glyph."""
    seg = sentencesplit.Segmenter(language="en", clean=True)
    assert "".join(seg.segment_clean(text)) == text


# ---------------------------------------------------------------------------
# Abbreviation findall index misalignment.
# A period-less decoy occurrence before the real "ABBR." must not flip the
# split decision for the real occurrence.
# ---------------------------------------------------------------------------
def test_abbreviation_decoy_occurrence_does_not_flip_split_en_legal():
    seg = sentencesplit.Segmenter(language="en_legal")
    isolated = [s.strip() for s in seg.segment("The 9th Cir. The panel reversed.")]
    with_decoy = [s.strip() for s in seg.segment("The 9th Cir held. The 9th Cir. The panel reversed.")]
    assert isolated == ["The 9th Cir.", "The panel reversed."]
    # The decoy "Cir held" must not change how the real "Cir." is handled.
    assert with_decoy == ["The 9th Cir held.", "The 9th Cir.", "The panel reversed."]


def test_abbreviation_decoy_occurrence_does_not_flip_split_en():
    seg = sentencesplit.Segmenter(language="en")
    assert [s.strip() for s in seg.segment("See Gov here. The Gov. The state acted.")] == [
        "See Gov here.",
        "The Gov. The state acted.",
    ]


# ---------------------------------------------------------------------------
# CJK exclamation/question terminals inside quotes split before a new clause,
# but stay joined for embedded reported quotes (quotative と) and title marks.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "language,text,expected",
    [
        ("zh", "「快跑！」大家都散开了。", ["「快跑！」", "大家都散开了。"]),
        ("zh", "『真的吗？』他愣住了。", ["『真的吗？』", "他愣住了。"]),
        ("ja", "「危ない！」みんな逃げた。", ["「危ない！」", "みんな逃げた。"]),
    ],
)
def test_cjk_bang_quote_splits_before_new_clause(language, text, expected):
    seg = sentencesplit.Segmenter(language=language)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "language,text",
    [
        ("zh", "「先这样吧！」她回答。"),  # reporting clause re-merges
        ("ja", "彼は「本当に来るの？」と聞いた。"),  # quotative と marks an embedded quote
    ],
)
def test_cjk_bang_quote_stays_joined_for_reported_speech(language, text):
    seg = sentencesplit.Segmenter(language=language)
    assert [s.strip() for s in seg.segment(text)] == [text]


# ---------------------------------------------------------------------------
# Orphan-merge must not swallow a legitimate short sentence.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("He walked away.) The end.", ["He walked away.", ") The end."]),
        ("I have two. 3 are red.", ["I have two.", "3 are red."]),
        ("Look here. go away.", ["Look here.", "go away."]),
    ],
)
def test_orphan_merge_does_not_swallow_short_sentences(text, expected):
    seg = sentencesplit.Segmenter(language="en")
    assert [s.strip() for s in seg.segment(text)] == expected
    assert "".join(seg.segment(text)) == text


# ---------------------------------------------------------------------------
# Cleaner fixes.
# ---------------------------------------------------------------------------
def test_escaped_html_rule_preserves_escaped_comparisons():
    """&lt; / &gt; in prose (escaped math) must not be deleted as a fake tag."""
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    # Genuine escaped tags are still stripped...
    assert Cleaner("a &lt;b&gt;x&lt;/b&gt; c", en).clean() == "a x c"
    # ...but escaped comparison operators in prose are preserved.
    cleaned = Cleaner("The value x &lt; 5 and y &gt; 3 here.", en).clean()
    assert "5 and y" in cleaned


def test_table_of_contents_rule_does_not_eat_ellipsis_prose():
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    assert Cleaner("wait.... 42 things happened", en).clean() == "wait.... 42 things happened"


def test_escaped_and_real_newlines_clean_identically():
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    escaped = Cleaner("Line one.\\nLine two.", en).clean()
    real = Cleaner("Line one.\nLine two.", en).clean()
    assert escaped == real


def test_pdf_mode_dehyphenates_line_broken_words():
    seg = sentencesplit.Segmenter(language="en", clean=True, doc_type="pdf")
    assert seg.segment("This is a hyphen-\nated word in pdf.") == ["This is a hyphenated word in pdf."]


# ---------------------------------------------------------------------------
# Between-punctuation: a single-quoted phrase at the start of the text must be
# protected (mirroring double quotes / parens).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "'stop now. go away.' he said",
        "‘stop now. go away.’ he said",
    ],
)
def test_leading_single_quote_phrase_is_protected(text):
    seg = sentencesplit.Segmenter(language="en")
    assert seg.segment(text) == [text]


# ---------------------------------------------------------------------------
# Hindi: "." is not a sentence terminator (danda is); periods must not split.
# ---------------------------------------------------------------------------
def test_hindi_period_is_not_a_boundary():
    seg = sentencesplit.Segmenter(language="hi")
    assert seg.segment("First sentence. Second sentence.") == ["First sentence. Second sentence."]
    assert [s.strip() for s in seg.segment("अ आ। इ ई।")] == ["अ आ।", "इ ई।"]


# ---------------------------------------------------------------------------
# Exclamation-word alternation must match the longest entry first.
# ---------------------------------------------------------------------------
def test_exclamation_words_longest_match_first():
    from sentencesplit.exclamation_words import ExclamationWords

    # "!Kung-Ekoka" must be matched whole, not as "!Kung" + dangling "-Ekoka".
    out = ExclamationWords.apply_rules("the !Kung-Ekoka people")
    assert "!" not in out  # the protected "!" was replaced by its placeholder
