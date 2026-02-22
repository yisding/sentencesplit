"""
Example of pySBD as a sentencizer component for spaCy

Installation:
pip install spacy
"""

import spacy
from spacy.language import Language

import pysbd


@Language.component("pysbd_sentence_boundaries")
def pysbd_sentence_boundaries(doc):
    seg = pysbd.Segmenter(language="en", clean=False, char_span=True)
    sents_char_spans = seg.segment(doc.text)
    start_char_offsets = {span.start for span in sents_char_spans}
    for token in doc:
        token.is_sent_start = token.idx in start_char_offsets
    return doc


if __name__ == "__main__":
    text = "My name is Jonas E. Smith.          Please turn to p. 55."
    nlp = spacy.blank("en")

    # add as a spaCy pipeline component
    nlp.add_pipe("pysbd_sentence_boundaries")

    doc = nlp(text)
    print("sent_id", "sentence", sep="\t|\t")
    for sent_id, sent in enumerate(doc.sents, start=1):
        print(sent_id, sent.text, sep="\t|\t")
