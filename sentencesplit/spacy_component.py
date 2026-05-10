# -*- coding: utf-8 -*-
from __future__ import annotations

import re


class SentenceSplitFactory:
    """sentencesplit as a spacy component through entrypoints"""

    def __init__(self, nlp, name: str = "sentencesplit", language: str = "en") -> None:
        self.nlp = nlp
        self.name = name
        # Deferred import avoids circular dependency with sentencesplit.__init__
        from sentencesplit import Segmenter

        self.seg = Segmenter(language=language, clean=False, char_span=True)

    def __call__(self, doc):
        sents_char_spans = self.seg.segment(doc.text)
        tokens = list(doc)
        start_token_ids = _sentence_start_token_indices(tokens, sents_char_spans)
        for token in tokens:
            token.is_sent_start = True if token.idx in start_token_ids else False
        return doc


def _sentence_start_token_indices(tokens, sentence_spans):
    start_token_ids = set()
    token_index = 0
    for sent in sentence_spans:
        while token_index < len(tokens) and tokens[token_index].idx < sent.start:
            token_index += 1
        search_index = token_index
        while search_index < len(tokens) and tokens[search_index].idx < sent.end:
            start_token_ids.add(tokens[search_index].idx)
            token_index = search_index + 1
            break
        else:
            token_index = search_index
    return start_token_ids


def create_sentencesplit(nlp, name, language):
    return SentenceSplitFactory(nlp, name, language)


try:
    import spacy
except ImportError:
    pass
else:
    _match = re.match(r"(\d+)\.(\d+)", spacy.__version__)
    if _match is None or (int(_match[1]), int(_match[2])) < (3, 8):
        raise ImportError(f"sentencesplit requires spaCy >= 3.8, found {spacy.__version__}")

    from spacy.language import Language

    Language.factory("sentencesplit", default_config={"language": "en"})(create_sentencesplit)
