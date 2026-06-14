from __future__ import annotations

import re
import weakref
from dataclasses import dataclass
from threading import RLock

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lists_item_replacer import ListItemReplacer
from sentencesplit.utils import Rule, ensure_compiled

# Resolved profiles keyed by language class. Language classes are effectively
# immutable singletons, so a profile only needs to be built once per class. A
# WeakKeyDictionary lets a dynamically registered+unregistered language class be
# garbage-collected instead of being pinned forever by the cache.
_PROFILE_CACHE: "weakref.WeakKeyDictionary[type, LanguageProfile]" = weakref.WeakKeyDictionary()
_PROFILE_CACHE_LOCK = RLock()


@dataclass(frozen=True)
class LanguageProfile:
    """Resolved language hooks and compiled regexes used by the processor."""

    language: type
    abbreviation_replacer_cls: type[AbbreviationReplacer]
    between_punctuation_cls: type[BetweenPunctuation]
    list_item_replacer_cls: type[ListItemReplacer]
    cjk_abbreviation_rules: tuple[Rule, ...]
    cjk_reporting_clause_re: re.Pattern[str] | None
    colon_rule: Rule | None
    comma_rule: Rule | None
    latin_uppercase_resplit: bool
    sentence_boundary_re: re.Pattern[str]
    quotation_end_re: re.Pattern[str]
    split_quotation_re: re.Pattern[str]
    parens_dq_re: re.Pattern[str]
    continuous_punct_re: re.Pattern[str]
    numbered_ref_re: re.Pattern[str]
    double_punct_re: re.Pattern[str]
    # Static per-language rule hooks the Processor consumes. Languages keep
    # declaring these as class attributes; they are resolved here once so the
    # Processor reads only ``self.profile.*`` (one config channel).
    punctuations: tuple[str, ...]
    multi_period_email_rule: Rule
    geo_location_rule: Rule
    file_format_rule: Rule
    dotnet_rule: Rule
    sub_single_quote_rule: Rule
    single_newline_rule: Rule
    question_mark_in_quotation_rule: Rule
    sub_symbols_table: tuple[tuple[str, str], ...]
    number_rules: tuple[Rule, ...]
    ellipsis_rules: tuple[Rule, ...]
    ellipsis_three_consecutive_rule: Rule
    reinsert_ellipsis_rules: tuple[Rule, ...]
    double_punct_rules: tuple[Rule, ...]
    exclamation_rules: tuple[Rule, ...]
    exclamation_mid_sentence_rule: Rule
    exclamation_before_comma_rule: Rule

    @classmethod
    def from_language(cls, lang) -> LanguageProfile:
        # A language's hooks are immutable class attributes, so the resolved
        # profile is fully determined by the class — cache it to avoid rebuilding
        # one (and re-running getattr/regex resolution) on every Segmenter call.
        with _PROFILE_CACHE_LOCK:
            cached = _PROFILE_CACHE.get(lang)
            if cached is not None:
                return cached
            profile = cls._build(lang)
            _PROFILE_CACHE[lang] = profile
            return profile

    @classmethod
    def _build(cls, lang) -> LanguageProfile:
        cjk_rules = tuple(getattr(getattr(lang, "CjkAbbreviationRules", None), "All", ()))
        clause_regex = getattr(lang, "CJK_REPORTING_CLAUSE_REGEX", None)
        ellipsis_rules = lang.EllipsisRules
        exclamation_rules = lang.ExclamationPointRules
        return cls(
            language=lang,
            abbreviation_replacer_cls=getattr(lang, "AbbreviationReplacer", AbbreviationReplacer),
            between_punctuation_cls=getattr(lang, "BetweenPunctuation", BetweenPunctuation),
            list_item_replacer_cls=getattr(lang, "ListItemReplacer", ListItemReplacer),
            cjk_abbreviation_rules=cjk_rules,
            cjk_reporting_clause_re=ensure_compiled(clause_regex) if clause_regex is not None else None,
            colon_rule=getattr(lang, "ReplaceColonBetweenNumbersRule", None),
            comma_rule=getattr(lang, "ReplaceNonSentenceBoundaryCommaRule", None),
            latin_uppercase_resplit=getattr(lang, "LATIN_UPPERCASE_RESPLIT", True),
            sentence_boundary_re=ensure_compiled(lang.SENTENCE_BOUNDARY_REGEX),
            quotation_end_re=ensure_compiled(lang.QUOTATION_AT_END_OF_SENTENCE_REGEX),
            split_quotation_re=ensure_compiled(lang.SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX),
            parens_dq_re=ensure_compiled(lang.PARENS_BETWEEN_DOUBLE_QUOTES_REGEX),
            continuous_punct_re=ensure_compiled(lang.CONTINUOUS_PUNCTUATION_REGEX),
            numbered_ref_re=ensure_compiled(lang.NUMBERED_REFERENCE_REGEX),
            double_punct_re=ensure_compiled(lang.DoublePunctuationRules.DoublePunctuation),
            punctuations=tuple(lang.Punctuations),
            multi_period_email_rule=lang.Abbreviation.WithMultiplePeriodsAndEmailRule,
            geo_location_rule=lang.GeoLocationRule,
            file_format_rule=lang.FileFormatRule,
            dotnet_rule=lang.DotNetRule,
            sub_single_quote_rule=lang.SubSingleQuoteRule,
            single_newline_rule=lang.SingleNewLineRule,
            question_mark_in_quotation_rule=lang.QuestionMarkInQuotationRule,
            sub_symbols_table=tuple(lang.SubSymbolsRules.SUBS_TABLE),
            number_rules=tuple(lang.Numbers.All),
            ellipsis_rules=tuple(ellipsis_rules.All),
            ellipsis_three_consecutive_rule=ellipsis_rules.ThreeConsecutiveRule,
            reinsert_ellipsis_rules=tuple(lang.ReinsertEllipsisRules.All),
            double_punct_rules=tuple(lang.DoublePunctuationRules.All),
            exclamation_rules=tuple(exclamation_rules.All),
            exclamation_mid_sentence_rule=exclamation_rules.MidSentenceRule,
            exclamation_before_comma_rule=exclamation_rules.BeforeCommaMidSentenceRule,
        )
