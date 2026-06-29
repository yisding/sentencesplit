import gc
import weakref

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


def test_language_profile_cache_does_not_pin_dynamic_language_classes():
    class Demo(Common, Standard):
        iso_code = "demo"

    profile = LanguageProfile.from_language(Demo)
    assert profile.abbreviation_replacer_cls is Demo.AbbreviationReplacer

    demo_ref = weakref.ref(Demo)
    del Demo
    del profile
    gc.collect()

    assert demo_ref() is None


def test_language_profile_resolves_static_rule_hooks():
    """Every per-language rule the Processor consumes is resolved on the profile.

    S2: the Processor reads only ``self.profile.*`` (one config channel), so the
    profile must carry every static ``self.lang.*`` rule hook the Processor used
    to read off the language class directly.
    """
    english = Language.get_language_code("en")
    profile = LanguageProfile.from_language(english)

    assert profile.punctuations == tuple(english.Punctuations)
    assert profile.multi_period_email_rule is english.Abbreviation.WithMultiplePeriodsAndEmailRule
    assert profile.geo_location_rule is english.GeoLocationRule
    assert profile.file_format_rule is english.FileFormatRule
    assert profile.dotnet_rule is english.DotNetRule
    assert profile.sub_single_quote_rule is english.SubSingleQuoteRule
    assert profile.single_newline_rule is english.SingleNewLineRule
    assert profile.question_mark_in_quotation_rule is english.QuestionMarkInQuotationRule
    assert profile.sub_symbols_table == tuple(english.SubSymbolsRules.SUBS_TABLE)
    assert profile.number_rules == tuple(english.Numbers.All)
    assert profile.ellipsis_rules == tuple(english.EllipsisRules.All)
    assert profile.ellipsis_three_consecutive_rule is english.EllipsisRules.ThreeConsecutiveRule
    assert profile.reinsert_ellipsis_rules == tuple(english.ReinsertEllipsisRules.All)
    assert profile.double_punct_rules == tuple(english.DoublePunctuationRules.All)
    assert profile.exclamation_rules == tuple(english.ExclamationPointRules.All)
    assert profile.exclamation_mid_sentence_rule is english.ExclamationPointRules.MidSentenceRule
    assert profile.exclamation_before_comma_rule is english.ExclamationPointRules.BeforeCommaMidSentenceRule


def test_language_profile_resolves_per_language_rule_overrides():
    """Per-language overrides (e.g. Punctuations, Numbers) are reflected on the profile."""
    arabic = Language.get_language_code("ar")
    arabic_profile = LanguageProfile.from_language(arabic)
    assert arabic_profile.punctuations == tuple(arabic.Punctuations)
    assert arabic_profile.punctuations != LanguageProfile.from_language(Language.get_language_code("en")).punctuations

    deutsch = Language.get_language_code("de")
    deutsch_profile = LanguageProfile.from_language(deutsch)
    assert deutsch_profile.number_rules == tuple(deutsch.Numbers.All)


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
