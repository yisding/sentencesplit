import pytest

import sentencesplit


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


def test_split_mode_controls_russian_sr_abbreviation():
    ambiguous = "Ср. Она важна."
    assert [s.strip() for s in sentencesplit.Segmenter(language="ru", split_mode="conservative").segment(ambiguous)] == [
        ambiguous
    ]
    for mode in ("balanced", "aggressive"):
        assert [s.strip() for s in sentencesplit.Segmenter(language="ru", split_mode=mode).segment(ambiguous)] == [
            "Ср.",
            "Она важна.",
        ]

    compare_phrase = "Ср. Пушкина и Лермонтова."
    for mode in ("conservative", "balanced"):
        assert [s.strip() for s in sentencesplit.Segmenter(language="ru", split_mode=mode).segment(compare_phrase)] == [
            compare_phrase
        ]
    assert [s.strip() for s in sentencesplit.Segmenter(language="ru", split_mode="aggressive").segment(compare_phrase)] == [
        "Ср.",
        "Пушкина и Лермонтова.",
    ]


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
