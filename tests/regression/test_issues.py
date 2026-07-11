# -*- coding: utf-8 -*-
from time import perf_counter

import pytest

import sentencesplit
from sentencesplit.lang.common.standard import Standard
from sentencesplit.lists_item_replacer import ListItemReplacer
from sentencesplit.utils import TextSpan

TEST_ISSUE_DATA = [
    (
        "#27",
        "This new form of generalized PDF in (9) is generic and suitable for all the fading models presented in Table I withbranches MRC reception. In section III, (9) will be used in the derivations of the unified ABER and ACC expression.",
        [
            "This new form of generalized PDF in (9) is generic and suitable for all the fading models presented in Table I withbranches MRC reception.",
            "In section III, (9) will be used in the derivations of the unified ABER and ACC expression.",
        ],
    ),
    (
        "#29",
        "Random walk models (Skellam, 1951;Turchin, 1998) received a lot of attention and were then extended to several more mathematically and statistically sophisticated approaches to interpret movement data such as State-Space Models (SSM) (Jonsen et al., 2003(Jonsen et al., , 2005 and Brownian Bridge Movement Model (BBMM) (Horne et al., 2007). Nevertheless, these models require heavy computational resources (Patterson et al., 2008) and unrealistic structural a priori hypotheses about movement, such as homogeneous movement behavior. A fundamental property of animal movements is behavioral heterogeneity (Gurarie et al., 2009) and these models poorly performed in highlighting behavioral changes in animal movements through space and time (Kranstauber et al., 2012).",
        [
            "Random walk models (Skellam, 1951;Turchin, 1998) received a lot of attention and were then extended to several more mathematically and statistically sophisticated approaches to interpret movement data such as State-Space Models (SSM) (Jonsen et al., 2003(Jonsen et al., , 2005 and Brownian Bridge Movement Model (BBMM) (Horne et al., 2007).",
            "Nevertheless, these models require heavy computational resources (Patterson et al., 2008) and unrealistic structural a priori hypotheses about movement, such as homogeneous movement behavior.",
            "A fundamental property of animal movements is behavioral heterogeneity (Gurarie et al., 2009) and these models poorly performed in highlighting behavioral changes in animal movements through space and time (Kranstauber et al., 2012).",
        ],
    ),
    (
        "#30",
        "Thus, we first compute EMC 3 's response time-i.e., the duration from the initial of a call (from/to a participant in the target region) to the time when the decision of task assignment is made; and then, based on the computed response time, we estimate EMC 3 maximum throughput [28]-i.e., the maximum number of mobile users allowed in the MCS system. EMC 3 algorithm is implemented with the Java SE platform and is running on a Java HotSpot(TM) 64-Bit Server VM; and the implementation details are given in Appendix, available in the online supplemental material.",
        [
            "Thus, we first compute EMC 3 's response time-i.e., the duration from the initial of a call (from/to a participant in the target region) to the time when the decision of task assignment is made; and then, based on the computed response time, we estimate EMC 3 maximum throughput [28]-i.e., the maximum number of mobile users allowed in the MCS system.",
            "EMC 3 algorithm is implemented with the Java SE platform and is running on a Java HotSpot(TM) 64-Bit Server VM; and the implementation details are given in Appendix, available in the online supplemental material.",
        ],
    ),
    (
        "#31",
        r"Proof. First let v ∈ V be incident to at least three leaves and suppose there is a minimum power dominating set S of G that does not contain v. If S excludes two or more of the leaves of G incident to v, then those leaves cannot be dominated or forced at any step. Thus, S excludes at most one leaf incident to v, which means S contains at least two leaves ℓ 1 and ℓ 2 incident to v. Then, (S\{ℓ 1 , ℓ 2 }) ∪ {v} is a smaller power dominating set than S, which is a contradiction. Now consider the case in which v ∈ V is incident to exactly two leaves, ℓ 1 and ℓ 2 , and suppose there is a minimum power dominating set S of G such that {v, ℓ 1 , ℓ 2 } ∩ S = ∅. Then neither ℓ 1 nor ℓ 2 can be dominated or forced at any step, contradicting the assumption that S is a power dominating set. If S is a power dominating set that contains ℓ 1 or ℓ 2 , say ℓ 1 , then (S\{ℓ 1 }) ∪ {v} is also a power dominating set and has the same cardinality. Applying this to every vertex incident to exactly two leaves produces the minimum power dominating set required by (3). Definition 3.4. Given a graph G = (V, E) and a set X ⊆ V , define ℓ r (G, X) as the graph obtained by attaching r leaves to each vertex in X. If X = {v 1 , . . . , v k }, we denote the r leaves attached to vertex v i as ℓ",
        [
            "Proof.",
            "First let v ∈ V be incident to at least three leaves and suppose there is a minimum power dominating set S of G that does not contain v. If S excludes two or more of the leaves of G incident to v, then those leaves cannot be dominated or forced at any step.",
            "Thus, S excludes at most one leaf incident to v, which means S contains at least two leaves ℓ 1 and ℓ 2 incident to v. Then, (S\\{ℓ 1 , ℓ 2 }) ∪ {v} is a smaller power dominating set than S, which is a contradiction.",
            "Now consider the case in which v ∈ V is incident to exactly two leaves, ℓ 1 and ℓ 2 , and suppose there is a minimum power dominating set S of G such that {v, ℓ 1 , ℓ 2 } ∩ S = ∅.",
            "Then neither ℓ 1 nor ℓ 2 can be dominated or forced at any step, contradicting the assumption that S is a power dominating set.",
            "If S is a power dominating set that contains ℓ 1 or ℓ 2 , say ℓ 1 , then (S\\{ℓ 1 }) ∪ {v} is also a power dominating set and has the same cardinality.",
            "Applying this to every vertex incident to exactly two leaves produces the minimum power dominating set required by (3).",
            "Definition 3.4.",
            "Given a graph G = (V, E) and a set X ⊆ V , define ℓ r (G, X) as the graph obtained by attaching r leaves to each vertex in X. If X = {v 1 , . . . , v k }, we denote the r leaves attached to vertex v i as ℓ",
        ],
    ),
    ("#34", ".", ["."]),
    ("#34", "..", [".."]),
    ("#34", ". . .", [". . ."]),
    ("#34", "! ! !", ["! ! !"]),
    ("#36", "??", ["??"]),
    (
        "#37",
        "As an example of a different special-purpose mechanism, we have introduced a methodology for letting donors make their donations to charities conditional on donations by other donors (who, in turn, can make their donations conditional) [70]. We have used this mechanism to collect money for Indian Ocean Tsunami and Hurricane Katrina victims. We have also introduced a more general framework for negotiation when one agent's actions have a direct effect (externality) on the other agents' utilities [69]. Both the charities and externalities methodologies require the solution of NP-hard optimization problems in general, but there are some natural tractable cases as well as effective MIP formulations. Recently, Ghosh and Mahdian [86] at Yahoo! Research extended our charities work, and based on this a web-based system for charitable donations was built at Yahoo!",
        [
            "As an example of a different special-purpose mechanism, we have introduced a methodology for letting donors make their donations to charities conditional on donations by other donors (who, in turn, can make their donations conditional) [70].",
            "We have used this mechanism to collect money for Indian Ocean Tsunami and Hurricane Katrina victims.",
            "We have also introduced a more general framework for negotiation when one agent's actions have a direct effect (externality) on the other agents' utilities [69].",
            "Both the charities and externalities methodologies require the solution of NP-hard optimization problems in general, but there are some natural tractable cases as well as effective MIP formulations.",
            "Recently, Ghosh and Mahdian [86] at Yahoo! Research extended our charities work, and based on this a web-based system for charitable donations was built at Yahoo!",
        ],
    ),
    (
        "#39",
        "T stands for the vector transposition. As shown in Fig. ??",
        ["T stands for the vector transposition.", "As shown in Fig. ??"],
    ),
    ("#39", "Fig. ??", ["Fig. ??"]),
    (
        "#58",
        "Rok bud.2027777983834843834843042003200220012000199919981997199619951994199319921991199019891988198042003200220012000199919981997199619951994199319921991199019891988198",
        [
            "Rok bud.2027777983834843834843042003200220012000199919981997199619951994199319921991199019891988198042003200220012000199919981997199619951994199319921991199019891988198"
        ],
    ),
]

TEST_ISSUE_DATA_CHAR_SPANS = [
    ("#49", "1) The first item. 2) The second item.", [("1) The first item. ", 0, 19), ("2) The second item.", 19, 38)]),
    (
        "#49",
        "a. The first item. b. The second item. c. The third list item",
        [("a. The first item. ", 0, 19), ("b. The second item. ", 19, 39), ("c. The third list item", 39, 61)],
    ),
    (
        "#53",
        "Trust in journalism is not associated with frequency of media use (except in the case of television as mentioned above), indicating that trust is not an important predictor of media use, though it might have an important impact on information processing. This counterintuitive fi nding can be explained by taking into account the fact that audiences do not watch informative content merely to inform themselves; they have other motivations that might override credibility concerns. For example, they might follow media primarily for entertainment purposes and consequently put less emphasis on the quality of the received information.As <|CITE|> have claimed, audiences tend to approach and process information differently depending on the channel; they approach television primarily for entertainment and newspapers primarily for information. This has implications for trust as well since audiences in an entertainment processing mode will be less attentive to credibility cues, such as news errors, than those in an information processing mode (Ibid.). <|CITE|> research confi rms this claim -he found that audiences tend to approach newspaper reading more actively than television viewing and that credibility assessments differ regarding whether audience members approach news actively or passively. These fi ndings can help explain why we found a weak positive correlation between television news exposure and trust in journalism. It could be that audiences turn to television not because they expect the best quality information but rather the opposite -namely, that they approach television news less critically, focus less attention on credibility concerns and, therefore, develop a higher degree of trust in journalism. The fact that those respondents who follow the commercial television channel POP TV and the tabloid Slovenske Novice exhibit a higher trust in journalistic objectivity compared to those respondents who do not follow these media is also in line with this interpretation. The topic of Janez Janša and exposure to media that are favourable to him and his SDS party is negatively connected to trust in journalism. This phenomenon can be partly explained by the elaboration likelihood model <|CITE|> , according to which highly involved individuals tend to process new information in a way that maintains and confi rms their original opinion by 1) taking information consistent with their views (information that falls within a narrow range of acceptance) as simply veridical and embracing it, and 2) judging counter-attitudinal information to be the product of biased, misguided or ill-informed sources and rejecting it <|CITE|> <|CITE|> . Highly partisan audiences will, therefore, tend to react to dissonant information by lowering the trustworthiness assessment of the source of such information.",
        [
            (
                "Trust in journalism is not associated with frequency of media use (except in the case of television as mentioned above), indicating that trust is not an important predictor of media use, though it might have an important impact on information processing. ",
                0,
                255,
            ),
            (
                "This counterintuitive fi nding can be explained by taking into account the fact that audiences do not watch informative content merely to inform themselves; they have other motivations that might override credibility concerns. ",
                255,
                482,
            ),
            (
                "For example, they might follow media primarily for entertainment purposes and consequently put less emphasis on the quality of the received information.As <|CITE|> have claimed, audiences tend to approach and process information differently depending on the channel; they approach television primarily for entertainment and newspapers primarily for information. ",
                482,
                844,
            ),
            (
                "This has implications for trust as well since audiences in an entertainment processing mode will be less attentive to credibility cues, such as news errors, than those in an information processing mode (Ibid.). ",
                844,
                1055,
            ),
            (
                "<|CITE|> research confi rms this claim -he found that audiences tend to approach newspaper reading more actively than television viewing and that credibility assessments differ regarding whether audience members approach news actively or passively. ",
                1055,
                1304,
            ),
            (
                "These fi ndings can help explain why we found a weak positive correlation between television news exposure and trust in journalism. ",
                1304,
                1436,
            ),
            (
                "It could be that audiences turn to television not because they expect the best quality information but rather the opposite -namely, that they approach television news less critically, focus less attention on credibility concerns and, therefore, develop a higher degree of trust in journalism. ",
                1436,
                1729,
            ),
            (
                "The fact that those respondents who follow the commercial television channel POP TV and the tabloid Slovenske Novice exhibit a higher trust in journalistic objectivity compared to those respondents who do not follow these media is also in line with this interpretation. ",
                1729,
                1999,
            ),
            (
                "The topic of Janez Janša and exposure to media that are favourable to him and his SDS party is negatively connected to trust in journalism. ",
                1999,
                2139,
            ),
            (
                "This phenomenon can be partly explained by the elaboration likelihood model <|CITE|> , according to which highly involved individuals tend to process new information in a way that maintains and confi rms their original opinion by ",
                2139,
                2369,
            ),
            (
                "1) taking information consistent with their views (information that falls within a narrow range of acceptance) as simply veridical and embracing it, and ",
                2369,
                2522,
            ),
            (
                "2) judging counter-attitudinal information to be the product of biased, misguided or ill-informed sources and rejecting it <|CITE|> <|CITE|> . ",
                2522,
                2665,
            ),
            (
                "Highly partisan audiences will, therefore, tend to react to dissonant information by lowering the trustworthiness assessment of the source of such information.",
                2665,
                2824,
            ),
        ],
    ),
    (
        "#55",
        'She turned to him, "This is great." She held the book out to show him.',
        [('She turned to him, "This is great." ', 0, 36), ("She held the book out to show him.", 36, 70)],
    ),
    (
        "#56",
        """This eBook is for the use of anyone anywhere at no cost
you may copy it, give it away or re-use it under the terms of the this license
""",
        [
            ("This eBook is for the use of anyone anywhere at no cost\n", 0, 56),
            ("you may copy it, give it away or re-use it under the terms of the this license\n", 56, 135),
        ],
    ),
    (
        "#78",
        "Sentence. .. Next sentence. Next next sentence.",
        [("Sentence. ", 0, 10), (".. ", 10, 13), ("Next sentence. ", 13, 28), ("Next next sentence.", 28, 47)],
    ),
    (
        "#83",
        "Maissen se chargea du reste .. Logiquement,",
        [("Maissen se chargea du reste .", 0, 29), (". ", 29, 31), ("Logiquement,", 31, 43)],
    ),
    (
        "#83",
        "Maissen se chargea du reste ... Logiquement,",
        [("Maissen se chargea du reste ... ", 0, 32), ("Logiquement,", 32, 44)],
    ),
    pytest.param(
        "#83",
        "Maissen se chargea du reste .... Logiquement,",
        [("Maissen se chargea du reste .", 0, 29), ("... ", 29, 33), ("Logiquement,", 33, 45)],
        marks=pytest.mark.xfail(
            reason="BACKLOG[xfail-index]: issue-83-four-dot-ellipsis — a 4-dot run '....' (sentence period +"
            " 3-dot ellipsis) is not yet split into 'word .' + '... '; the 2-dot and 3-dot siblings above pass."
            " DO NOT DELETE: dropping this would leave the suite asserting a model inconsistent with those"
            " passing siblings. Re-adjudicate as its own scoped task."
        ),
    ),
]


@pytest.mark.parametrize("language", ["mr", "fr", "it", "pl", "es", "nl"])
def test_non_english_two_letter_initialism_follows_split_mode(language):
    """Latin-script non-English profiles route two-letter initialisms through split_mode."""
    text = "Je vois U.S. Il part."

    seg = sentencesplit.Segmenter(language=language, clean=False, split_mode="conservative")
    assert [s.strip() for s in seg.segment(text)] == [text]
    for mode in ("balanced", "aggressive"):
        seg = sentencesplit.Segmenter(language=language, clean=False, split_mode=mode)
        assert [s.strip() for s in seg.segment(text)] == ["Je vois U.S.", "Il part."]


@pytest.mark.parametrize("language", ["zh", "ja", "nl", "it", "mr"])
def test_non_english_two_letter_initialism_before_i_follows_split_mode(language):
    """Classifier-protected initialisms still respect the downstream split dial."""
    text = "Je vois U.S. I went."

    seg = sentencesplit.Segmenter(language=language, clean=False, split_mode="conservative")
    assert [s.strip() for s in seg.segment(text)] == [text]
    for mode in ("balanced", "aggressive"):
        seg = sentencesplit.Segmenter(language=language, clean=False, split_mode=mode)
        assert [s.strip() for s in seg.segment(text)] == ["Je vois U.S.", "I went."]


@pytest.mark.parametrize("language", ["fr", "es", "it", "nl"])
def test_non_english_profiles_do_not_inherit_uppercase_abbreviation_heuristic(language):
    """Removing empty overrides must not expose English-oriented Standard flags."""
    seg = sentencesplit.Segmenter(language=language, clean=False)

    assert [s.strip() for s in seg.segment("Voir fig. I maintenant.")] == ["Voir fig. I maintenant."]


def test_fig_number_abbreviation():
    """Fig. should split before text but not before numbers."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    # Fig. before a new sentence should split
    segments = [s.strip() for s in seg.segment("See Fig. The answer is clear.")]
    assert segments == ["See Fig.", "The answer is clear."]
    # Fig. before a number should not split
    segments = [s.strip() for s in seg.segment("See Fig. 5 for details.")]
    assert segments == ["See Fig. 5 for details."]


def test_spanish_sta_sto_prepositive():
    """Sta./Sto. abbreviations should not split before the place/saint name."""
    seg = sentencesplit.Segmenter(language="es", clean=False)
    segments = [s.strip() for s in seg.segment("Vive en Sta. Cruz. Después se mudó.")]
    assert segments == ["Vive en Sta. Cruz.", "Después se mudó."]
    segments = [s.strip() for s in seg.segment("Fue a Sto. Domingo y Sta. Rosa.")]
    assert segments == ["Fue a Sto. Domingo y Sta. Rosa."]


def test_period_before_comma_is_not_a_sentence_boundary():
    """A period immediately followed by a comma must not split a sentence.

    The multi-period botanical author abbreviation 'N.E.Br.' is not in any
    abbreviation list, so its final period was left as a boundary candidate
    and fired even though the next non-space character is a comma. A comma can
    never start a new sentence, so the period must stay inside the sentence.
    """
    seg = sentencesplit.Segmenter(language="es", clean=False)
    text = "Su única especie: Didymaotus lapidiformis (Marloth) N.E.Br., es originaria de Sudáfrica."
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == ["Su única especie: Didymaotus lapidiformis (Marloth) N.E.Br., es originaria de Sudáfrica."]


def test_period_before_dutch_opening_quote_still_splits():
    """The period-before-comma protection must NOT swallow a Dutch opening quote.

    Dutch typography uses a doubled comma (",,") as an *opening* quotation mark,
    so a period before ",," ends a real sentence. The period-before-comma rule
    therefore excludes a doubled comma; only a single comma protects the period.
    """
    seg = sentencesplit.Segmenter(language="nl", clean=False)
    text = "Dat was het einde. ,,Een nieuwe zin begint hier. En nog een zin."
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == [
        "Dat was het einde.",
        ",,Een nieuwe zin begint hier.",
        "En nog een zin.",
    ]


def test_versus_abbreviation_not_treated_as_list_item():
    """v. in case names like 'Marbury v. Madison' should not be split as a list item."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    # v. next to U.S. triggered false alphabetical list detection (u, v adjacent in alphabet)
    text = "In Marbury v. Madison, 5 U.S. 137 (1803), the Court established judicial review. This was a landmark case."
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == [
        "In Marbury v. Madison, 5 U.S. 137 (1803), the Court established judicial review.",
        "This was a landmark case.",
    ]
    # Should also work without nearby single-letter abbreviations
    text2 = "The ruling in Roe v. Wade was significant. It changed the legal landscape."
    segments2 = [s.strip() for s in seg.segment(text2)]
    assert segments2 == [
        "The ruling in Roe v. Wade was significant.",
        "It changed the legal landscape.",
    ]


def test_descending_alphabetical_sequences_not_treated_as_list_items():
    """Reverse-order letters should not be rewritten as alphabetical list markers."""
    text = "Discussion of v. Wade case and then u. other matter."
    assert ListItemReplacer(text).add_line_break() == text


def test_hyphen_prefixed_numbered_period_paren_list_items_split():
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = [s.strip() for s in seg.segment("-1.) The first item -2.) The second item")]
    assert segments == ["-1.) The first item", "-2.) The second item"]


def test_german_consecutive_ordinals_not_treated_as_numbered_list():
    """Two nearby ascending ordinals embedded in prose ('19. ... 20. Jahrhunderts')
    must not be promoted to a numbered list."""
    seg = sentencesplit.Segmenter(language="de", clean=False)
    text = "Im Laufe des 19. und frühen 20. Jahrhunderts entwickelte sich Berlin zur weltweit drittgrößten Stadt."
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == [text]


@pytest.mark.parametrize("split_mode", ["conservative", "balanced"])
def test_german_ordinal_range_not_treated_as_numbered_list(split_mode):
    text = "Die Sammlung umfasst Werke vom 19. bis 20. Jahrhundert."
    seg = sentencesplit.Segmenter(language="de", clean=False, split_mode=split_mode)

    assert [s.strip() for s in seg.segment(text)] == [text]


def test_german_ordinal_range_before_later_list_does_not_split_inside_range():
    text = "Die Sammlung umfasst Werke vom 19. bis 20. Jahrhundert. 1. apple 2. banana"
    seg = sentencesplit.Segmenter(language="de", clean=False)

    assert [s.strip() for s in seg.segment(text)] == [
        "Die Sammlung umfasst Werke vom 19. bis 20. Jahrhundert.",
        "1. apple",
        "2. banana",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Die Ausstellung zeigt Werke des 19. sowie 20. Jahrhunderts.",
        "Die Ausstellung zeigt Werke des 19. bzw. 20. Jahrhunderts.",
    ],
)
def test_german_ordinal_prose_connectors_not_treated_as_numbered_lists(text):
    seg = sentencesplit.Segmenter(language="de", clean=False)

    assert [s.strip() for s in seg.segment(text)] == [text]


def test_consecutive_ordinals_followed_by_lowercase_not_a_list():
    """Embedded ordinals followed by prose connectors are not list markers, so
    no line break ('\\r') is inserted to split them into list items. The ordinal
    periods are still protected (replaced with the placeholder), which keeps the
    text from splitting downstream."""
    text = "Im Laufe des 19. und frühen 20. Jahrhunderts entwickelte sich Berlin."
    result = ListItemReplacer(text).add_line_break()
    assert "\r" not in result and "\n" not in result


def test_lowercase_numbered_list_items_split():
    """Lowercase item text is still a real numbered list, not prose ordinal text."""
    for text in ("1. apple 2. banana", "1. and gates 2. or gates"):
        assert ListItemReplacer(text).add_line_break().count("\r") == 1

        seg = sentencesplit.Segmenter(language="en", clean=False)
        assert [s.strip() for s in seg.segment(text)] == [text.split(" 2. ")[0], "2. " + text.split(" 2. ")[1]]


def test_lowercase_numbered_list_item_does_not_suppress_later_boundaries():
    """A lowercase item at the start must not globally suppress every list break."""
    text = "1. apple 2. Banana 3. Cherry"
    assert ListItemReplacer(text).add_line_break() == "1∯ apple\r2∯ Banana\r3∯ Cherry"


def test_common_abbreviations_no_false_split():
    """Common abbreviations like govt., approx., misc. should not cause false splits."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    # Before lowercase words
    assert [s.strip() for s in seg.segment("The govt. issued new regulations. They take effect Monday.")] == [
        "The govt. issued new regulations.",
        "They take effect Monday.",
    ]
    assert [s.strip() for s in seg.segment("The natl. average rose sharply. Experts were surprised.")] == [
        "The natl. average rose sharply.",
        "Experts were surprised.",
    ]
    assert [s.strip() for s in seg.segment("See the misc. expenses below. They total five thousand.")] == [
        "See the misc. expenses below.",
        "They total five thousand.",
    ]
    assert [s.strip() for s in seg.segment("The avg. score was 85 points. Students improved overall.")] == [
        "The avg. score was 85 points.",
        "Students improved overall.",
    ]
    assert [s.strip() for s in seg.segment("The max. capacity is 500 people. Do not exceed it.")] == [
        "The max. capacity is 500 people.",
        "Do not exceed it.",
    ]
    assert [s.strip() for s in seg.segment("The orig. version was better. Fans agreed unanimously.")] == [
        "The orig. version was better.",
        "Fans agreed unanimously.",
    ]
    # Before numbers (NUMBER_ABBREVIATIONS)
    assert [s.strip() for s in seg.segment("It costs approx. 50 dollars. That is affordable.")] == [
        "It costs approx. 50 dollars.",
        "That is affordable.",
    ]
    assert [s.strip() for s in seg.segment("See vol. 3 for the full analysis. It was published last year.")] == [
        "See vol. 3 for the full analysis.",
        "It was published last year.",
    ]
    assert [s.strip() for s in seg.segment("Contact us at tel. 555-1234 for information. We are open daily.")] == [
        "Contact us at tel. 555-1234 for information.",
        "We are open daily.",
    ]
    assert [s.strip() for s in seg.segment("The town was est. 1842 by settlers. It grew quickly.")] == [
        "The town was est. 1842 by settlers.",
        "It grew quickly.",
    ]
    # Should still split at real sentence boundaries
    assert [s.strip() for s in seg.segment("The govt. The rules are strict.")] == [
        "The govt.",
        "The rules are strict.",
    ]
    # Before Roman numerals (NUMBER_ABBREVIATIONS)
    assert [s.strip() for s in seg.segment("See vol. IV for details. It covers the topic.")] == [
        "See vol. IV for details.",
        "It covers the topic.",
    ]
    assert [s.strip() for s in seg.segment("See vol. III of the series. It was published last.")] == [
        "See vol. III of the series.",
        "It was published last.",
    ]
    assert [s.strip() for s in seg.segment("Refer to art. XII of the constitution. It addresses due process.")] == [
        "Refer to art. XII of the constitution.",
        "It addresses due process.",
    ]
    assert [s.strip() for s in seg.segment("See vol. V for appendices. They contain raw data.")] == [
        "See vol. V for appendices.",
        "They contain raw data.",
    ]
    # Roman numeral should not match regular words starting with I, V, etc.
    assert [s.strip() for s in seg.segment("See vol. Instead, we should proceed. That was the plan.")] == [
        "See vol.",
        "Instead, we should proceed.",
        "That was the plan.",
    ]


def test_double_punctuation_after_sentence_boundary():
    """Double punctuation (??, !!, ?!, !?) should not be lost after a sentence boundary."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert [s.strip() for s in seg.segment("Hello. ??")] == ["Hello.", "??"]
    assert [s.strip() for s in seg.segment("Hello. !!")] == ["Hello.", "!!"]
    assert [s.strip() for s in seg.segment("Hello. ?!")] == ["Hello.", "?!"]
    assert [s.strip() for s in seg.segment("Hello. !?")] == ["Hello.", "!?"]


@pytest.mark.parametrize("issue_no,text,expected_sents", TEST_ISSUE_DATA)
def test_issue(issue_no, text, expected_sents):
    """pySBD issues tests from https://github.com/nipunsadvilkar/pySBD/issues/"""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = seg.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
    # clubbing sentences and matching with original text
    assert text == " ".join(segments)


def test_english_smart_quotes_unaffected():
    """Verify English smart-quote segmentation is not broken by CJK changes to common.py."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    text = "He said \u201cHello.\u201d She replied \u201cGoodbye.\u201d"
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == ["He said \u201cHello.\u201d", "She replied \u201cGoodbye.\u201d"]


@pytest.mark.parametrize("issue_no,text,expected_sents_w_spans", TEST_ISSUE_DATA_CHAR_SPANS)
def test_issues_with_char_spans(issue_no, text, expected_sents_w_spans):
    """pySBD issues tests from https://github.com/nipunsadvilkar/pySBD/issues/"""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = seg.segment_spans(text)
    expected_text_spans = [TextSpan(sent_w_span[0], sent_w_span[1], sent_w_span[2]) for sent_w_span in expected_sents_w_spans]
    assert segments == expected_text_spans
    # clubbing sentences and matching with original text
    assert text == "".join([seg.sent for seg in segments])


@pytest.mark.parametrize(
    "language,text,expected",
    [
        (
            "zh",
            "\u5979\u8bf4\uff1a\u201c\u4f60\u597d\u3002\u201d abc\u5f00\u59cb\u3002",
            ["\u5979\u8bf4\uff1a\u201c\u4f60\u597d\u3002\u201d", "abc\u5f00\u59cb\u3002"],
        ),
        (
            "ja",
            "\u5f7c\u306f\u300c\u3053\u3093\u306b\u3061\u306f\u3002\u300d abc\u3068\u8a00\u3063\u305f\u3002",
            ["\u5f7c\u306f\u300c\u3053\u3093\u306b\u3061\u306f\u3002\u300d", "abc\u3068\u8a00\u3063\u305f\u3002"],
        ),
        (
            "ja",
            "\u5f7c\u306f\u300c\u3053\u3093\u306b\u3061\u306f\u3002\u300d 123\u3068\u8a00\u3063\u305f\u3002",
            ["\u5f7c\u306f\u300c\u3053\u3093\u306b\u3061\u306f\u3002\u300d", "123\u3068\u8a00\u3063\u305f\u3002"],
        ),
    ],
)
def test_cjk_quote_splitting_not_gated_by_uppercase(language, text, expected):
    """CJK closing-quote boundaries must split without requiring an uppercase start."""
    seg = sentencesplit.Segmenter(language=language, clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_compact_ampm_before_non_ascii_uppercase():
    """Compact 6p.m. form should split before non-ASCII uppercase sentence starts."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert [s.strip() for s in seg.segment("He left at 6p.m. \u00c9lodie arrived.")] == [
        "He left at 6p.m.",
        "\u00c9lodie arrived.",
    ]


def test_bare_ampm_initialism_before_name_stays_joined():
    """Without a preceding number, P.M./A.M. is a generic two-part initialism."""
    for text in ("Met with P.M. Trudeau today.", "The A.M. Smith papers arrived."):
        for mode in ("conservative", "balanced", "aggressive"):
            seg = sentencesplit.Segmenter(language="en", clean=False, split_mode=mode)
            assert [s.strip() for s in seg.segment(text)] == [text]


def test_eq_abbreviation_before_roman_numeral():
    """Eq. before a Roman numeral should stay joined like Fig."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert [s.strip() for s in seg.segment("Eq. IV shows the result. Next sentence.")] == [
        "Eq. IV shows the result.",
        "Next sentence.",
    ]


def test_pt_abbreviation_before_roman_numeral():
    """Pt. before a Roman numeral should stay joined (number abbreviation)."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert [s.strip() for s in seg.segment("Pt. II discusses methods. Next sentence.")] == [
        "Pt. II discusses methods.",
        "Next sentence.",
    ]


def test_two_letter_initialism_before_non_ascii_uppercase_follows_split_mode():
    """Two-letter initialisms split before capital followers using split_mode."""
    text = "He moved from the U.S. \u00c9lodie arrived."

    seg = sentencesplit.Segmenter(language="en", clean=False, split_mode="conservative")
    assert [s.strip() for s in seg.segment(text)] == [text]

    for mode in ("balanced", "aggressive"):
        seg = sentencesplit.Segmenter(language="en", clean=False, split_mode=mode)
        assert [s.strip() for s in seg.segment(text)] == ["He moved from the U.S.", "\u00c9lodie arrived."]


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "He earned a Ph.D. \u4e2d\u6587\u5f00\u59cb\u3002",
            ["He earned a Ph.D. \u4e2d\u6587\u5f00\u59cb\u3002"],
        ),
        (
            "He left at 6 p.m. \u4e2d\u6587\u5f00\u59cb\u3002",
            ["He left at 6 p.m. \u4e2d\u6587\u5f00\u59cb\u3002"],
        ),
    ],
)
def test_en_es_zh_latin_abbreviation_before_cjk(text, expected):
    """Latin abbreviations in en_es_zh stay joined before CJK continuations —
    CJK chars are not reliable sentence-start signals for abbreviation boundary logic."""
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Bring paper, pens, etc. \u4e2d\u6587\u7ee7\u7eed\u3002",
            ["Bring paper, pens, etc. \u4e2d\u6587\u7ee7\u7eed\u3002"],
        ),
        (
            "Met at Univ. \u4e2d\u6587\u5b66\u9662\u3002",
            ["Met at Univ. \u4e2d\u6587\u5b66\u9662\u3002"],
        ),
    ],
)
def test_en_es_zh_ordinary_abbreviation_before_cjk_stays_joined(text, expected):
    """Ordinary English abbreviations (etc., Univ.) in en_es_zh must NOT split
    before CJK continuations — CJK text is not a sentence-start signal."""
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_three_part_initialism_before_non_ascii_uppercase_follows_split_mode():
    """Non-ASCII Latin capitals are still capital followers for the acronym dial."""
    text = "He works for the U.S.A. \u00c9lodie Foundation."

    seg = sentencesplit.Segmenter(language="en", clean=False, split_mode="conservative")
    assert [s.strip() for s in seg.segment(text)] == [text]

    for mode in ("balanced", "aggressive"):
        seg = sentencesplit.Segmenter(language="en", clean=False, split_mode=mode)
        assert [s.strip() for s in seg.segment(text)] == [
            "He works for the U.S.A.",
            "\u00c9lodie Foundation.",
        ]


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Substituting into Eq. 5 yields the result. The proof is complete.",
            ["Substituting into Eq. 5 yields the result.", "The proof is complete."],
        ),
        ("Pt. presented for evaluation. Results pending.", ["Pt. presented for evaluation.", "Results pending."]),
    ],
)
def test_en_es_zh_number_abbreviations_before_lowercase(text, expected):
    """Number abbreviations (eq, pt) in en_es_zh must stay joined before lowercase text."""
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize("split_mode", ["conservative", "balanced", "aggressive"])
def test_en_es_zh_number_abbreviation_before_unknown_placeholder(split_mode):
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False, split_mode=split_mode)

    assert [s.strip() for s in seg.segment("As shown in Fig. ??")] == ["As shown in Fig. ??"]


@pytest.mark.parametrize("language", ["en", "en_es_zh"])
@pytest.mark.parametrize(
    "text,expected",
    [
        ("Fig. ?? is missing. Done.", ["Fig. ?? is missing.", "Done."]),
        ("As shown in Fig. ??, the curve rises. Done.", ["As shown in Fig. ??, the curve rises.", "Done."]),
    ],
)
def test_number_abbreviation_unknown_placeholder_continuations(language, text, expected):
    seg = sentencesplit.Segmenter(language=language, clean=False)

    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize("language", ["en", "en_es_zh"])
def test_number_abbreviation_does_not_partially_attach_long_question_run(language):
    seg = sentencesplit.Segmenter(language=language, clean=False)
    segments = [s.strip() for s in seg.segment("Fig. ???")]

    assert segments[0] == "Fig."
    assert "".join(segments[1:]) == "???"


def test_greek_uppercase_not_treated_as_sentence_start():
    """Greek/Cyrillic uppercase (e.g. Δ) should not trigger sentence splits —
    only accented Latin uppercase (e.g. É) should."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert [s.strip() for s in seg.segment("The reading was taken at 6 p.m. ΔF508 remained detectable.")] == [
        "The reading was taken at 6 p.m. ΔF508 remained detectable.",
    ]


def test_en_es_zh_accented_uppercase_splits_after_number_abbreviation():
    """Accented uppercase starters like Él must split after number abbreviations in en_es_zh."""
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False)
    assert [s.strip() for s in seg.segment("Fig. Él explica el resultado. Siguiente.")] == [
        "Fig.",
        "Él explica el resultado.",
        "Siguiente.",
    ]


@pytest.mark.parametrize(
    "language,text,expected",
    [
        ("en", 'The abbreviation is "etc." 中文里也常见。', ['The abbreviation is "etc." 中文里也常见。']),
        ("fr", 'The abbreviation is "etc." 中文里也常见。', ['The abbreviation is "etc." 中文里也常见。']),
        ("es", 'The abbreviation is "etc." 中文里也常见。', ['The abbreviation is "etc." 中文里也常见。']),
    ],
)
def test_latin_quote_resplit_not_triggered_by_cjk(language, text, expected):
    """Latin profiles must not resplit after quoted punctuation before CJK text."""
    seg = sentencesplit.Segmenter(language=language, clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Bring paper, pens, etc. český text continued.",
            ["Bring paper, pens, etc. český text continued."],
        ),
        (
            "Bring paper, pens, etc. ΔF508 remained detectable.",
            ["Bring paper, pens, etc. ΔF508 remained detectable."],
        ),
        (
            "Meet at Univ. český text continued.",
            ["Meet at Univ. český text continued."],
        ),
    ],
)
def test_en_es_zh_abbreviation_protection_for_non_latin1_letters(text, expected):
    """en_es_zh abbreviation protection must cover non-Latin-1 letters like č and Δ."""
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        # Lone trailing U+200B (Wikipedia reference marker) must not survive as a phantom sentence.
        ("Texto.​", ["Texto."]),
        (
            "siendo la 1.ª área metropolitana española en actividad económica −19 % del PIB.​",
            ["siendo la 1.ª área metropolitana española en actividad económica −19 % del PIB."],
        ),
        # Mid-text U+200B must not be folded into the FOLLOWING sentence as a leading char.
        (
            "Frase uno.​ Frase dos.​",
            ["Frase uno.", "Frase dos."],
        ),
        (
            "En sus Novelas ejemplares, Cervantes dice ser tartamudo. "
            "Para José Manuel Lucía Megías, se trataría de una figura retórica "
            "para describirse a sí mismo como falto de elocuencia verbal.​ "
            "Krzysztof Sliwa, por el contrario, cree que Cervantes padecía una verdadera "
            "alteración del lenguaje, citando similares comentarios del manchego en tres de "
            "sus escritos además de las Novelas.​",
            [
                "En sus Novelas ejemplares, Cervantes dice ser tartamudo.",
                "Para José Manuel Lucía Megías, se trataría de una figura retórica "
                "para describirse a sí mismo como falto de elocuencia verbal.",
                "Krzysztof Sliwa, por el contrario, cree que Cervantes padecía una verdadera "
                "alteración del lenguaje, citando similares comentarios del manchego en tres de "
                "sus escritos además de las Novelas.",
            ],
        ),
    ],
)
def test_trailing_zero_width_space_not_emitted_as_sentence(text, expected):
    """Wikipedia U+200B reference markers must not produce phantom/leading-char sentences."""
    seg = sentencesplit.Segmenter(language="es", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        # "и др." (etc.) and the inline language tags must not split.
        (
            "Чувашское книжное издательство -- республиканское государственное унитарное "
            "предприятие, выпускающее художественную, детскую, учебно-педагогическую, "
            "общественно-политическую и др. литературу на чуваш., рус., англ. языках.",
            [
                "Чувашское книжное издательство -- республиканское государственное унитарное "
                "предприятие, выпускающее художественную, детскую, учебно-педагогическую, "
                "общественно-политическую и др. литературу на чуваш., рус., англ. языках."
            ],
        ),
        # "Ср." (cf.) at the start of a sentence must not split.
        (
            "Ср. с иконографией ``Муж скорбей&#39;&#39;, где ангелы придерживают израненное "
            "тело Христа, но не умершего, а живого, так как это является не сценой "
            "погребения, а аллегорическим изображением.",
            [
                "Ср. с иконографией ``Муж скорбей&#39;&#39;, где ангелы придерживают израненное "
                "тело Христа, но не умершего, а живого, так как это является не сценой "
                "погребения, а аллегорическим изображением."
            ],
        ),
        # Language-tag abbreviations introducing a Latin-capital gloss must stay non-terminal.
        (
            "откуда в иностранных языках возникли названия типа англ. Moscow, нем. Moskau, фр. Moscou.",
            ["откуда в иностранных языках возникли названия типа англ. Moscow, нем. Moskau, фр. Moscou."],
        ),
    ],
)
def test_russian_abbreviations_no_false_split(text, expected):
    """Common Russian abbreviations (др., ср.) and inline language tags (англ., нем., фр.,
    чуваш., рус.) must not be treated as sentence boundaries — even before a Latin-capital
    gloss, which introduces a foreign-language name rather than ending a sentence."""
    seg = sentencesplit.Segmenter(language="ru", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_trailing_zero_width_space_preserves_char_spans():
    """Dropping zero-width chars must keep char-span mapping non-destructive."""
    seg = sentencesplit.Segmenter(language="es", clean=False)
    text = "Frase uno.​ Frase dos.​"
    spans = seg.segment_spans(text)
    # Each returned span's text must be an exact slice of the original text.
    for span in spans:
        assert text[span.start : span.end] == span.sent


@pytest.mark.parametrize(
    "text,expected",
    [
        # U+200D inside an emoji ZWJ sequence is meaningful, not a boundary artifact.
        ("👩‍💻 works here.", ["👩‍💻 works here."]),
        # U+200C (ZWNJ) inside a Persian word must survive segmentation.
        ("او می‌گوید سلام.", ["او می‌گوید سلام."]),
        # Interior ZWNJ is preserved even while a trailing U+200B artifact is dropped.
        ("می‌گوید.​", ["می‌گوید."]),
    ],
)
def test_interior_zero_width_joiner_preserved(text, expected):
    """Only boundary zero-width artifacts are dropped; joiners inside a word or
    emoji sequence must be preserved (not globally deleted)."""
    seg = sentencesplit.Segmenter(language="es", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "language,text,expected",
    [
        # Multi-character terminator (!!!) before a capitalized word ends a sentence.
        (
            "de",
            "Der Betrieb AF Wintergarten ist einfach Top!!! Der Fisch ist immer frisch und der Wein ist sehr gut.",
            [
                "Der Betrieb AF Wintergarten ist einfach Top!!!",
                "Der Fisch ist immer frisch und der Wein ist sehr gut.",
            ],
        ),
        (
            "de",
            "Bei Kontaktanfragen wird man bei Problemen wochenlang ignoriert!!! "
            "Bei Rechtsanwalt Lansky sind wir seit 2002 Mandanten.",
            [
                "Bei Kontaktanfragen wird man bei Problemen wochenlang ignoriert!!!",
                "Bei Rechtsanwalt Lansky sind wir seit 2002 Mandanten.",
            ],
        ),
        # Accented German capital after the cluster still counts as a boundary.
        (
            "de",
            "Das ist Top!!! Über alles begeistert.",
            ["Das ist Top!!!", "Über alles begeistert."],
        ),
        # English behaves the same.
        (
            "en",
            "This place is amazing!!! Go there now.",
            ["This place is amazing!!!", "Go there now."],
        ),
    ],
)
def test_multi_char_terminator_before_capital_splits(language, text, expected):
    """A run of '!'/'?' (3+) that ends a sentence must split before a capitalized
    next word, while the cluster itself is kept intact."""
    seg = sentencesplit.Segmenter(language=language, clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "language,text,expected",
    [
        # End-of-text cluster must stay attached, not become its own fragment.
        ("en", "This place is 5 stars!!!", ["This place is 5 stars!!!"]),
        # A cluster mid-clause followed by a lowercase word must not split.
        ("en", "wow!!! amazing place", ["wow!!! amazing place"]),
        ("de", "einfach Top!!! aber teuer", ["einfach Top!!! aber teuer"]),
    ],
)
def test_multi_char_terminator_protected_when_no_capital_follower(language, text, expected):
    """Protect the cluster from splitting when it does not end a sentence
    (end of text, or followed by a lowercase continuation)."""
    seg = sentencesplit.Segmenter(language=language, clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "language,text,expected",
    [
        # NL: conservative mode keeps chained single-letter initials joined
        # before the capitalized surname.
        (
            "nl",
            "De onderzoeksvraag van forensisch psycholoog F.J.G. Buschman van het "
            "psychiatrisch centrum Veldzicht in Balkbrug is subtieler: kun je met behulp "
            "van de techniek zien of een zedendelinquent alweer bezig is te denken over "
            "zijn volgende misdaad?",
            [
                "De onderzoeksvraag van forensisch psycholoog F.J.G. Buschman van het "
                "psychiatrisch centrum Veldzicht in Balkbrug is subtieler: kun je met behulp "
                "van de techniek zien of een zedendelinquent alweer bezig is te denken over "
                "zijn volgende misdaad?"
            ],
        ),
        (
            "nl",
            "forensisch psycholoog F.J.G. Buschman van het centrum",
            ["forensisch psycholoog F.J.G. Buschman van het centrum"],
        ),
        # EN: same structure — initials followed by a single capitalized surname.
        (
            "en",
            "A.S.E. Ackermann and team published the findings in 2007.",
            ["A.S.E. Ackermann and team published the findings in 2007."],
        ),
    ],
)
def test_chained_initials_before_capital_surname_conservative_no_split(language, text, expected):
    """A run of single-letter initials (e.g. F.J.G.) followed by a single
    capitalized token can be read as an Initials + Surname personal name;
    conservative mode preserves that joined reading."""
    seg = sentencesplit.Segmenter(language=language, clean=False, split_mode="conservative")
    assert [s.strip() for s in seg.segment(text)] == expected


def test_dutch_chained_initials_balanced_keeps_name_reading():
    text = "forensisch psycholoog F.J.G. Buschman van het centrum"

    balanced = sentencesplit.Segmenter(language="nl", clean=False)
    assert [s.strip() for s in balanced.segment(text)] == [text]

    aggressive = sentencesplit.Segmenter(language="nl", clean=False, split_mode="aggressive")
    assert [s.strip() for s in aggressive.segment(text)] == ["forensisch psycholoog F.J.G.", "Buschman van het centrum"]


def test_dutch_balanced_initialism_exception_is_language_specific():
    """Dutch balanced mode keeps the name-heavy 3+ initialism reading; aggressive splits."""
    text = "Hij behaalde zijn M.B.A. Daarna vertrok hij."

    balanced = sentencesplit.Segmenter(language="nl", clean=False)
    assert [s.strip() for s in balanced.segment(text)] == [text]

    aggressive = sentencesplit.Segmenter(language="nl", clean=False, split_mode="aggressive")
    assert [s.strip() for s in aggressive.segment(text)] == ["Hij behaalde zijn M.B.A.", "Daarna vertrok hij."]


@pytest.mark.parametrize(
    "language,text,expected",
    [
        # EL: the Greek profile's Unicode MULTI_PERIOD_ABBREVIATION_REGEX absorbs a
        # leading non-ASCII initial into the protected chain (e.g. "Δ.A.B.C." ->
        # "Δ∯A∯B∯C∯"). The initials-name heuristic must keep the ASCII-only
        # ([A-Za-z]) semantics of the original regex and stop walking left at the
        # non-ASCII letter — otherwise it traverses back to the preceding "a"/"o"/"de"
        # determiner and wrongly splits before the surname.
        (
            "el",
            "a Δ.A.B.C. Smith arrived.",
            ["a Δ.A.B.C. Smith arrived."],
        ),
        (
            "el",
            "die Ñ.A.B.C. Applications arrived.",
            ["die Ñ.A.B.C. Applications arrived."],
        ),
    ],
)
def test_non_ascii_prefixed_initials_no_split(language, text, expected):
    """A non-ASCII leading initial absorbed into the protected initials chain
    (via the Greek Unicode MPA regex) must not cause the initials-name heuristic
    to walk back to a preceding determiner and split before the surname in
    conservative mode."""
    seg = sentencesplit.Segmenter(language=language, clean=False, split_mode="conservative")
    assert [s.strip() for s in seg.segment(text)] == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        # An acronym used as a noun (preceded by an article) before a new
        # sentence must still split — this is the boundary case the chained
        # initials rule must not regress.
        ("I studied for the S.A.T. Tomorrow is test day.", ["I studied for the S.A.T.", "Tomorrow is test day."]),
        ("I studied for the S.A.T. Test is hard.", ["I studied for the S.A.T.", "Test is hard."]),
    ],
)
def test_acronym_noun_before_new_sentence_still_splits(text, expected):
    """Initials acting as a noun (e.g. 'the S.A.T.') must keep splitting before
    a capitalized new sentence — guards against over-joining from the chained
    initials name heuristic."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == expected


@pytest.mark.perf
def test_repeated_initials_heuristic_is_linear_time():
    """Repeated joined initialisms should not rescan the full prefix per match."""
    seg = sentencesplit.Segmenter(language="en", clean=False, split_mode="conservative")
    text = "A.B.C. X " * 4000

    start = perf_counter()
    segments = seg.segment(text)
    elapsed = perf_counter() - start

    assert segments
    assert elapsed < 2.0


@pytest.mark.parametrize(
    "text,expected",
    [
        # A four-dot run glued (no whitespace) to a lowercase continuation is a
        # typo/run-on, not a real boundary — keep it attached.
        (
            "You have to see these slides....they are amazing. This Fallujah operation my turn out to be the most "
            "important operation done by the US Military since the end of the war.",
            [
                "You have to see these slides....they are amazing.",
                "This Fallujah operation my turn out to be the most important operation done by the US Military "
                "since the end of the war.",
            ],
        ),
        (
            "You have to see these slides....they are amazing.",
            ["You have to see these slides....they are amazing."],
        ),
        # A three-dot run glued to a lowercase continuation is likewise a run-on.
        (
            "I love this place...it is wonderful.",
            ["I love this place...it is wonderful."],
        ),
        # GUARD: a four-dot ellipsis followed by whitespace + a capital must
        # still split into two sentences.
        ("Wait.... The end.", ["Wait....", "The end."]),
        # GUARD: a normal "... Capital" ellipsis boundary must still split.
        ("I was thinking... Maybe later.", ["I was thinking...", "Maybe later."]),
    ],
)
def test_glued_ellipsis_lowercase_runon_not_split(text, expected):
    """A '...'/'....' run with no whitespace before a lowercase continuation is
    an intra-word run-on and must not introduce a sentence boundary, while
    normal spaced ellipsis boundaries before a capital still split."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == expected


@pytest.mark.perf
def test_glued_ellipsis_lowercase_rule_handles_long_period_runs_linearly():
    """The glued lowercase run-on protection must not rescan long period runs
    from every period when the run is not followed by lowercase text."""
    text = "a" + "." * 20_000 + "A"

    start = perf_counter()
    result = Standard.EllipsisRules.GluedLowercaseRunOnRule.regex.sub("∮", text)
    elapsed = perf_counter() - start

    assert result == text
    assert elapsed < 0.25


def test_glued_ellipsis_lowercase_rule_preserves_long_runon_protection():
    """Runs longer than four periods still protect every dot before the
    trailing ellipsis so no bare terminal period remains."""
    result = Standard.EllipsisRules.GluedLowercaseRunOnRule.regex.sub("∮", "slides......they")

    assert result == "slides∮∮∮...they"


@pytest.mark.parametrize(
    "text,expected",
    [
        # All-caps imprint/colophon: "CO." is a company abbreviation here, not a
        # sentence end. The follower "TOOKS" is uppercase but lives in an all-caps
        # run, so the period must stay joined.
        (
            "CHISWICK PRESS:--CHARLES WHITTINGHAM AND CO. TOOKS COURT, CHANCERY LANE, LONDON.",
            ["CHISWICK PRESS:--CHARLES WHITTINGHAM AND CO. TOOKS COURT, CHANCERY LANE, LONDON."],
        ),
        (
            "CELLULAR COMMUNICATIONS INC. SOLD 1,550,000 COMMON SHARES.",
            ["CELLULAR COMMUNICATIONS INC. SOLD 1,550,000 COMMON SHARES."],
        ),
        ("ACME CORP. ANNOUNCED RESULTS.", ["ACME CORP. ANNOUNCED RESULTS."]),
        ("FOO LTD. LONDON.", ["FOO LTD. LONDON."]),
        ("WARNER BROS. RELEASED TRAILERS.", ["WARNER BROS. RELEASED TRAILERS."]),
        # GUARD: mixed-case "Co." at a genuine boundary must still split
        # (Golden Rule 9) — the follower "It" is not an all-caps imprint word.
        (
            "They closed the deal with Pitt, Briggs & Co. It closed yesterday.",
            ["They closed the deal with Pitt, Briggs & Co.", "It closed yesterday."],
        ),
        # GUARD: mixed-case "Co." mid-sentence before lowercase stays joined
        # (Golden Rule 7).
        (
            "They closed the deal with Pitt, Briggs & Co. at noon.",
            ["They closed the deal with Pitt, Briggs & Co. at noon."],
        ),
        # GUARD: lowercase "co." as a genuine terminal still splits (Golden Rule 8).
        (
            "Let's ask Jane and co. They should know.",
            ["Let's ask Jane and co.", "They should know."],
        ),
        # GUARD: unrelated all-caps abbreviations, such as months, can still end
        # a sentence before an all-caps sentence start.
        (
            "IT HAPPENED IN DEC. THE END.",
            ["IT HAPPENED IN DEC.", "THE END."],
        ),
    ],
)
def test_allcaps_imprint_company_abbreviation_no_false_split(text, expected):
    """A company abbreviation (CO.) inside an all-caps imprint/colophon run must
    not be split from the following all-caps token, while mixed-case company
    abbreviations keep their normal boundary behaviour."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    segments = [s.strip() for s in seg.segment(text)]
    assert segments == expected


def test_common_two_part_initialism_phrase_before_capital_stays_joined():
    """Common two-part initialism phrases stay joined in every split mode."""
    text = "His involvement at the D.C. Circuit level and Anthony Kennedy joining the liberals."
    for mode in ("conservative", "balanced", "aggressive"):
        seg = sentencesplit.Segmenter(language="en", clean=False, split_mode=mode)
        assert [s.strip() for s in seg.segment(text)] == [text]


MULTI_SENTENCE_QUOTATION_DATA = [
    # case_0080 — a single pair of curly quotes wraps four complete sentences;
    # the closing quote only arrives at the end, so the interior terminal
    # periods must still split (punkt/syntok do, sentencesplit used not to).
    (
        "case_0080",
        "“Indeed, I should have thought a little more. Just a trifle more, I fancy, Watson. "
        "And in practice again, I observe. You did not tell me that you intended to go into harness.”",
        [
            "“Indeed, I should have thought a little more.",
            "Just a trifle more, I fancy, Watson.",
            "And in practice again, I observe.",
            "You did not tell me that you intended to go into harness.”",
        ],
    ),
]


@pytest.mark.parametrize("case_id, text, expected", MULTI_SENTENCE_QUOTATION_DATA)
def test_multi_sentence_quotation_splits_interior_boundaries(case_id, text, expected):
    """A self-contained multi-sentence quotation (a single un-nested quote pair
    wrapping several complete sentences whose closing quote is far away) must
    split at its interior period boundaries (cluster multi-sentence-quotation).
    Previously the between-punctuation pass treated the whole quoted span as one
    unsplittable region."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


MULTI_SENTENCE_QUOTATION_KEEP_DATA = [
    # case_0102 — GUARD: a short quoted speech act whose first clause is brief
    # ("I see it, I deduce it.") stays as one unit (pysbd/pragmatic agree).
    (
        "case_0102",
        "“I see it, I deduce it. How do I know that you have been getting yourself very wet lately, "
        "and that you have a most clumsy and careless servant girl?”",
        [
            "“I see it, I deduce it. How do I know that you have been getting yourself very wet lately, "
            "and that you have a most clumsy and careless servant girl?”",
        ],
    ),
    # GUARD (case_0085 / test_english_clean): short embedded exclamations inside
    # a quotation must stay together rather than fragment into "Oh dear!" etc.
    (
        "oh_dear",
        "There was nothing so very remarkable in that, nor did Alice think it so very much out of "
        'the way to hear the Rabbit say to itself, "Oh dear! Oh dear! I shall be too late!"',
        [
            "There was nothing so very remarkable in that, nor did Alice think it so very much out of "
            'the way to hear the Rabbit say to itself, "Oh dear! Oh dear! I shall be too late!"',
        ],
    ),
    # GUARD (Golden Rule): an interior period inside a quote followed by a
    # lowercase attribution verb stays joined.
    (
        "gr_lowercase_attribution",
        'She turned to him, "This is great." she said.',
        ['She turned to him, "This is great." she said.'],
    ),
    # GUARD (case_0110): a quotation with a SINGLE interior boundary stays whole.
    # Splitting it would regress the structurally identical gold "...at tea-time.
    # Dinah, my dear, I wish..." below, so single-boundary quotes are left intact.
    (
        "case_0110",
        "“When I hear you give your reasons,” I remarked, “the thing always appears to me to be "
        "so ridiculously simple that I could easily do it myself, though at each successive instance "
        "of your reasoning I am baffled until you explain your process. And yet I believe that my "
        "eyes are as good as yours.”",
        [
            "“When I hear you give your reasons,” I remarked, “the thing always appears to me to be "
            "so ridiculously simple that I could easily do it myself, though at each successive instance "
            "of your reasoning I am baffled until you explain your process. And yet I believe that my "
            "eyes are as good as yours.”",
        ],
    ),
    # GUARD (test_english_clean): a single-boundary quote whose second clause is
    # a vocative continuation of the same speech act must NOT be split.
    (
        "dinah",
        '"I hope they\'ll remember her saucer of milk at tea-time. Dinah, my dear, I wish you were down here with me!"',
        ['"I hope they\'ll remember her saucer of milk at tea-time. Dinah, my dear, I wish you were down here with me!"'],
    ),
    # GUARD (test_english_clean): a multi-sentence quote that contains embedded
    # attribution ('," said Alice ...; "') is NOT a single self-contained
    # quotation, so it is kept whole — the resplit only fires for an un-nested,
    # un-attributed single quote pair.
    (
        "well_perhaps_not",
        '"Well, perhaps not," said Alice in a soothing tone; "don\'t be angry about it. And yet I wish '
        "I could show you our cat Dinah. I think you'd take a fancy to cats, if you could only see her. "
        'She is such a dear, quiet thing."',
        [
            '"Well, perhaps not," said Alice in a soothing tone; "don\'t be angry about it. And yet I wish '
            "I could show you our cat Dinah. I think you'd take a fancy to cats, if you could only see her. "
            'She is such a dear, quiet thing."'
        ],
    ),
    # GUARD (test_english_clean): a run of in-quote exclamations is one emphatic
    # speech act, not separate sentences — only PERIOD boundaries split, so this
    # stays whole.
    (
        "as_if_i_would",
        '"As if _I_ would talk on such a subject! Our family always _hated_ cats--nasty, low, vulgar '
        "things! Don't let me hear the name again!\"",
        [
            '"As if _I_ would talk on such a subject! Our family always _hated_ cats--nasty, low, vulgar '
            "things! Don't let me hear the name again!\""
        ],
    ),
    # GUARD (case_0106): a quotation broken by embedded attribution ('," said he;
    # "') has more than one quote run, so the resplit leaves it intact even
    # though it contains several interior periods.
    (
        "case_0106",
        "“It is simplicity itself,” said he; “my eyes tell me that on the inside of your left "
        "shoe, just where the firelight strikes it, the leather is scored by six almost parallel "
        "cuts. Obviously they have been caused by someone who has very carelessly scraped round the "
        "edges of the sole. Hence, you see, my double deduction.”",
        [
            "“It is simplicity itself,” said he; “my eyes tell me that on the inside of your left "
            "shoe, just where the firelight strikes it, the leather is scored by six almost parallel "
            "cuts. Obviously they have been caused by someone who has very carelessly scraped round the "
            "edges of the sole. Hence, you see, my double deduction.”"
        ],
    ),
]


@pytest.mark.parametrize("case_id, text, expected", MULTI_SENTENCE_QUOTATION_KEEP_DATA)
def test_multi_sentence_quotation_keeps_short_speech_acts(case_id, text, expected):
    """GUARD: brief quoted utterances / embedded exclamations must NOT be
    fragmented by the multi-sentence-quotation resplit."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


# The interior-boundary detector recognises a sentence start by its leading
# capital. Restricting it to ASCII [A-Z] under-split multi-sentence quotations
# whose sentences begin with a non-ASCII capital — accented Latin (É, Ú, Ñ, Ä, …,
# Spanish/French/Italian), Greek (Η, Έ), or Cyrillic (П, В, Т, Russian/Bulgarian).
# The detector now accepts any uppercase letter (str.isupper(); the regex already
# guarantees a letter follows, so caseless CJK is naturally excluded), so these
# split like their all-ASCII equivalents.
MULTI_SENTENCE_QUOTATION_NON_ASCII_DATA = [
    # Accented Latin capitals (É, Ú) — Spanish.
    (
        "es",
        "«La primera frase está aquí mismo. Época de grandes cambios llegó ya. Última frase para terminar esto.»",
        [
            "«La primera frase está aquí mismo.",
            "Época de grandes cambios llegó ya.",
            "Última frase para terminar esto.»",
        ],
    ),
    # Mixed: the accented-capital boundary (". Época") was previously missed,
    # undercounting interior sentences so the whole quote stayed joined.
    (
        "en",
        "“This first sentence is right here. Época nueva comienza para todos hoy. This third sentence is right here.”",
        [
            "“This first sentence is right here.",
            "Época nueva comienza para todos hoy.",
            "This third sentence is right here.”",
        ],
    ),
    # Greek capitals (Η) — guillemet quotation wrapping three sentences.
    (
        "el",
        "«Η πρώτη πρόταση είναι εδώ τώρα. Η δεύτερη πρόταση είναι εδώ τώρα. Η τρίτη πρόταση είναι εδώ τώρα.»",
        [
            "«Η πρώτη πρόταση είναι εδώ τώρα.",
            "Η δεύτερη πρόταση είναι εδώ τώρα.",
            "Η τρίτη πρόταση είναι εδώ τώρα.»",
        ],
    ),
    # Cyrillic capitals (П, В, Т) — Russian guillemet quotation.
    (
        "ru",
        "«Первое предложение находится прямо здесь. Второе предложение находится прямо здесь. "
        "Третье предложение находится прямо здесь.»",
        [
            "«Первое предложение находится прямо здесь.",
            "Второе предложение находится прямо здесь.",
            "Третье предложение находится прямо здесь.»",
        ],
    ),
]


@pytest.mark.parametrize("language, text, expected", MULTI_SENTENCE_QUOTATION_NON_ASCII_DATA)
def test_multi_sentence_quotation_splits_before_non_ascii_capital(language, text, expected):
    """A multi-sentence quotation whose interior sentences begin with a non-ASCII
    capital (accented Latin, Greek, or Cyrillic) must split, like the ASCII case."""
    seg = sentencesplit.Segmenter(language=language, clean=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_multi_sentence_quotation_keeps_abbreviation_periods_joined():
    """Quote resplitting must not turn restored abbreviation periods into boundaries."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    text = (
        '"He very gladly met Dr. Watson and Sherlock talked at noon. '
        "They then discussed the strange case. "
        'The matter remained unresolved overnight."'
    )
    assert [s.strip() for s in seg.segment(text)] == [
        '"He very gladly met Dr. Watson and Sherlock talked at noon.',
        "They then discussed the strange case.",
        'The matter remained unresolved overnight."',
    ]


def test_multi_sentence_quotation_ignores_quote_initial_abbreviation_period():
    """A quote-initial title abbreviation must not count as an interior sentence."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    text = '"Dr. Smith was present today. They discussed the strange case at noon. The matter remained unresolved overnight."'
    assert [s.strip() for s in seg.segment(text)] == [
        '"Dr. Smith was present today.',
        "They discussed the strange case at noon.",
        'The matter remained unresolved overnight."',
    ]


@pytest.mark.parametrize("opener, closer", [("(", ")"), ("[", "]")])
def test_multi_sentence_quotation_ignores_delimited_abbreviation_period(opener, closer):
    """An abbreviation after an opening delimiter must not become a quote split."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    text = (
        f'"The witness greeted our old friend {opener}Dr. John Hamish Watson visited warmly today{closer}. '
        "They discussed the strange case at noon. "
        'The matter remained unresolved overnight."'
    )
    assert [s.strip() for s in seg.segment(text)] == [
        f'"The witness greeted our old friend {opener}Dr. John Hamish Watson visited warmly today{closer}.',
        "They discussed the strange case at noon.",
        'The matter remained unresolved overnight."',
    ]


# PR #41: the linear-time glued-lowercase-run-on scanner must reproduce the
# original `(?<=\S)\.(?=\.{3,}[a-z])` regex, whose per-dot lookbehind protected
# interior dots even when the run begins at index 0 or follows whitespace
# (each interior dot is preceded by a literal '.', which is \S). A whole-run
# guard that skips leading / whitespace-preceded runs over-fragments these on
# the public clean=False path (used for span mapping).
GLUED_LEADING_DOT_RUN_DATA = [
    ("leading_run", ".....and then.", [".....and then."]),
    ("leading_run_letter", ".....x is here.", [".....x is here."]),
    ("ws_preceded_run", "ok. .....and then.", ["ok. ", ".", "....and then."]),
    (
        "ws_preceded_run_with_tail",
        "Foo. .....and then. Bar.",
        ["Foo. ", ".", "....and then. ", "Bar."],
    ),
    # CONTROLS: word-char-preceded mid-string runs must be unaffected.
    ("glued_word", "slides......they", ["slides......they"]),
    ("uppercase_tail", "Wait.... The end.", ["Wait.... ", "The end."]),
]


@pytest.mark.parametrize("case_id, text, expected", GLUED_LEADING_DOT_RUN_DATA)
def test_glued_lowercase_run_on_protects_leading_dot_runs(case_id, text, expected):
    """REGRESSION (PR #41): leading / whitespace-preceded 4+ period runs must
    stay intact under clean=False, matching the original per-dot lookbehind."""
    seg = sentencesplit.Segmenter(language="en", clean=False)
    assert seg.segment(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Fig. ?? Next sentence.", ["Fig. ?? ", "Next sentence."]),
        ("Fig. ?? ¿Cómo está?", ["Fig. ?? ", "¿Cómo está?"]),
        ("Fig. ?? 下一个。", ["Fig. ?? ", "下一个。"]),
        ("Fig. ?? “下一个。”", ["Fig. ?? ", "“下一个。”"]),
        ("Fig. ?? (下一个。)", ["Fig. ?? ", "(下一个。)"]),
        ("Fig. ?? (¿Cómo está?)", ["Fig. ?? ", "(¿Cómo está?)"]),
    ],
)
def test_en_es_zh_resplits_protected_number_abbreviation_unknown_placeholder(text, expected):
    """The combined profile must resplit restored ?? after number abbreviations.

    Its custom CJK-aware resplit path should preserve the base Latin multi-terminator behavior and support combined
    profile sentence starters after protected unknown punctuation placeholders are restored.
    """
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False)

    assert seg.segment(text) == expected

    span_seg = sentencesplit.Segmenter(language="en_es_zh", clean=False)
    spans = span_seg.segment_spans(text)
    assert [span.sent for span in spans] == expected
    assert "".join(span.sent for span in spans) == text


def test_slovak_overlapping_whole_span_abbreviations_do_not_drop_later_edits():
    """Overlapping Slovak abbreviation candidates should not force an all-kept scan.

    The leading ``a.s.a.p.`` creates overlapping whole-span edits; later disjoint
    edits model a long line of ordinary Slovak abbreviations and must all remain.
    """
    from sentencesplit.period_classifier import Edit, PeriodClassifier

    edits = [
        Edit(0, 4, "a∯s∯", 3),
        Edit(0, 8, "a∯s∯a∯p∯", 7),
        *(Edit(start, start + 1, "∯", start) for start in range(20, 120, 5)),
    ]

    deduped = PeriodClassifier._dedup_sorted(edits)

    assert deduped[0] == Edit(0, 8, "a∯s∯a∯p∯", 7)
    assert deduped[1:] == [Edit(start, start + 1, "∯", start) for start in range(20, 120, 5)]


def test_slovak_segmenter_handles_overlap_and_many_following_abbreviations():
    """Public Slovak API keeps crafted overlap input as one protected sentence."""
    seg = sentencesplit.Segmenter(language="sk", clean=False)
    text = "a.s.a.p. " + "napr. " * 100 + "koniec."

    assert seg.segment(text) == [text]
