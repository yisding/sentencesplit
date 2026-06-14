# -*- coding: utf-8 -*-
"""Regression guard for the between-punctuation opener fast-path.

``BetweenPunctuation`` skips each quote/paren sub when its opening delimiter is
absent. The guard MUST live inside each individual ``sub_*`` method, not in the
``sub_punctuation_between_quotes_and_parens`` dispatcher: language subclasses
repurpose a base method for a different opener (German routes ``„…“`` through
``sub_punctuation_between_double_quotes``), so a dispatcher-level ``'"' in txt``
check would wrongly skip that override and split inside the quote.

These tests fail if the guard regresses to the dispatcher form.
"""

from sentencesplit import Segmenter

# German low-quote dialogue: the "!" lives inside „…“ and must not end the
# sentence. German's BetweenPunctuation repurposes the base double-quote method
# for „…“ (opener U+201E, closer U+201C — no ASCII "), so a dispatcher-level
# `'"' in txt` guard would skip it; the per-method guard must still run it.
_GERMAN_QUOTED = "„Lass uns jetzt essen gehen!“, sagte die Mutter zu ihrer Freundin, „am besten zum Italiener.“"


def test_german_low_quote_dialogue_stays_one_sentence():
    sentences = Segmenter(language="de", clean=True).segment(_GERMAN_QUOTED)
    # The interior "!" is protected, so the whole utterance is a single sentence.
    assert len(sentences) == 1, sentences


def test_english_quote_and_paren_punctuation_still_protected():
    # Punctuation inside ASCII quotes and parens must not create false splits —
    # the opener IS present, so the guarded subs still run.
    quoted = Segmenter(language="en").segment('He said "Wait. Stop." and left.')
    assert quoted == ['He said "Wait. Stop." and left.'], quoted

    parened = Segmenter(language="en").segment("See the note (cf. p. 3. etc.) for details.")
    assert parened == ["See the note (cf. p. 3. etc.) for details."], parened


def test_quote_free_text_is_unchanged_by_the_fast_path():
    # The fast-path must be byte-identical to running every sub: a string with no
    # quote/paren/dash delimiters segments exactly as it always did.
    text = "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones."
    assert Segmenter(language="en").segment(text) == [
        "Dr. Smith went to Washington. ",
        "He arrived on Jan. 5th at 3 p.m. and met with Sen. Jones.",
    ]
