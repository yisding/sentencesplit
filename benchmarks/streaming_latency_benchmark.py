"""Latency-to-first-stable-sentence benchmark for StreamSegmenter.

Simulates a token-by-token stream (as from an LLM or ASR) and measures, per
sentence, how many tokens had to arrive *after* the sentence's last character
before StreamSegmenter emitted it. This "emission lag" is the streaming cost of
the lookahead buffering: conservative trades a few tokens of lag for never
speaking a half-formed sentence; aggressive trims the lag by trusting terminal
punctuation immediately.

Run with:
    uv run python benchmarks/streaming_latency_benchmark.py
"""

from __future__ import annotations

import statistics
import time

from sentencesplit import StreamSegmenter

# A handful of multi-sentence samples with the ambiguities that make streaming
# interesting: abbreviations, decimals, and clean boundaries.
SAMPLES = {
    "en": (
        "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 p.m. "
        "The model is GPT 3.1 and it is fast. That is all for now. Goodbye."
    ),
    "es": "El Dr. García fue a Madrid. Llegó el 5 de ene. a las 3 p.m. Todo salió bien. Hasta luego.",
    "de": "Herr Dr. Müller ging nach Berlin. Er kam am 5. Jan. um 15 Uhr an. Alles war gut. Auf Wiedersehen.",
    "zh": "史密斯博士去了华盛顿。他于1月5日下午3点到达。一切都很顺利。再见。",
}


def _tokenize(text):
    """Cheap word/whitespace token stream, keeping the delimiters attached."""
    tokens = []
    current = ""
    for ch in text:
        current += ch
        if ch == " ":
            tokens.append(current)
            current = ""
    if current:
        tokens.append(current)
    return tokens


def _emission_lags(language, text, buffering_mode):
    """Return the per-sentence emission lag, in tokens, for one sample."""
    stream = StreamSegmenter(language=language, buffering_mode=buffering_mode)
    tokens = _tokenize(text)

    lags = []
    chars_fed = 0
    # Map each emitted sentence's end offset to the token index that produced it.
    char_to_token_end = []
    running = 0
    for idx, tok in enumerate(tokens):
        running += len(tok)
        char_to_token_end.append((running, idx))

    emitted_chars = 0
    for token_index, tok in enumerate(tokens):
        chars_fed += len(tok)
        stream.feed(tok)
        for sent in stream.get_completed_sentences():
            emitted_chars += len(sent)
            content_end = len(sent.rstrip())
            # Token index at which the sentence's last content char arrived.
            produced_at = next(
                (i for end, i in char_to_token_end if end >= emitted_chars - (len(sent) - content_end)),
                token_index,
            )
            lags.append(token_index - produced_at)
    stream.flush()
    return lags


def main():
    print("StreamSegmenter latency-to-stable-sentence benchmark")
    print("=" * 64)
    for mode in ("conservative", "aggressive"):
        all_lags = []
        t0 = time.perf_counter()
        for language, text in SAMPLES.items():
            all_lags.extend(_emission_lags(language, text, mode))
        elapsed = (time.perf_counter() - t0) * 1000
        if all_lags:
            all_lags.sort()
            median = statistics.median(all_lags)
            p95 = all_lags[min(len(all_lags) - 1, int(0.95 * len(all_lags)))]
            p99 = all_lags[min(len(all_lags) - 1, int(0.99 * len(all_lags)))]
        else:
            median = p95 = p99 = 0
        print(f"\n  mode = {mode}")
        print(f"    sentences emitted : {len(all_lags)}")
        print(f"    emission lag (tokens): median={median}  p95={p95}  p99={p99}")
        print(f"    wall time (all samples): {elapsed:.2f} ms")
    print("\nLower lag = lower latency. Aggressive should match or beat conservative.")


if __name__ == "__main__":
    main()
