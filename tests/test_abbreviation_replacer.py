import sentencesplit
from sentencesplit.abbreviation_replacer import _AbbreviationData
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.english import English
from sentencesplit.languages import register_language, unregister_language


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


def test_legacy_sentence_start_override_remains_compatible():
    class DemoAbbreviationReplacer(English.AbbreviationReplacer):
        def _is_likely_sentence_start(self, text: str) -> bool:
            return text.lstrip().startswith("★")

    class Demo(Common, Standard):
        iso_code = "demo_legacy_start"
        AbbreviationReplacer = DemoAbbreviationReplacer

    register_language("demo_legacy_start", Demo)
    try:
        seg = sentencesplit.Segmenter(language="demo_legacy_start", clean=False)
        assert [s.strip() for s in seg.segment("He earned a Ph.D. ★ Next.")] == [
            "He earned a Ph.D.",
            "★ Next.",
        ]
    finally:
        unregister_language("demo_legacy_start")
