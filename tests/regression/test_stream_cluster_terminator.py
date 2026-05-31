# -*- coding: utf-8 -*-
"""Regression: StreamSegmenter must not emit a fragment when a chunk boundary
lands inside a still-growing multi-character terminator.

Previously, feeding a chunk that ended part-way through an ellipsis ("..") or a
"!!"/"??" run made segment_spans() place a boundary inside the incomplete
cluster; the leading piece was a *non-final* span and was emitted immediately
("Wait." out of "Wait..."), shattering the sentence even though more of the
cluster was still arriving. _detect now holds a non-final span whose boundary
abuts more terminal punctuation until the cluster resolves.
"""

import sentencesplit
from sentencesplit import StreamSegmenter


def _stream(chunks, **kwargs):
    stream = StreamSegmenter(language="en", **kwargs)
    out = []
    for chunk in chunks:
        stream.feed(chunk)
        out.extend(stream.get_completed_sentences())
    out.extend(stream.flush())
    return out


def test_ellipsis_split_across_chunks_is_not_shattered():
    # A chunk that carries the partial cluster ("..") makes "Wait." a non-final
    # span; the guard holds it until the ellipsis completes.
    seg = sentencesplit.Segmenter(language="en").segment("Wait... Now go.")
    assert _stream(["Wait..", ". Now go."]) == seg
    assert _stream(["I will wait..", ". Then go now."]) == sentencesplit.Segmenter(language="en").segment(
        "I will wait... Then go now."
    )


def test_normal_boundary_still_emits_promptly():
    # The cluster guard must not delay an ordinary boundary followed by a letter.
    stream = StreamSegmenter(language="en")
    stream.feed("One. Two")
    assert stream.get_completed_sentences() == ["One. "]


def test_final_span_cluster_is_text_preserving_documented_limitation():
    # When a chunk ends *exactly* on the first char of a cluster ("Wait."), that
    # leading piece is a complete-looking FINAL span and is emitted before the
    # rest of the cluster arrives — indistinguishable from a real boundary
    # without lookahead changes. This is the documented text-preservation-only
    # contract for fine-grained feeds: text is never lost or duplicated.
    out = _stream(["Wait.", ".. Now go."])
    assert "".join(out) == "Wait... Now go."
