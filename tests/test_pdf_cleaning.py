import pytest

import sentencesplit


def test_exception_with_unknown_doc_type():
    with pytest.raises(ValueError, match="doc_type must be None or 'pdf'"):
        sentencesplit.Segmenter(language="en", clean=True, doc_type="html")


def test_exception_with_doc_type_pdf_and_clean_false():
    """
    Test to force clean=True when doc_type="pdf"
    """
    with pytest.raises(ValueError) as e:
        sentencesplit.Segmenter(language="en", clean=False, doc_type="pdf")
    assert str(e.value) == ("`doc_type='pdf'` should have `clean=True` since original text will be modified.")


PDF_TEST_DATA = [
    ("This is a sentence\ncut off in the middle because pdf.", ["This is a sentence cut off in the middle because pdf."]),
    (
        "Organising your care early \nmeans you'll have months to build a good relationship with your midwife or doctor, ready for \nthe birth.",
        [
            "Organising your care early means you'll have months to build a good relationship with your midwife or doctor, ready for the birth."
        ],
    ),
    (
        "10. Get some rest \n \nYou have the best chance of having a problem-free pregnancy and a healthy baby if you follow \na few simple guidelines:",
        [
            "10. Get some rest",
            "You have the best chance of having a problem-free pregnancy and a healthy baby if you follow a few simple guidelines:",
        ],
    ),
    (
        "• 9. Stop smoking \n• 10. Get some rest \n \nYou have the best chance of having a problem-free pregnancy and a healthy baby if you follow \na few simple guidelines:  \n\n1. Organise your pregnancy care early",
        [
            "• 9. Stop smoking",
            "• 10. Get some rest",
            "You have the best chance of having a problem-free pregnancy and a healthy baby if you follow a few simple guidelines:",
            "1. Organise your pregnancy care early",
        ],
    ),
    (
        "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next. First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs. She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.\n'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        [
            "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next.",
            "First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs.",
            "She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.",
            "'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        ],
    ),
    (
        "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next. First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs. She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.\r'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        [
            "Either the well was very deep, or she fell very slowly, for she had plenty of time as she went down to look about her and to wonder what was going to happen next.",
            "First, she tried to look down and make out what she was coming to, but it was too dark to see anything; then she looked at the sides of the well, and noticed that they were filled with cupboards and book-shelves; here and there she saw maps and pictures hung upon pegs.",
            "She took down a jar from one of the shelves as she passed; it was labelled 'ORANGE MARMALADE', but to her great disappointment it was empty: she did not like to drop the jar for fear of killing somebody, so managed to put it into one of the cupboards as she fell past it.",
            "'Well!' thought Alice to herself, 'after such a fall as this, I shall think nothing of tumbling down stairs! How brave they'll all think me at home! Why, I wouldn't say anything about it, even if I fell off the top of the house!' (Which was very likely true.)",
        ],
    ),
]


@pytest.mark.parametrize("text,expected_sents", PDF_TEST_DATA)
def test_en_pdf_type(text, expected_sents):
    """SBD tests from Pragmatic Segmenter for doctype:pdf"""
    seg = sentencesplit.Segmenter(language="en", clean=True, doc_type="pdf")
    segments = seg.segment(text)
    segments = [s.strip() for s in segments]
    assert segments == expected_sents
