import pytest

import sentencesplit


def _segments(language, text, split_mode):
    return [s.strip() for s in sentencesplit.Segmenter(language=language, clean=False, split_mode=split_mode).segment(text)]


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
    "language,boundary_text,ambiguous_text",
    [
        (
            "en",
            "He moved from the U.S. It happened.",
            "He joined the U.S. Market today.",
        ),
        (
            "de",
            "Er lebt in der E.U. Das ist bekannt.",
            "Er lebt in der E.U. Kommission arbeitet dort.",
        ),
        (
            "da",
            "Han bor i U.S. Det er kendt.",
            "Han bor i U.S. Market i dag.",
        ),
    ],
)
def test_split_mode_controls_two_letter_initialisms(language, boundary_text, ambiguous_text):
    """Capitalized followers after two-letter dotted initialisms are structural ambiguity.

    Conservative keeps the abbreviation joined; balanced and aggressive split.
    """
    assert _segments(language, boundary_text, "conservative") == [boundary_text]
    assert _segments(language, ambiguous_text, "conservative") == [ambiguous_text]
    for mode in ("balanced", "aggressive"):
        assert len(_segments(language, boundary_text, mode)) == 2
        assert len(_segments(language, ambiguous_text, mode)) == 2


@pytest.mark.parametrize(
    "text",
    [
        "The U.S. Department issued guidance.",
        "The U.S. Department's guidance changed.",
        "The L.A. Times reported the story.",
        "The D.C. Circuit heard arguments.",
        "The D.C. Circuit's ruling stood.",
        "The U.S. Court of Appeals ruled.",
        "The U.S. Courts reopened.",
        "The U.S. Courts' procedures changed.",
        "The U.S. Supreme Court ruled.",
        "The U.S. District Court ruled.",
        "The U.S. Embassy opened.",
        "The U.S. Government issued guidance.",
        "The U.S. Government office opened.",
        "The U.S. Government's response arrived.",
        "The U.N. General Assembly met.",
        "The U.N. General Assembly's vote passed.",
        "The U.N. Security Council met.",
        "The U.N. Security Council's vote passed.",
        "The U.N. Secretary General spoke.",
        "The U.N. Secretary-General spoke.",
        "The U.N. Secretary-General's statement landed.",
        "The E.U. Commission met.",
    ],
)
def test_common_two_letter_initialism_phrases_stay_joined(text):
    for mode in ("conservative", "balanced", "aggressive"):
        assert _segments("en", text, mode) == [text]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("He left the U.S. Court resumed at noon.", ["He left the U.S.", "Court resumed at noon."]),
        ("The talks left the U.N. General replied later.", ["The talks left the U.N.", "General replied later."]),
        (
            "The report discussed the U.N. Security improved afterward.",
            ["The report discussed the U.N.", "Security improved afterward."],
        ),
        ("I went to J.C. Penney.", ["I went to J.C.", "Penney."]),
        ("The banker joined L.F. Rothschild.", ["The banker joined L.F.", "Rothschild."]),
        ("The trial involved O.J. Simpson.", ["The trial involved O.J.", "Simpson."]),
    ],
)
def test_common_initialism_phrase_prefixes_do_not_force_join(text, expected):
    assert _segments("en", text, "conservative") == [text]
    for mode in ("balanced", "aggressive"):
        assert _segments("en", text, mode) == expected


def test_split_mode_handles_i_boundary_without_royal_name_split():
    text = "We make a good team, you and I. Did you see Albert I. Jones yesterday."

    for mode in ("conservative", "balanced"):
        assert _segments("en", text, mode) == [
            "We make a good team, you and I.",
            "Did you see Albert I. Jones yesterday.",
        ]
    assert _segments("en", text, "aggressive") == [
        "We make a good team, you and I.",
        "Did you see Albert I.",
        "Jones yesterday.",
    ]


@pytest.mark.parametrize("language", ["en", "en_legal", "en_es_zh"])
def test_english_profiles_restore_standalone_i_boundary(language):
    text = "We make a good team, you and I. Did it work."

    for mode in ("conservative", "balanced", "aggressive"):
        assert _segments(language, text, mode) == ["We make a good team, you and I.", "Did it work."]


def test_split_mode_aggressive_splits_i_after_heading_like_name_continuation():
    text = "See Appendix I. It explains this."

    for mode in ("conservative", "balanced"):
        assert _segments("en", text, mode) == [text]
    assert _segments("en", text, "aggressive") == ["See Appendix I.", "It explains this."]


@pytest.mark.parametrize("text", ["We discussed H.B.S. She applied.", "F.J.G. Smith arrived."])
def test_split_mode_disambiguates_initialisms_from_names(text):
    """A capitalized follower after initials is joined only in conservative mode."""
    assert sentencesplit.Segmenter(language="en", split_mode="conservative").segment(text) == [text]
    for mode in ("balanced", "aggressive"):
        assert len(sentencesplit.Segmenter(language="en", split_mode=mode).segment(text)) == 2


@pytest.mark.parametrize(
    "text",
    [
        "Er lebt in der E.U. Für ihn ist das klar.",
    ],
)
def test_two_letter_initialism_mode_handles_non_ascii_capital_follower(text):
    language = "de"
    assert _segments(language, text, "conservative") == [text]
    for mode in ("balanced", "aggressive"):
        assert len(_segments(language, text, mode)) == 2


@pytest.mark.parametrize(
    "language,text,expected",
    [
        ("en", "I live in the U.S. How about you?", ["I live in the U.S.", "How about you?"]),
        ("da", "Jeg bor i E.U. Hvad med dig?", ["Jeg bor i E.U.", "Hvad med dig?"]),
    ],
)
def test_two_letter_initialism_splits_before_structural_question(language, text, expected):
    assert _segments(language, text, "conservative") == [text]
    for mode in ("balanced", "aggressive"):
        assert _segments(language, text, mode) == expected


@pytest.mark.parametrize(
    "text",
    [
        "The U.S. 'Who Wants to Be a Millionaire?' audience grew.",
        'The U.S. "Who Wants to Be a Millionaire?" audience grew.',
    ],
)
def test_two_letter_initialism_before_quoted_title_follows_mode(text):
    expected_split = text.replace("The U.S. ", "", 1)

    assert _segments("en", text, "conservative") == [text]
    for mode in ("balanced", "aggressive"):
        assert _segments("en", text, mode) == ["The U.S.", expected_split]


@pytest.mark.parametrize(
    "text",
    [
        "The U.S. 'who wants to be a millionaire?' audience grew.",
        'The U.S. "who wants to be a millionaire?" audience grew.',
    ],
)
def test_two_letter_initialism_before_lowercase_quoted_continuation_stays_joined(text):
    for mode in ("conservative", "balanced", "aggressive"):
        assert _segments("en", text, mode) == [text]


@pytest.mark.parametrize(
    "text,expected",
    [
        ('I live in the U.S. "How about you?" she asked.', '"How about you?" she asked.'),
        ("I live in the U.S. 'How about you?' she asked.", "'How about you?' she asked."),
    ],
)
def test_two_letter_initialism_before_quoted_dialogue_follows_mode(text, expected):

    assert _segments("en", text, "conservative") == [text]
    for mode in ("balanced", "aggressive"):
        assert _segments("en", text, mode) == ["I live in the U.S.", expected]


def test_allcaps_imprint_behavior_independent_of_capitalized_follower_split():
    for mode in ("conservative", "balanced", "aggressive"):
        assert _segments("en", "ACME CORP. ANNOUNCED RESULTS.", mode) == ["ACME CORP. ANNOUNCED RESULTS."]
        assert _segments("en", "IT HAPPENED IN DEC. THE END.", mode) == ["IT HAPPENED IN DEC.", "THE END."]


@pytest.mark.parametrize("language", ["fr", "es", "it", "pl", "nl"])
def test_non_english_profiles_use_split_mode_for_two_letter_initialisms(language):
    text = "Je vois U.S. Il part."

    assert _segments(language, text, "conservative") == [text]
    for mode in ("balanced", "aggressive"):
        assert _segments(language, text, mode) == ["Je vois U.S.", "Il part."]


def test_profile_without_capitalized_follower_cue_keeps_uppercase_continuation_joined():
    text = "Ide o firmy, napr. XYZCorp a.s."

    for mode in ("conservative", "balanced", "aggressive"):
        assert _segments("sk", text, mode) == [text]


@pytest.mark.parametrize(
    "text,joined,split",
    [
        # Multi-period initialism before a capitalized word is structurally
        # ambiguous; conservative keeps it joined, balanced/aggressive split.
        ("We discussed H.B.S. Applications are due.", ["We discussed H.B.S. Applications are due."], 2),
        ("I visited U.S.A. Microsoft is based there.", ["I visited U.S.A. Microsoft is based there."], 2),
        # The accepted trade-off: a real name splits outside conservative mode too.
        (
            "A.S.E. Ackermann and team published the findings in 2007.",
            ["A.S.E. Ackermann and team published the findings in 2007."],
            2,
        ),
    ],
)
def test_split_mode_initialism_before_capital(text, joined, split):
    # Conservative keeps the joined reading; balanced/aggressive split.
    assert sentencesplit.Segmenter(language="en", split_mode="conservative").segment(text) == joined
    for mode in ("balanced", "aggressive"):
        segmented = sentencesplit.Segmenter(language="en", split_mode=mode).segment(text)
        assert len(segmented) == split


def test_split_mode_initialism_with_strong_cue_splits_in_all_modes():
    # A determiner ("the S.A.T.") still leaves acronym/capital ambiguity to the
    # split-mode dial.
    assert sentencesplit.Segmenter(language="en", split_mode="conservative").segment(
        "I studied for the S.A.T. Tomorrow is test day."
    ) == ["I studied for the S.A.T. Tomorrow is test day."]
    for mode in ("balanced", "aggressive"):
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
        # Generic uppercase two-part initialisms use the split-mode dial, except
        # for a tiny phrase-level join list.
        ("Work on A.I. Systems are improving.", 1, 2, 2),
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
    initialism = "Met with P.M. Trudeau today."
    for mode in ("conservative", "balanced", "aggressive"):
        assert sentencesplit.Segmenter(language="en", split_mode=mode).segment(initialism) == [initialism]


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
    # en_legal STARTER_AWARE prepositive "Cir."/"Bankr.": conservative and
    # balanced keep the prepositive reading; aggressive splits before any
    # capitalized follower ("Bankr. Court" included).
    expectations = {
        "conservative": {
            "The 9th Cir. The panel reversed.": 1,
            "The 9th Cir. This panel reversed.": 1,
            "The 9th Cir. Under the statute, it reversed.": 1,
            'The 9th Cir. "The panel reversed," he wrote.': 1,
            "The 9th Cir. \u00c9lodie wrote separately.": 1,
            "The 9th Cir. (The panel reversed.)": 1,
            "The Bankr. Court approved the plan.": 1,
        },
        "balanced": {
            "The 9th Cir. The panel reversed.": 1,
            "The 9th Cir. This panel reversed.": 1,
            "The 9th Cir. Under the statute, it reversed.": 1,
            'The 9th Cir. "The panel reversed," he wrote.': 1,
            "The 9th Cir. \u00c9lodie wrote separately.": 1,
            "The 9th Cir. (The panel reversed.)": 1,
            "The Bankr. Court approved the plan.": 1,
        },
        "aggressive": {
            "The 9th Cir. The panel reversed.": 2,
            "The 9th Cir. This panel reversed.": 2,
            "The 9th Cir. Under the statute, it reversed.": 2,
            'The 9th Cir. "The panel reversed," he wrote.': 2,
            "The 9th Cir. \u00c9lodie wrote separately.": 2,
            "The 9th Cir. (The panel reversed.)": 2,
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
