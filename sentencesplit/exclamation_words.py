# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.punctuation_replacer import replace_punctuation


class ExclamationWords:
    """
    Searches for exclamation points that are part of words
    and not ending punctuation and replaces them.
    """

    EXCLAMATION_WORDS = (
        "!Xũ !Kung ǃʼOǃKung !Xuun !Kung-Ekoka ǃHu ǃKhung ǃKu ǃung ǃXo ǃXû ǃXung ǃXũ !Xun Yahoo! Y!J Yum!".split()
    )
    # Longest first so a longer entry (e.g. "!Kung-Ekoka") is matched before a
    # shorter prefix ("!Kung") that would otherwise leave a dangling suffix.
    EXCLAMATION_REGEX = r"|".join(re.escape(w) for w in sorted(EXCLAMATION_WORDS, key=len, reverse=True))

    @classmethod
    def apply_rules(cls, text: str) -> str:
        return re.sub(ExclamationWords.EXCLAMATION_REGEX, replace_punctuation, text)
