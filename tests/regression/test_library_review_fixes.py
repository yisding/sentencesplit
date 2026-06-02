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


def test_escaped_html_rule_strips_tags_with_entities_in_attributes():
    """Escaped tags whose attributes carry ordinary entities (&amp;, &quot;,
    &#39;) must still be removed — the inner run must not stop at the first '&'."""
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    assert Cleaner('&lt;a href="x&amp;y"&gt;link&lt;/a&gt;', en).clean() == "link"
    assert Cleaner('&lt;img alt=&quot;a&amp;b&quot; src="x"&gt;Y', en).clean() == "Y"
    assert Cleaner("&lt;p data-x=&#39;1&#39;&gt;Z&lt;/p&gt;", en).clean() == "Z"


def test_escaped_html_rule_not_redos_on_entity_packed_unclosed_run():
    """The entity-crossing alternation must stay linear: an unclosed escaped tag
    packed with entities (many '&lt;' starts) would be quadratic if a run could
    consume past the next delimiter, so guard the rule itself at large N."""
    import time

    from sentencesplit.cleaner import HTML
    from sentencesplit.utils import apply_rules

    # ~1M chars of "&lt;a&amp;" with no closing &gt;: linear ~tens of ms here,
    # but seconds-to-minutes if the alternation regressed to quadratic.
    evil = "&lt;a&amp;" * 100000
    start = time.perf_counter()
    assert apply_rules(evil, HTML.EscapedHTMLTagRule) == evil
    assert time.perf_counter() - start < 1.0


def test_table_of_contents_rule_does_not_eat_ellipsis_prose():
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    assert Cleaner("wait.... 42 things happened", en).clean() == "wait.... 42 things happened"


def test_table_of_contents_rule_not_redos_on_failed_line_anchor():
    import time

    from sentencesplit.cleaner import cr
    from sentencesplit.utils import apply_rules

    evil = "." * 300 + " " * 300 + "1" * 300 + "X"
    start = time.perf_counter()
    assert apply_rules(evil, cr.TableOfContentsRule) == evil
    assert time.perf_counter() - start < 0.25


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


# ---------------------------------------------------------------------------
# en_es_zh combined-profile divergences from the component languages.
# ---------------------------------------------------------------------------
def test_en_es_zh_spanish_abbreviation_splits_before_capital_like_components():
    """A Spanish-only abbreviation that is also a plain word (doc) must split
    before a capitalized sentence start, as it does in both en and es."""
    ez = sentencesplit.Segmenter(language="en_es_zh")
    en = sentencesplit.Segmenter(language="en")
    es = sentencesplit.Segmenter(language="es")
    text = "I read the doc. He left."
    expected = ["I read the doc.", "He left."]
    assert [s.strip() for s in en.segment(text)] == expected
    assert [s.strip() for s in es.segment(text)] == expected
    assert [s.strip() for s in ez.segment(text)] == expected


def test_en_es_zh_cjk_closer_then_lowercase_latin_splits_like_zh():
    """A lowercase Latin word after a CJK closing quote is a new sentence
    (matching standalone zh), not a quote continuation."""
    text = "结果是「好。」then nothing happened."
    ez = [s.strip() for s in sentencesplit.Segmenter(language="en_es_zh").segment(text)]
    zh = [s.strip() for s in sentencesplit.Segmenter(language="zh").segment(text)]
    assert ez == zh == ["结果是「好。」", "then nothing happened."]


# ---------------------------------------------------------------------------
# CJK abbreviation-period override (zh/ja): a Latin abbreviation period before a
# CJK character is protected (stays joined).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "language,text",
    [
        ("zh", "He works at Inc.中文继续。"),
        ("ja", "He works at co.日本語が続く。"),
    ],
)
def test_cjk_abbreviation_period_before_cjk_stays_joined(language, text):
    seg = sentencesplit.Segmenter(language=language)
    assert seg.segment(text) == [text]


# ---------------------------------------------------------------------------
# ReDoS: an unclosed HTML-like tag with repeated attributes must clean quickly
# (the old HTMLTagRule had catastrophic backtracking on untrusted clean=True
# input). We assert correctness + a generous wall-clock ceiling.
# ---------------------------------------------------------------------------
def test_html_tag_rule_is_not_redos_vulnerable():
    import time

    seg = sentencesplit.Segmenter(language="en", clean=True)
    evil = "ok <a " + 'b="c" ' * 60 + "z."
    start = time.perf_counter()
    seg.segment(evil)
    assert time.perf_counter() - start < 2.0


def test_html_tag_rule_still_strips_tags():
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    assert Cleaner("Yes <em>really</em> <p class='x'>now</p>.", en).clean() == "Yes really now."


# ---------------------------------------------------------------------------
# Second-round fixes surfaced by adversarial verification of the first round.
# ---------------------------------------------------------------------------
def test_sentinel_escape_handles_preexisting_private_use_chars():
    """A pre-existing private-use codepoint must round-trip even when the input
    also contains a reserved sentinel that triggers escaping."""
    # clean=False: nothing dropped (escape targets are chosen absent from input)
    seg = sentencesplit.Segmenter(language="en")
    text = "Math  and  with ∯ sentinel. Then  more."
    assert "".join(seg.segment(text)) == text
    # clean=True: the user's private-use chars and sentinel survive verbatim
    clean = sentencesplit.Segmenter(language="en", clean=True)
    t2 = "Glyph  next to ∯ here."
    assert "".join(clean.segment_clean(t2)) == t2


def test_sentinel_escape_pool_exhaustion_uses_absent_private_use_tokens(monkeypatch):
    """If the input occupies every single-character escape target, escaping a
    reserved sentinel must fall back to a longer absent private-use token instead
    of raising from process()."""
    from sentencesplit import processor as _proc

    # Shrink the escape pool to two codepoints so the 20 reserved sentinels
    # cannot all be assigned a single-character free target.
    monkeypatch.setattr(_proc, "_PRIVATE_USE_RANGES", ((0xE000, 0xE001),))
    seg = sentencesplit.Segmenter(language="en")
    text = "Has \ue000 and \ue001 plus a ∯ reserved sentinel. And more."
    assert "".join(seg.segment(text)) == text


def test_sentinel_restore_is_overlap_safe_for_adjacent_multichar_tokens(monkeypatch):
    """When the single-char private-use pool is exhausted, two adjacent reserved
    sentinels escape to multi-character tokens. Restoring them must be atomic so
    an earlier token's restore cannot consume a window straddling the next
    token's bytes (which would leave raw private-use chars in the output).

    Exercised directly through Processor.process() and segment_clean(), not only
    segment(): the default span-recovery path in Segmenter._match_spans re-anchors
    to the original text and would mask the corruption.
    """
    from sentencesplit import processor as _proc
    from sentencesplit.languages import Language

    # Two-codepoint pool forces fixed-width multi-char escape tokens for the 20
    # reserved sentinels, so adjacent escaped sentinels form an ambiguous run.
    monkeypatch.setattr(_proc, "_PRIVATE_USE_RANGES", ((0xE000, 0xE001),))

    en = Language.get_language_code("en")
    clean = sentencesplit.Segmenter(language="en", clean=True)

    # Single sentence: the two adjacent sentinels (♭∯) escape to distinct
    # multi-char tokens, and the whole string must round-trip exactly, with no
    # raw private-use chars left behind.
    single = "Pair ♭∯ here and more."
    out = "".join(_proc.Processor(single, en).process())
    assert out == single
    assert not any(0xE000 <= ord(ch) <= 0xF8FF for ch in out)
    assert "".join(clean.segment_clean(single)) == single

    # Across a sentence boundary the adjacent sentinels must still survive
    # verbatim on the segment that carries them (the boundary space is consumed
    # by splitting, so an exact whole-string join is not the invariant here).
    multi = "Pair ♭∯ here. And more."
    segments = _proc.Processor(multi, en).process()
    assert segments == ["Pair ♭∯ here.", "And more."]
    assert not any(0xE000 <= ord(ch) <= 0xF8FF for seg in segments for ch in seg)
    assert clean.segment_clean(multi) == ["Pair ♭∯ here.", "And more."]


def test_escaped_html_rule_is_not_redos_vulnerable():
    import time

    seg = sentencesplit.Segmenter(language="en", clean=True)
    evil = "Hello. &lt;a" + "b" * 40000 + " world."
    start = time.perf_counter()
    seg.segment(evil)
    assert time.perf_counter() - start < 2.0


def test_html_tag_rule_not_redos_on_long_unclosed_run():
    import time

    seg = sentencesplit.Segmenter(language="en", clean=True)
    evil = "Intro. <a" + "b" * 40000 + " trailing."
    start = time.perf_counter()
    seg.segment(evil)
    assert time.perf_counter() - start < 2.0


def test_html_tag_rule_not_quadratic_on_many_unclosed_openers():
    import time

    seg = sentencesplit.Segmenter(language="en", clean=True)
    evil = ("<a " * 50000) + "end."
    start = time.perf_counter()
    assert seg.segment(evil)[-1].endswith("end.")
    assert time.perf_counter() - start < 2.0


def test_html_tag_rule_preserves_gt_inside_quoted_attribute():
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    assert Cleaner('<a title="a>b">link</a>', en).clean() == "link"


def test_html_tag_rule_strips_lt_inside_quoted_attribute():
    """A literal '<' inside a quoted attribute value must not stop the tag from
    matching: a quoted run is self-terminating at its closing quote and cannot
    cross another tag, so '<' (like '>') is allowed inside quoted runs. Excluding
    it would leak the opening tag into the cleaned untrusted-HTML stream."""
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    assert Cleaner('<span data-x="1 < 2">Text</span>', en).clean() == "Text"
    assert Cleaner("<span data-x='1 < 2'>Text</span>", en).clean() == "Text"


def test_html_tag_rule_not_quadratic_with_lt_permissive_quoted_run():
    """The '<'-inside-quotes fix must not reintroduce the quadratic blow-up on
    many unclosed openers that the perf hardening killed."""
    import time

    seg = sentencesplit.Segmenter(language="en", clean=True)
    evil = ("<a " * 50000) + "end."
    start = time.perf_counter()
    assert seg.segment(evil)[-1].endswith("end.")
    assert time.perf_counter() - start < 2.0


def test_cjk_bang_resplit_does_not_oversplit_ascii_in_combined_profile():
    """A Latin '!'/'?' inside parens must not be resplit in the CJK-aware
    en_es_zh profile (only fullwidth ！？ trigger the bang resplit)."""
    ez = sentencesplit.Segmenter(language="en_es_zh")
    en = sentencesplit.Segmenter(language="en")
    for text in ["The album (Help!)was great.", "I asked (why?)but got no reply."]:
        assert ez.segment(text) == en.segment(text) == [text]


def test_profile_cache_does_not_pin_unregistered_language_classes():
    import gc
    import weakref

    from sentencesplit.lang.common import Common, Standard
    from sentencesplit.languages import register_language, unregister_language

    refs = []
    for i in range(25):
        cls = type(f"Demo{i}", (Common, Standard), {"iso_code": "demo"})
        register_language("demo", cls)
        sentencesplit.Segmenter(language="demo").segment("Hello. Bye.")
        refs.append(weakref.ref(cls))
        unregister_language("demo")
        del cls
    gc.collect()
    assert all(ref() is None for ref in refs)
