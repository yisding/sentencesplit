# -*- coding: utf-8 -*-
"""Regression tests for two robustness findings in ``sentencesplit.processor``.

Finding 6 — ``_resplit_multi_sentence_quote`` discarded its abbreviation-protected
scan whenever ``replace_abbreviations`` changed the segment length (the
``\\s ??`` -> `` <unknown placeholder>`` expansion is not length-preserving).
With the protected scan discarded, the ``∯`` abbreviation sentinel lookup
misaligned and an abbreviation period inside a multi-sentence quotation could be
over-split (e.g. ``Dr. Adams`` split apart under the default ``balanced`` mode).

Finding 7 — under ``clean=True`` a pre-existing multi-char ``&X&`` sentinel in
the user's input is restored to its punctuation form by ``_sub_symbols_fast``
(``&ᓴ&`` -> ``!``). This is a documented, accepted limitation; the ``Segmenter``
docstring records the caveat.
"""

from sentencesplit import Segmenter

# A pre-existing multi-char sentinel token (means "!" inside the pipeline).
_BANG_SENTINEL = "&ᓴ&"


# A multi-sentence quotation whose interior contains a protectable abbreviation
# (``Dr.``) that must stay joined, plus a number-abbreviation ``No. ??`` trigger
# that forces ``replace_abbreviations`` to change the segment length (via the
# unknown-placeholder expansion). Every interior piece is >= 5 words so the
# quote is eligible for the multi-sentence resplit.
_MULTI_SENTENCE_QUOTE = (
    '"The local patient clearly saw old Dr. Adams about the strange illness today. '
    "Many other people also consider this whole matter rather important. "
    'Consider also entry No. ?? in greater detail."'
)


def test_quote_resplit_keeps_abbreviation_joined_on_length_change():
    """Finding 6: the abbreviation period inside the quote must not be over-split.

    Before the fix, the length-changing ``No. ??`` expansion forced the resplit
    to fall back to the unprotected scan, so ``Dr. Adams`` was split apart
    (``...saw old Dr.`` / ``Adams about...``) under the default balanced mode.
    """
    seg = Segmenter(language="en")
    sentences = seg.segment(_MULTI_SENTENCE_QUOTE)

    # No segment may end at the abbreviation period of "Dr." with the following
    # word "Adams" orphaned into the next segment.
    for sentence in sentences:
        assert not sentence.rstrip().endswith("Dr."), sentences
    assert not any(sentence.lstrip().startswith("Adams") for sentence in sentences), sentences

    # The abbreviation stays inside a single segment.
    assert any("Dr. Adams" in sentence for sentence in sentences), sentences

    # The split round-trip is preserved (no text gained or lost).
    assert "".join(sentences) == _MULTI_SENTENCE_QUOTE.replace("\n", "")


def test_quote_resplit_span_round_trip_holds_on_length_change():
    """Finding 6: span mapping must still round-trip exactly (no text loss)."""
    seg = Segmenter(language="en")
    spans = seg.segment_spans(_MULTI_SENTENCE_QUOTE)
    assert "".join(s.sent for s in spans) == _MULTI_SENTENCE_QUOTE
    for span in spans:
        assert _MULTI_SENTENCE_QUOTE[span.start : span.end] == span.sent


def test_clean_true_multi_char_sentinel_caveat_is_documented():
    """Finding 7: the accepted ``clean=True`` multi-char-sentinel limitation.

    The code-fix path (escaping pre-existing ``&X&`` tokens) cannot be done
    without threading escape state through the Cleaner -> Processor boundary,
    where the Cleaner legitimately produces the same multi-char tokens, so the
    documented fallback is taken. Assert the documented behavior so the caveat
    cannot silently disappear.
    """
    # Documented behavior: under clean=True a literal sentinel is restored to "!".
    seg_clean = Segmenter(language="en", clean=True)
    cleaned = seg_clean.segment(f"foo{_BANG_SENTINEL}bar. baz qux here.")
    assert any("!" in sentence for sentence in cleaned), cleaned
    assert not any(_BANG_SENTINEL in sentence for sentence in cleaned), cleaned

    # The default clean=False path is non-destructive: the sentinel survives.
    seg_default = Segmenter(language="en", clean=False)
    default = seg_default.segment(f"foo{_BANG_SENTINEL}bar. baz qux here.")
    assert any(_BANG_SENTINEL in sentence for sentence in default), default


# A multi-sentence document with abbreviations but NO leading-quote segment. The
# quote-resplit branch can never fire here, so it must not run the (expensive)
# abbreviation-protected scan once per sentence.
_NO_QUOTE_MULTI_SENTENCE = (
    "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
    "The model is GPT 3.1 and it is fast. That is all for now. Goodbye. "
    "She paid $4.50 for the U.S. edition (vol. 2, p. 17). Mr. Lee agreed."
)


def test_quote_resplit_skips_abbreviation_scan_for_quote_free_segments():
    """The quote-resplit branch must not re-run abbreviation replacement per
    sentence when no segment begins with a quote.

    ``_resplit_multi_sentence_quote`` returns ``None`` immediately unless the
    segment starts with a leading quote, so the abbreviation-protected scan it
    consumes is wasted work for quote-free segments. ``replace_abbreviations``
    legitimately runs once for the whole text in the main pipeline; the resplit
    pass must add zero further calls when there is no quoted segment.
    """
    from sentencesplit.processor import Processor

    seg = Segmenter(language="en")

    original = Processor.replace_abbreviations
    calls = {"n": 0}

    def counting(self, text=None):
        calls["n"] += 1
        return original(self, text)

    Processor.replace_abbreviations = counting
    try:
        sentences = seg.segment(_NO_QUOTE_MULTI_SENTENCE)
    finally:
        Processor.replace_abbreviations = original

    # Exactly one whole-text abbreviation pass: the main text-processing phase.
    # The per-sentence quote-resplit branch contributes none.
    assert calls["n"] == 1, calls["n"]
    # Behavior is unchanged: the text still round-trips with no loss.
    assert "".join(sentences) == _NO_QUOTE_MULTI_SENTENCE
