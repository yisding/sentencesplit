# -*- coding: utf-8 -*-
from __future__ import annotations


class SentenceSplitFactory:
    """sentencesplit as a spacy component through entrypoints"""

    def __init__(self, nlp, name: str = "sentencesplit", language: str = "en") -> None:
        self.nlp = nlp
        self.name = name
        # Deferred import avoids circular dependency with sentencesplit.__init__
        from sentencesplit import Segmenter

        self.seg = Segmenter(language=language, clean=False, char_span=True)

    def __call__(self, doc):
        sents_char_spans = self.seg.segment(doc.text_with_ws)
        start_token_ids = [sent.start for sent in sents_char_spans]
        for token in doc:
            token.is_sent_start = True if token.idx in start_token_ids else False
        return doc
