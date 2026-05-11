from __future__ import annotations

import re
from dataclasses import dataclass

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lists_item_replacer import ListItemReplacer
from sentencesplit.utils import Rule, ensure_compiled


@dataclass(frozen=True)
class LanguageProfile:
    """Resolved language hooks and compiled regexes used by the processor."""

    abbreviation_replacer_cls: type[AbbreviationReplacer]
    between_punctuation_cls: type[BetweenPunctuation]
    list_item_replacer_cls: type[ListItemReplacer]
    cjk_abbreviation_rules: tuple[Rule, ...]
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

    @classmethod
    def from_language(cls, lang) -> LanguageProfile:
        cjk_rules = tuple(getattr(getattr(lang, "CjkAbbreviationRules", None), "All", ()))
        return cls(
            abbreviation_replacer_cls=getattr(lang, "AbbreviationReplacer", AbbreviationReplacer),
            between_punctuation_cls=getattr(lang, "BetweenPunctuation", BetweenPunctuation),
            list_item_replacer_cls=getattr(lang, "ListItemReplacer", ListItemReplacer),
            cjk_abbreviation_rules=cjk_rules,
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
        )
