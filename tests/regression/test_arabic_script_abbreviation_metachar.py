# -*- coding: utf-8 -*-
"""Regression: Arabic-script abbreviation replacers must escape the matched
abbreviation before splicing it into the period-protecting lookbehind.

The retired legacy ``ArabicScriptProfile.AbbreviationReplacer`` built a
lookbehind from the raw matched text. Abbreviations such as Persian "e.g"/"i.e"
or Arabic "ا.د" contain a literal ".", which acted as a regex wildcard, so the
period after an *unrelated* word that happened to match the pattern (e.g. "egg."
matches the lookbehind "(?<= e.g)") was wrongly protected and the sentence never
split. The V2 ``AR_POLICY`` path uses the pre-escaped abbreviation in the
classifier's lookbehind, so the literal "." stays escaped and this case splits.
"""

import sentencesplit


def test_persian_dotted_abbreviation_does_not_protect_unrelated_period():
    # "e.g" is a Persian abbreviation; the period after "egg" must still split.
    text = "This is e.g. a test. I ate an egg. Then I left."
    fa = sentencesplit.Segmenter(language="fa").segment(text)
    assert fa == ["This is e.g. a test. ", "I ate an egg. ", "Then I left."]
    # Matches the English segmentation (which never had the wildcard bug).
    assert fa == sentencesplit.Segmenter(language="en").segment(text)


def test_persian_real_abbreviation_period_still_protected():
    # The genuine abbreviation period stays joined (no false split mid-sentence).
    text = "See e.g. the docs. Next sentence."
    assert sentencesplit.Segmenter(language="fa").segment(text) == [
        "See e.g. the docs. ",
        "Next sentence.",
    ]


def test_arabic_dotted_abbreviation_does_not_overprotect():
    # Arabic ships dotted abbreviations like "ا.د". Segmentation must not raise
    # and must remain non-destructive (round-trips the source).
    seg = sentencesplit.Segmenter(language="ar")
    text = "هذا اختبار. جملة أخرى هنا."
    out = seg.segment(text)
    assert "".join(out).replace(" ", "") == text.replace(" ", "")
