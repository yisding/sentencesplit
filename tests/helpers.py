from __future__ import annotations

from sentencesplit.utils import TextSpan


def assert_segments(segmenter, text: str, expected: list[str], *, strip: bool = True) -> None:
    segments = segmenter.segment(text)
    if strip:
        segments = [segment.strip() for segment in segments]
    assert segments == expected


def assert_span_contract(text: str, spans: list[TextSpan]) -> None:
    for span in spans:
        assert isinstance(span, TextSpan)
        assert text[span.start : span.end] == span.sent

    if not spans:
        assert text == ""
        return

    for span in spans:
        assert 0 <= span.start < span.end <= len(text)

    assert spans[0].start == 0
    assert spans[-1].end == len(text)

    prev_end = 0
    for span in spans:
        assert span.start == prev_end
        prev_end = span.end

    assert "".join(span.sent for span in spans) == text
