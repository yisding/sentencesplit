import sentencesplit
from sentencesplit.abbreviation_replacer import AbbreviationReplacer, _AbbreviationData
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


def test_legacy_sentence_starters_still_enable_base_helper_flags():
    class DemoAbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = ["Several"]

    class Demo(Common, Standard):
        iso_code = "demo_legacy_starters"
        AbbreviationReplacer = DemoAbbreviationReplacer

    register_language("demo_legacy_starters", Demo)
    try:
        conservative = sentencesplit.Segmenter(language="demo_legacy_starters", clean=False, split_mode="conservative")
        assert [s.strip() for s in conservative.segment("See Fig. Several panels follow.")] == [
            "See Fig. Several panels follow."
        ]
        assert [s.strip() for s in conservative.segment("ACME CORP. ANNOUNCED RESULTS.")] == ["ACME CORP. ANNOUNCED RESULTS."]
        balanced = sentencesplit.Segmenter(language="demo_legacy_starters", clean=False, split_mode="balanced")
        assert [s.strip() for s in balanced.segment("I live in the U.S. Several agencies joined.")] == [
            "I live in the U.S.",
            "Several agencies joined.",
        ]
    finally:
        unregister_language("demo_legacy_starters")


def test_legacy_sentence_starters_work_on_subclasses_of_builtin_replacers():
    class DemoAbbreviationReplacer(English.AbbreviationReplacer):
        SENTENCE_STARTERS = ["Several"]

    class Demo(Common, Standard):
        iso_code = "demo_legacy_english_starters"
        AbbreviationReplacer = DemoAbbreviationReplacer

    register_language("demo_legacy_english_starters", Demo)
    try:
        seg = sentencesplit.Segmenter(language="demo_legacy_english_starters", clean=False, split_mode="balanced")
        assert [s.strip() for s in seg.segment("I live in the U.S. Several agencies joined.")] == [
            "I live in the U.S.",
            "Several agencies joined.",
        ]
    finally:
        unregister_language("demo_legacy_english_starters")
