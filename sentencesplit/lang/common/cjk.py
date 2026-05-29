# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.processor import Processor
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule

_QUOTE_CLOSER_RE = re.compile(r"""["'”’」』》】]+$""")

_CJK_SLANTED_QUOTE_END_RE = re.compile(r"(&ᓰ&|&ᓱ&|&ᓳ&|&ᓴ&|&ᓷ&|&ᓸ&)(?=[”’][^\s])")
_CJK_REPORTING_CLAUSE_BOUNDARY = r"(?=$|[，,：:。．.!！?？…])"

# Chinese reporting-clause regex, shared by zh and the en_es_zh combined profile
# (Japanese uses its own verbs). A quote followed by "<subject>…<reporting verb>"
# (他说 / 记者表示 / …) is a single reported sentence, so it is re-merged.
CJK_REPORTING_CLAUSE_RE = re.compile(
    rf"^(?:他|她|他们|她们|我|我们|记者|警方|老师|母亲|父亲|主持人|发言人).{{0,6}}(?:说|问|答|表示|回应|补充|解释){_CJK_REPORTING_CLAUSE_BOUNDARY}"
)


def make_cjk_abbreviation_rules(cjk_char_class: str) -> list[Rule]:
    """Build the two CJK abbreviation-period rules for a given ideograph range.

    Languages differ only in which CJK code points count as a "following CJK
    char" (zh: BMP unified ideographs, ja: + kana, en_es_zh: + Extension A), so
    the rule bodies are shared and only the char class varies.
    """
    return [
        Rule(r"(?<=[A-Za-z])\.(?=[A-Za-z]\.)", "∯"),
        Rule(rf"(?<=[A-Za-z]∯[A-Za-z])\.(?=[{cjk_char_class}])", "∯"),
    ]


_RESTORE_CJK_TERMINAL_PUNCT = {
    "&ᓰ&": "。",
    "&ᓱ&": "．",
    "&ᓳ&": "！",
    "&ᓴ&": "!",
    "&ᓷ&": "?",
    "&ᓸ&": "？",
}

_CJK_DOUBLE_ANGLE_QUOTE_RE = re.compile(r"《(?=(?P<tmp>[^》\\]+|\\{2}|\\.)*)(?P=tmp)》")
_CJK_L_BRACKET_RE = re.compile(r"「(?=(?P<tmp>[^」\\]+|\\{2}|\\.)*)(?P=tmp)」")
_CJK_CORNER_QUOTE_RE = re.compile(r"『(?=(?P<tmp>[^』\\]+|\\{2}|\\.)*)(?P=tmp)』")
_CJK_FULLWIDTH_PAREN_RE = re.compile(r"（(?=(?P<tmp>[^）\\]+|\\{2}|\\.)*)(?P=tmp)）")


class CJKBetweenPunctuationMixin:
    """Shared between-punctuation helpers for CJK quotes and full-width parens.

    Subclasses inherit ``BetweenPunctuation`` and call ``apply_cjk_punctuation(txt)``
    inside their ``replace()`` override (after ``super().replace()``) to protect
    punctuation inside CJK delimiters from splitting sentences. Also restores the
    CJK terminal-punctuation placeholders that the base slanted-quote step
    consumes when they appear at quote-final position followed by non-space.
    """

    def apply_cjk_punctuation(self, txt: str) -> str:
        txt = _CJK_DOUBLE_ANGLE_QUOTE_RE.sub(replace_punctuation, txt)
        txt = _CJK_L_BRACKET_RE.sub(replace_punctuation, txt)
        txt = _CJK_CORNER_QUOTE_RE.sub(replace_punctuation, txt)
        txt = _CJK_FULLWIDTH_PAREN_RE.sub(replace_punctuation, txt)
        return _CJK_SLANTED_QUOTE_END_RE.sub(lambda m: _RESTORE_CJK_TERMINAL_PUNCT[m.group(1)], txt)


class CJKBoundaryProfile:
    """Boundary defaults for CJK scripts that do not assume Latin uppercase starts."""

    # Include temporary placeholders from DoublePunctuationRules so CJK
    # boundary matching still works before SubSymbols restoration.
    _CJK_SENTENCE_END = r"[。．.！!?？☉☈☇☄☊☋☌☍]"
    _CJK_CLOSERS = r"[\]\"')”’」』》〉】）〕〗〙〛]"

    SENTENCE_BOUNDARY_REGEX = re.compile(rf".*?{_CJK_SENTENCE_END}{_CJK_CLOSERS}*|.*?$")
    QUOTATION_AT_END_OF_SENTENCE_REGEX = re.compile(rf"{_CJK_SENTENCE_END}{_CJK_CLOSERS}\s+[^\s]")
    SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX = re.compile(rf"(?<={_CJK_SENTENCE_END}{_CJK_CLOSERS})\s+(?=[^\s])")

    # Heuristic in processor.py depends on " Capital" starts and should not run for CJK.
    LATIN_UPPERCASE_RESPLIT = False


class CJKProcessor(Processor):
    def split_into_segments(self, text: str | None = None) -> list[str]:
        return self._merge_quote_continuations(super().split_into_segments(text))

    def _merge_quote_continuations(self, sentences: list[str]) -> list[str]:
        clause_regex = self.profile.cjk_reporting_clause_re
        if clause_regex is None:
            return sentences

        merged: list[str] = []
        for current in sentences:
            if merged and self._should_merge_quote_continuation(merged[-1], current, clause_regex):
                merged[-1] = merged[-1] + current.lstrip()
            else:
                merged.append(current)
        return merged

    def _should_merge_quote_continuation(self, previous: str, current: str, clause_regex) -> bool:
        previous = previous.rstrip()
        current = current.lstrip()
        if not previous or not current:
            return False
        if not _QUOTE_CLOSER_RE.search(previous):
            return False
        return bool(clause_regex.match(current))
