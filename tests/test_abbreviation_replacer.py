from sentencesplit.abbreviation_replacer import _AbbreviationData
from sentencesplit.lang.english import English
import sentencesplit


def test_abbreviation_next_word_regex_reads_char_after_period_case_insensitive():
    data = _AbbreviationData(English.Abbreviation)
    dr_entry = next(item for item in data.abbreviations if item[0] == "dr")
    next_word_re = dr_entry[4]

    assert next_word_re.findall("Dr. Smith") == ["S"]
    assert next_word_re.findall("dr. smith") == ["s"]


def test_uppercase_following_word_does_not_force_split_when_no_sentence_starters():
    text = "Ide o firmy, napr. XYZCorp a.s."
    seg = sentencesplit.Segmenter(language="sk", clean=False)

    assert [s.strip() for s in seg.segment(text)] == [text]
