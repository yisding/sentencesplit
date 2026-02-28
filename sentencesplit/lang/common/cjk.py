# -*- coding: utf-8 -*-


class CJKBoundaryProfile:
    """Boundary defaults for CJK scripts that do not assume Latin uppercase starts."""

    _CJK_SENTENCE_END = r"[。．.！!?？]"
    _CJK_CLOSERS = r"[\"'“”’」』》〉】）〕〗〙〛]"

    SENTENCE_BOUNDARY_REGEX = rf"\S[^\n。．.！!?？]*{_CJK_SENTENCE_END}{_CJK_CLOSERS}*|.+$"
    QUOTATION_AT_END_OF_SENTENCE_REGEX = rf"{_CJK_SENTENCE_END}{_CJK_CLOSERS}\s+[^\s]"
    SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX = rf"(?<={_CJK_SENTENCE_END}{_CJK_CLOSERS})\s+(?=[^\s])"

    # Heuristic in processor.py depends on " Capital" starts and should not run for CJK.
    LATIN_UPPERCASE_RESPLIT = False
