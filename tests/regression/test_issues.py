# -*- coding: utf-8 -*-
import pytest

import sentencesplit
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
    pytest.param(
        "#39",
        "T stands for the vector transposition. As shown in Fig. ??",
        ["T stands for the vector transposition.", "As shown in Fig. ??"],
        marks=pytest.mark.xfail,
    ),
    pytest.param("#39", "Fig. ??", ["Fig. ??"], marks=pytest.mark.xfail),
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
        marks=pytest.mark.xfail,
    ),
]


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
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=True)
    segments = seg.segment(text)
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
    seg = sentencesplit.Segmenter(language=language, clean=False, char_span=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_compact_ampm_before_non_ascii_uppercase():
    """Compact 6p.m. form should split before non-ASCII uppercase sentence starters."""
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment("He left at 6p.m. \u00c9lodie arrived.")] == [
        "He left at 6p.m.",
        "\u00c9lodie arrived.",
    ]


def test_eq_abbreviation_before_roman_numeral():
    """Eq. before a Roman numeral should stay joined like Fig."""
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment("Eq. IV shows the result. Next sentence.")] == [
        "Eq. IV shows the result.",
        "Next sentence.",
    ]


def test_pt_abbreviation_before_roman_numeral():
    """Pt. before a Roman numeral should stay joined (number abbreviation)."""
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment("Pt. II discusses methods. Next sentence.")] == [
        "Pt. II discusses methods.",
        "Next sentence.",
    ]


def test_boundary_abbreviation_before_non_ascii_uppercase():
    """Two-part boundary abbreviations (U.S.) stay joined before non-ASCII uppercase
    that is not a known sentence starter — avoids over-splitting noun phrases like
    'U.S. Élodie Foundation'."""
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment("He moved from the U.S. \u00c9lodie arrived.")] == [
        "He moved from the U.S. \u00c9lodie arrived.",
    ]


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
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False, char_span=False)
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
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_three_part_initialism_before_non_ascii_uppercase_stays_joined():
    """Pure initialisms like U.S.A. should stay joined before non-ASCII uppercase
    proper nouns like Élodie — avoids false splits in noun phrases."""
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment("He works for the U.S.A. \u00c9lodie Foundation.")] == [
        "He works for the U.S.A. \u00c9lodie Foundation.",
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
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment(text)] == expected


def test_greek_uppercase_not_treated_as_sentence_start():
    """Greek/Cyrillic uppercase (e.g. Δ) should not trigger sentence splits —
    only accented Latin uppercase (e.g. É) should."""
    seg = sentencesplit.Segmenter(language="en", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment("The reading was taken at 6 p.m. ΔF508 remained detectable.")] == [
        "The reading was taken at 6 p.m. ΔF508 remained detectable.",
    ]


def test_en_es_zh_accented_uppercase_splits_after_number_abbreviation():
    """Accented uppercase starters like Él must split after number abbreviations in en_es_zh."""
    seg = sentencesplit.Segmenter(language="en_es_zh", clean=False, char_span=False)
    assert [s.strip() for s in seg.segment("Fig. Él explica el resultado. Siguiente.")] == [
        "Fig.",
        "Él explica el resultado.",
        "Siguiente.",
    ]
