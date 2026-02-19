# -*- coding: utf-8 -*-
"""
Challenging English sentence boundary detection test cases.

These extend the golden rules with harder edge cases covering:
- Academic/professional degrees and titles
- Military and religious titles
- Legal and scientific citations
- Technical text (version numbers, file paths, IPs)
- Complex quotation and dialogue patterns
- Consecutive abbreviations
- Decimal/number ambiguities
- Parenthetical abbreviations
- Short and degenerate sentences
- Mixed formal/informal punctuation
"""
import pytest


CHALLENGING_EN_TEST_CASES = [
    # ===== Academic degrees & professional titles =====
    # 49) Ph.D. as non-boundary (mid-sentence)
    (
        "She earned her Ph.D. in molecular biology from MIT.",
        ["She earned her Ph.D. in molecular biology from MIT."],
    ),
    # 50) Ph.D. as boundary (end of sentence, next sentence starts)
    (
        "He completed his Ph.D. She completed her M.D.",
        ["He completed his Ph.D.", "She completed her M.D."],
    ),
    # 51) Multiple degrees in sequence
    (
        "John Smith, M.D., Ph.D., gave the keynote address. The audience applauded.",
        [
            "John Smith, M.D., Ph.D., gave the keynote address.",
            "The audience applauded.",
        ],
    ),
    # 52) B.A. / B.S. mid-sentence
    (
        "She holds a B.A. in English and a B.S. in computer science from Stanford.",
        ["She holds a B.A. in English and a B.S. in computer science from Stanford."],
    ),

    # ===== Military and religious titles =====
    # 53) Military abbreviations mid-sentence
    (
        "I spoke with Sgt. Johnson and Lt. Col. Davis about the mission.",
        ["I spoke with Sgt. Johnson and Lt. Col. Davis about the mission."],
    ),
    # 54) Military abbreviation at sentence boundary
    (
        "The order came from Gen. Patton. He demanded immediate action.",
        ["The order came from Gen. Patton.", "He demanded immediate action."],
    ),
    # 55) Religious title
    (
        "We visited Rev. Martin Luther King Jr.'s memorial. It was moving.",
        ["We visited Rev. Martin Luther King Jr.'s memorial.", "It was moving."],
    ),

    # ===== Legal and scientific citations =====
    # 56) Legal citation with U.S.C.
    (
        "The statute is codified at 42 U.S.C. § 1983. It provides a right of action.",
        [
            "The statute is codified at 42 U.S.C. § 1983.",
            "It provides a right of action.",
        ],
    ),
    # 57) Case citation with v.
    (
        "The ruling in Brown v. Board of Education changed history. Schools were desegregated.",
        [
            "The ruling in Brown v. Board of Education changed history.",
            "Schools were desegregated.",
        ],
    ),
    # 58) Scientific notation with et al.
    (
        "According to Smith et al. the results were inconclusive. Further studies are needed.",
        [
            "According to Smith et al. the results were inconclusive.",
            "Further studies are needed.",
        ],
    ),
    # 59) Footnote / citation markers in brackets
    (
        "The temperature rose by 1.5°C [1]. This is consistent with previous findings [2, 3].",
        [
            "The temperature rose by 1.5°C [1].",
            "This is consistent with previous findings [2, 3].",
        ],
    ),

    # ===== Technical text =====
    # 60) Version number at sentence boundary
    (
        "Please upgrade to version 3.2.1. The new release fixes several bugs.",
        [
            "Please upgrade to version 3.2.1.",
            "The new release fixes several bugs.",
        ],
    ),
    # 61) Filename with extension mid-sentence
    (
        "Edit the file config.yaml to change the settings.",
        ["Edit the file config.yaml to change the settings."],
    ),
    # 62) IP address mid-sentence
    (
        "The server at 192.168.1.1 is down. Please contact IT support.",
        ["The server at 192.168.1.1 is down.", "Please contact IT support."],
    ),
    # 63) File path with periods
    (
        "The log is at /var/log/app.2024.01.15.log. Check it for errors.",
        [
            "The log is at /var/log/app.2024.01.15.log.",
            "Check it for errors.",
        ],
    ),

    # ===== Complex quotation and dialogue =====
    # 64) Question inside quotes, continuation outside
    (
        '"Is anyone there?" she called. No one answered.',
        ['"Is anyone there?" she called.', "No one answered."],
    ),
    # 65) Exclamation inside quotes at sentence end
    (
        'He shouted, "Run!" and everyone scattered.',
        ['He shouted, "Run!" and everyone scattered.'],
    ),
    # 66) Multiple quoted sentences in dialogue
    (
        '"I\'m leaving," he said. "Don\'t wait up." She nodded.',
        ['"I\'m leaving," he said.', '"Don\'t wait up."', "She nodded."],
    ),
    # 67) Quote ending with ellipsis
    (
        '"I thought we could..." He trailed off. She looked away.',
        ['"I thought we could..."', "He trailed off.", "She looked away."],
    ),
    # 68) Nested single quotes inside double quotes
    (
        "She asked, \"Did he really say 'I quit'?\" I wasn't sure.",
        ["She asked, \"Did he really say 'I quit'?\"", "I wasn't sure."],
    ),

    # ===== Consecutive abbreviations =====
    # 69) Multiple geographic abbreviations
    (
        "He moved from Washington, D.C. to Los Angeles, CA. The move took three days.",
        [
            "He moved from Washington, D.C. to Los Angeles, CA.",
            "The move took three days.",
        ],
    ),
    # 70) U.S. and U.K. in same sentence
    (
        "The U.S. and U.K. signed a trade agreement. It takes effect in January.",
        [
            "The U.S. and U.K. signed a trade agreement.",
            "It takes effect in January.",
        ],
    ),
    # 71) Abbreviation before and after sentence boundary
    # xfail: H.B.S. not recognized as multi-period abbreviation at sentence end
    pytest.param(
        "She received her M.B.A. from H.B.S. She then joined McKinsey & Co.",
        [
            "She received her M.B.A. from H.B.S.",
            "She then joined McKinsey & Co.",
        ],
        marks=pytest.mark.xfail,
    ),

    # ===== Decimal / number edge cases =====
    # 72) Percentage at sentence boundary
    (
        "Sales grew by 12.5%. The board was pleased.",
        ["Sales grew by 12.5%.", "The board was pleased."],
    ),
    # 73) Ordinal-like number followed by period
    (
        "He finished in 1st. She finished in 3rd. They both qualified.",
        ["He finished in 1st.", "She finished in 3rd.", "They both qualified."],
    ),
    # 74) Temperature reading at boundary
    (
        "The patient's temperature was 101.3°F. The nurse administered medication.",
        [
            "The patient's temperature was 101.3°F.",
            "The nurse administered medication.",
        ],
    ),
    # 75) Mathematical value mid-sentence
    (
        "Let pi equal 3.14159 for this calculation.",
        ["Let pi equal 3.14159 for this calculation."],
    ),
    # 76) Year with period at end of sentence
    (
        "The company was founded in 2015. It went public in 2020.",
        ["The company was founded in 2015.", "It went public in 2020."],
    ),

    # ===== Parenthetical abbreviations =====
    # 77) Abbreviation inside parentheses, not a boundary
    (
        "He visited the capital (Washington, D.C.) for a conference.",
        ["He visited the capital (Washington, D.C.) for a conference."],
    ),
    # 78) Sentence ending with closing paren after abbreviation
    (
        "She works for the government (specifically, the C.I.A.). Her job is classified.",
        [
            "She works for the government (specifically, the C.I.A.).",
            "Her job is classified.",
        ],
    ),
    # 79) Parenthetical full sentence followed by continuation
    (
        "The project failed (see Appendix B for details). Management was not happy.",
        [
            "The project failed (see Appendix B for details).",
            "Management was not happy.",
        ],
    ),

    # ===== Short / degenerate sentences =====
    # 80) Single-word sentences
    (
        "Stop. Look. Listen. These are the rules.",
        ["Stop.", "Look.", "Listen.", "These are the rules."],
    ),
    # 81) Single character sentence
    (
        "Is it option A? Or B? Choose now.",
        ["Is it option A?", "Or B?", "Choose now."],
    ),
    # 82) All-caps sentence
    (
        "WARNING: DO NOT ENTER. THIS AREA IS RESTRICTED.",
        ["WARNING: DO NOT ENTER.", "THIS AREA IS RESTRICTED."],
    ),

    # ===== Mixed formal/informal punctuation =====
    # 83) Em-dash splitting context
    (
        "The suspect—a man in his 30s—fled the scene. Police gave chase.",
        [
            "The suspect—a man in his 30s—fled the scene.",
            "Police gave chase.",
        ],
    ),
    # 84) Semicolon within a sentence containing abbreviations
    (
        "He visited the U.S.; however, he preferred the U.K. The weather was better.",
        [
            "He visited the U.S.; however, he preferred the U.K.",
            "The weather was better.",
        ],
    ),
    # 85) Colon introducing a list, not a boundary
    (
        "She bought three items: apples, bread, and milk. Then she went home.",
        [
            "She bought three items: apples, bread, and milk.",
            "Then she went home.",
        ],
    ),
    # 86) Question followed by exclamation
    (
        "Can you believe it? Absolutely incredible! I was stunned.",
        ["Can you believe it?", "Absolutely incredible!", "I was stunned."],
    ),

    # ===== Ambiguous "i.e." and "e.g." =====
    # 87) i.e. mid-sentence
    (
        "The plan was simple, i.e. we would leave at dawn. No one objected.",
        [
            "The plan was simple, i.e. we would leave at dawn.",
            "No one objected.",
        ],
    ),
    # 88) e.g. with multiple examples
    (
        "Use a common format, e.g. JSON, XML, or CSV. The parser handles all three.",
        [
            "Use a common format, e.g. JSON, XML, or CSV.",
            "The parser handles all three.",
        ],
    ),

    # ===== Tricky boundary vs. non-boundary after abbreviation =====
    # 89) "Inc." at sentence end vs. mid-sentence
    (
        "She works at Apple Inc. Tim Cook is the CEO.",
        ["She works at Apple Inc.", "Tim Cook is the CEO."],
    ),
    # 90) "Corp." mid-sentence
    (
        "Acme Corp. announced record earnings last quarter.",
        ["Acme Corp. announced record earnings last quarter."],
    ),
    # 91) "Ltd." at sentence boundary
    (
        "The contract was signed by Thames Ltd. It goes into effect Monday.",
        ["The contract was signed by Thames Ltd.", "It goes into effect Monday."],
    ),

    # ===== Time expressions =====
    # 92) Time with a.m./p.m. followed by new sentence
    (
        "The flight departs at 6:30 a.m. Please arrive two hours early.",
        ["The flight departs at 6:30 a.m.", "Please arrive two hours early."],
    ),
    # 93) Multiple times in one passage
    (
        "Office hours are 9 a.m. to 5 p.m. The office is closed on weekends.",
        [
            "Office hours are 9 a.m. to 5 p.m.",
            "The office is closed on weekends.",
        ],
    ),

    # ===== Addresses and locations =====
    # 94) Street abbreviation mid-sentence
    (
        "The office is at 123 Main St. near the park.",
        ["The office is at 123 Main St. near the park."],
    ),
    # 95) Multiple address abbreviations
    (
        "Turn left on Oak Blvd. and right on 5th Ave. The building is on the corner.",
        [
            "Turn left on Oak Blvd. and right on 5th Ave.",
            "The building is on the corner.",
        ],
    ),

    # ===== Sentence with only punctuation-heavy content =====
    # 96) Initialism confusion with sentence-ending "I"
    (
        "The team includes you, her, and I. We start tomorrow.",
        ["The team includes you, her, and I.", "We start tomorrow."],
    ),

    # ===== No space after period (OCR / PDF artifacts) =====
    # 97) Missing space after period
    # xfail: no space between sentences (common OCR artifact)
    pytest.param(
        "The first experiment failed.The second one succeeded.",
        ["The first experiment failed.", "The second one succeeded."],
        marks=pytest.mark.xfail,
    ),
    # 98) Missing space after abbreviation + new sentence
    # xfail: no space between abbreviation and next sentence
    pytest.param(
        "He works at Acme Corp.She works at Globex Inc.",
        ["He works at Acme Corp.", "She works at Globex Inc."],
        marks=pytest.mark.xfail,
    ),

    # ===== Edge cases with "no.", "fig.", "eq." =====
    # 99) "No." as abbreviation for number
    (
        "See item No. 7 in the list. It contains the answer.",
        ["See item No. 7 in the list.", "It contains the answer."],
    ),
    # 100) "Fig." reference mid-sentence and at boundary
    (
        "As shown in Fig. 3, the curve rises sharply. Fig. 4 shows the decline.",
        [
            "As shown in Fig. 3, the curve rises sharply.",
            "Fig. 4 shows the decline.",
        ],
    ),
    # 101) "Eq." in scientific text
    # xfail: Eq. not in abbreviation list, falsely splits
    pytest.param(
        "Substituting into Eq. 5 yields the result. The proof is complete.",
        ["Substituting into Eq. 5 yields the result.", "The proof is complete."],
        marks=pytest.mark.xfail,
    ),

    # ===== Complex real-world text =====
    # 102) News-style dense text with multiple abbreviations
    (
        "The C.E.O. of Widgets Inc. met with Sen. Harris and Rep. Garcia at 3 p.m. They discussed H.R. 1234. No agreement was reached.",
        [
            "The C.E.O. of Widgets Inc. met with Sen. Harris and Rep. Garcia at 3 p.m.",
            "They discussed H.R. 1234.",
            "No agreement was reached.",
        ],
    ),
    # 103) Academic text with multiple citation styles
    (
        "Previous work (Johnson et al., 2019; see also Fig. 2 in Smith, 2020) supports this claim. However, the results of Lee (2021) suggest otherwise.",
        [
            "Previous work (Johnson et al., 2019; see also Fig. 2 in Smith, 2020) supports this claim.",
            "However, the results of Lee (2021) suggest otherwise.",
        ],
    ),
    # 104) Medical / clinical note
    # xfail: Pt. not in abbreviation list, falsely splits after it
    pytest.param(
        "Pt. presented with a temp. of 102.4°F and B.P. of 140/90. Dr. Lee ordered labs stat. Results pending.",
        [
            "Pt. presented with a temp. of 102.4°F and B.P. of 140/90.",
            "Dr. Lee ordered labs stat.",
            "Results pending.",
        ],
        marks=pytest.mark.xfail,
    ),

    # ===== Additional edge cases inspired by failure analysis =====

    # 105) Unknown abbreviation "approx." mid-sentence
    # xfail: approx. not in abbreviation list
    pytest.param(
        "The distance is approx. 500 miles. We should fly.",
        ["The distance is approx. 500 miles.", "We should fly."],
        marks=pytest.mark.xfail,
    ),
    # 106) "dept." as abbreviation
    (
        "She transferred to the marketing dept. Her new role starts Monday.",
        ["She transferred to the marketing dept.", "Her new role starts Monday."],
    ),
    # 107) Abbreviation "govt." mid-sentence
    # xfail: govt. not in abbreviation list
    pytest.param(
        "The govt. issued new regulations on emissions.",
        ["The govt. issued new regulations on emissions."],
        marks=pytest.mark.xfail,
    ),
    # 108) "max." and "min." in technical context
    # xfail: max./min. not in abbreviation list
    pytest.param(
        "The max. temperature was 35°C and the min. was 12°C. It was a wide range.",
        [
            "The max. temperature was 35°C and the min. was 12°C.",
            "It was a wide range.",
        ],
        marks=pytest.mark.xfail,
    ),
    # 109) Sentence ending with a URL that has trailing period
    (
        "Visit us at https://example.com/path/to/page.html. We look forward to hearing from you.",
        [
            "Visit us at https://example.com/path/to/page.html.",
            "We look forward to hearing from you.",
        ],
    ),
    # 110) Sentence with both parenthetical and abbreviation at end
    (
        "The treaty was signed by the U.S. (represented by the Sec. of State). It took effect immediately.",
        [
            "The treaty was signed by the U.S. (represented by the Sec. of State).",
            "It took effect immediately.",
        ],
    ),
    # 111) Quoted title with period inside
    (
        'He read "Dr. Jekyll and Mr. Hyde" in one sitting. It terrified him.',
        [
            'He read "Dr. Jekyll and Mr. Hyde" in one sitting.',
            "It terrified him.",
        ],
    ),
    # 112) Abbreviation "etc." at sentence boundary
    (
        "Bring supplies: water, food, rope, etc. The hike will be long.",
        ["Bring supplies: water, food, rope, etc.", "The hike will be long."],
    ),
    # 113) "etc." mid-sentence
    (
        "Items such as pens, pencils, etc. are provided free of charge.",
        ["Items such as pens, pencils, etc. are provided free of charge."],
    ),
    # 114) Mixed language / loanwords with periods
    (
        "The restaurant serves hors d'oeuvres, viz. small appetizers. The menu changes daily.",
        [
            "The restaurant serves hors d'oeuvres, viz. small appetizers.",
            "The menu changes daily.",
        ],
    ),
    # 115) Ellipsis followed by question mark
    (
        "You mean...? I can't believe it. Tell me more.",
        ["You mean...?", "I can't believe it.", "Tell me more."],
    ),
    # 116) Abbreviation "vs." mid-sentence
    (
        "The case of Smith vs. Jones was settled. The judge ruled in favor of Jones.",
        [
            "The case of Smith vs. Jones was settled.",
            "The judge ruled in favor of Jones.",
        ],
    ),
    # 117) Degrees with numbers (e.g., "3 ft. 5 in.")
    (
        "The shelf is 3 ft. 5 in. wide. It fits perfectly.",
        ["The shelf is 3 ft. 5 in. wide.", "It fits perfectly."],
    ),
    # 118) Multiple sentences with "Dr." crossing boundaries
    (
        "I saw Dr. Smith on Monday. Dr. Jones was unavailable. Dr. Patel will see you Friday.",
        [
            "I saw Dr. Smith on Monday.",
            "Dr. Jones was unavailable.",
            "Dr. Patel will see you Friday.",
        ],
    ),
    # 119) Sentence ending with a time zone abbreviation
    (
        "The meeting is at 3 p.m. EST. Please be on time.",
        ["The meeting is at 3 p.m. EST.", "Please be on time."],
    ),
    # 119a) a.m./p.m. followed by AST should stay with the same sentence
    (
        "The call is at 3 p.m. AST. Please join on time.",
        ["The call is at 3 p.m. AST.", "Please join on time."],
    ),
    # 119b) a.m./p.m. followed by all-caps acronym (NOT a timezone) is still a boundary
    (
        "The launch was at 3 p.m. NASA broadcast it live.",
        ["The launch was at 3 p.m.", "NASA broadcast it live."],
    ),
    # 119c) Non-timezone token should not be swallowed by timezone guard
    (
        "The update was at 3 p.m. ASST prepared the report.",
        ["The update was at 3 p.m.", "ASST prepared the report."],
    ),
    # 120) Sentence with "no." followed by digit (ambiguous list vs. abbreviation)
    (
        "He is ranked no. 1 in the world. She is no. 3.",
        ["He is ranked no. 1 in the world.", "She is no. 3."],
    ),
]


@pytest.mark.parametrize("text,expected_sents", CHALLENGING_EN_TEST_CASES)
def test_en_challenging(pysbd_default_en_no_clean_no_span_fixture, text, expected_sents):
    """Challenging SBD tests extending the golden rules."""
    segments = pysbd_default_en_no_clean_no_span_fixture.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
