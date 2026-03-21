# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.processor import Processor

_QUOTE_CLOSER_RE = re.compile(r"""["'”’」』》】]+$""")


class CJKBoundaryProfile:
    """Boundary defaults for CJK scripts that do not assume Latin uppercase starts."""

    # Include temporary placeholders from DoublePunctuationRules so CJK
    # boundary matching still works before SubSymbols restoration.
    _CJK_SENTENCE_END = r"[。．.！!?？☉☈☇☄☊☋☌☍]"
    _CJK_CLOSERS = r"[\]\"')”’」』》〉】）〕〗〙〛]"

    SENTENCE_BOUNDARY_REGEX = rf".*?{_CJK_SENTENCE_END}{_CJK_CLOSERS}*|.*?$"
    QUOTATION_AT_END_OF_SENTENCE_REGEX = rf"{_CJK_SENTENCE_END}{_CJK_CLOSERS}\s+[^\s]"
    SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX = rf"(?<={_CJK_SENTENCE_END}{_CJK_CLOSERS})\s+(?=[^\s])"

    # Heuristic in processor.py depends on " Capital" starts and should not run for CJK.
    LATIN_UPPERCASE_RESPLIT = False


class CJKProcessor(Processor):
    def split_into_segments(self) -> list[str]:
        return self._merge_quote_continuations(super().split_into_segments())

    def _merge_quote_continuations(self, sentences: list[str]) -> list[str]:
        clause_regex = getattr(self.lang, "CJK_REPORTING_CLAUSE_REGEX", None)
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
