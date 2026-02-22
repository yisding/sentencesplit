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


try:
    import spacy
except ImportError:
    pass
else:
    _spacy_version = tuple(int(x) for x in spacy.__version__.split(".")[:2])
    if _spacy_version < (3, 8):
        raise ImportError(f"sentencesplit requires spaCy >= 3.8, found {spacy.__version__}")

    from spacy.language import Language

    @Language.factory("sentencesplit", default_config={"language": "en"})
    def create_sentencesplit(nlp, name, language):
        return SentenceSplitFactory(nlp, name, language)
