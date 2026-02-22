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
    _EXCLAMATION_RE = re.compile(r"|".join(re.escape(w) for w in EXCLAMATION_WORDS))

    @classmethod
    def apply_rules(cls, text: str) -> str:
        return cls._EXCLAMATION_RE.sub(replace_punctuation, text)
