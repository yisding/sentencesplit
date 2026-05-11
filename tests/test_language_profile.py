import sentencesplit
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.language_profile import LanguageProfile
from sentencesplit.languages import LANGUAGE_CODES, Language
from sentencesplit.lists_item_replacer import ListItemReplacer
from sentencesplit.processor import Processor


def test_language_profile_resolves_default_and_custom_hooks():
    english = Language.get_language_code("en")
    english_profile = LanguageProfile.from_language(english)

    assert english_profile.abbreviation_replacer_cls is english.AbbreviationReplacer
    assert english_profile.between_punctuation_cls is BetweenPunctuation
    assert english_profile.list_item_replacer_cls is ListItemReplacer
    assert english_profile.cjk_abbreviation_rules == ()
    assert english_profile.colon_rule is None
    assert english_profile.comma_rule is None
    assert english_profile.latin_uppercase_resplit is True

    hybrid = Language.get_language_code("en_es_zh")
    hybrid_profile = LanguageProfile.from_language(hybrid)

    assert hybrid_profile.abbreviation_replacer_cls is hybrid.AbbreviationReplacer
    assert hybrid_profile.between_punctuation_cls is hybrid.BetweenPunctuation
    assert hybrid_profile.list_item_replacer_cls is ListItemReplacer
    assert hybrid_profile.cjk_abbreviation_rules == tuple(hybrid.CjkAbbreviationRules.All)
    assert hybrid_profile.latin_uppercase_resplit is False


def test_language_profile_resolves_custom_list_item_replacer_hook():
    class DemoListItemReplacer(ListItemReplacer):
        def add_line_break(self):
            self.format_numbered_list_with_periods()
            self.format_numbered_list_with_parens()
            return self.text

    class Demo(Common, Standard):
        iso_code = "demo"
        ListItemReplacer = DemoListItemReplacer

    profile = LanguageProfile.from_language(Demo)

    assert profile.list_item_replacer_cls is DemoListItemReplacer


def test_processor_uses_custom_list_item_replacer_hook():
    class DemoListItemReplacer(ListItemReplacer):
        def add_line_break(self):
            self.text = self.text.replace(" HOOK ", "\r")
            return self.text

    class Demo(Common, Standard):
        iso_code = "demo"
        ListItemReplacer = DemoListItemReplacer

    assert [s.strip() for s in Processor("Before HOOK After.", Demo).process()] == ["Before", "After."]


def test_custom_processor_hook_example_works():
    class Demo(Common, Standard):
        iso_code = "demo"

        class Processor(Processor):
            def replace_numbers(self, text: str) -> str:
                text = super().replace_numbers(text)
                return text.replace("§.", "§∯")

    LANGUAGE_CODES["demo"] = Demo
    try:
        seg = sentencesplit.Segmenter(language="demo", clean=False)
        assert [s.strip() for s in seg.segment("Section §. 5 applies. Next sentence.")] == [
            "Section §. 5 applies.",
            "Next sentence.",
        ]
    finally:
        del LANGUAGE_CODES["demo"]
