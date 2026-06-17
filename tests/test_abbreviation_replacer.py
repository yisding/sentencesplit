import sentencesplit
from sentencesplit.abbreviation_replacer import _AbbreviationData
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.english import English
from sentencesplit.languages import register_language, unregister_language


def test_abbreviation_data_entry_is_a_four_tuple():
    # (stripped, stripped_lower, escaped, match_re) — the dead per-abbr next_word_re
    # 5th element was removed (its follower-char read now lives in
    # PeriodClassifier.enumerate_candidates).
    data = _AbbreviationData(English.Abbreviation)
    dr_entry = next(item for item in data.abbreviations if item[0] == "dr")
    assert len(dr_entry) == 4
    assert dr_entry[0] == "dr" and dr_entry[1] == "dr"


def test_enumerate_candidates_reads_follower_char_case_insensitively():
    # The follower char (the char after "abbr. ") is read from the same occurrence
    # the abbreviation matched, case-insensitively, by enumerate_candidates.
    replacer = English.AbbreviationReplacer("", English, split_mode="balanced")
    classifier = replacer._period_classifier()

    def follower(line: str) -> str | None:
        cands = [c for c in classifier.enumerate_candidates(line) if c.am_lower == "dr"]
        return cands[0].follower_char if cands else None

    assert follower("Dr. Smith") == "S"
    assert follower("dr. smith") == "s"


def test_uppercase_following_word_does_not_force_split_without_capitalized_follower_cue():
    text = "Ide o firmy, napr. XYZCorp a.s."
    seg = sentencesplit.Segmenter(language="sk", clean=False)

    assert [s.strip() for s in seg.segment(text)] == [text]


def test_sentence_start_override_uses_text_start_signature():
    # The supported hook signature is ``_is_likely_sentence_start(self, text, start=0)``;
    # the override receives the full text plus the offset of the candidate sentence
    # start, so it must index into ``text`` at ``start`` rather than slicing.
    class DemoAbbreviationReplacer(English.AbbreviationReplacer):
        def _is_likely_sentence_start(self, text: str, start: int = 0) -> bool:
            return text[start:].startswith("★")

    class Demo(Common, Standard):
        iso_code = "demo_custom_start"
        AbbreviationReplacer = DemoAbbreviationReplacer

    register_language("demo_custom_start", Demo)
    try:
        seg = sentencesplit.Segmenter(language="demo_custom_start", clean=False)
        assert [s.strip() for s in seg.segment("He earned a Ph.D. ★ Next.")] == [
            "He earned a Ph.D.",
            "★ Next.",
        ]
    finally:
        unregister_language("demo_custom_start")
