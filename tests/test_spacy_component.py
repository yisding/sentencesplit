from sentencesplit.spacy_component import SentenceSplitFactory, create_sentencesplit


class FakeToken:
    def __init__(self, idx: int) -> None:
        self.idx = idx
        self.is_sent_start = None


class FakeDoc:
    def __init__(self, text: str, token_indices: list[int]) -> None:
        self.text = text
        self.tokens = [FakeToken(idx) for idx in token_indices]

    def __iter__(self):
        return iter(self.tokens)


def test_create_sentencesplit_is_importable_without_spacy_runtime():
    factory = create_sentencesplit(None, "sentencesplit", "en")

    assert isinstance(factory, SentenceSplitFactory)


def test_spacy_component_reads_doc_text():
    doc = FakeDoc("Hello. World.", [0, 1, 7])
    factory = SentenceSplitFactory(None)

    returned_doc = factory(doc)

    assert returned_doc is doc
    assert [token.is_sent_start for token in doc.tokens] == [True, False, True]


def test_spacy_component_marks_first_token_inside_leading_whitespace_span():
    doc = FakeDoc("\n  Hello. World.", [3, 10])
    factory = SentenceSplitFactory(None)

    returned_doc = factory(doc)

    assert returned_doc is doc
    assert [token.is_sent_start for token in doc.tokens] == [True, True]
