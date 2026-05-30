"""Recipe: stream an LLM's token output into a TTS engine, one sentence at a time.

A voice agent wants to start speaking as soon as a *complete* sentence is ready,
without ever speaking a half-formed one (which sounds broken) and without
re-speaking text. ``StreamSegmenter`` solves exactly this: feed it the LLM's
token deltas, and it hands back whole sentences only once their boundary is
stable, holding ambiguous tails (``Dr.``, ``GPT 3.``) until the next token
resolves them.

Run with:
    uv run python examples/streaming_to_tts_recipe.py
"""

from __future__ import annotations

from sentencesplit import StreamSegmenter


def fake_llm_token_stream():
    """Stand-in for an LLM streaming API yielding token deltas.

    Note the ambiguities a naive ``"split on '.'"`` would get wrong: the
    abbreviation "Dr." and the version number "GPT 3.1".
    """
    yield from [
        "Hello",
        "! ",
        "I",
        " spoke",
        " with",
        " Dr",
        ".",
        " Smith",
        " yesterday",
        ". ",
        "He",
        " uses",
        " GPT",
        " 3",
        ".",
        "1",
        " daily",
        ". ",
        "Goodbye",
        ".",
    ]


def speak(sentence: str) -> None:
    """Stand-in for a TTS engine. Replace with your synthesizer's enqueue call."""
    print(f"  [TTS] -> {sentence!r}")


def main():
    # Conservative buffering (the default) is the right choice for TTS: it never
    # emits an ambiguous tail, so the synthesizer never speaks "Dr" as a
    # sentence or "GPT 3" before learning it is "GPT 3.1".
    stream = StreamSegmenter(language="en", buffering_mode="conservative")

    spoken = []
    print("Streaming LLM tokens into TTS, sentence by sentence:\n")
    for token in fake_llm_token_stream():
        stream.feed(token)
        for sentence in stream.get_completed_sentences():
            speak(sentence)
            spoken.append(sentence)

    # End of stream: flush whatever sentence is still buffered (here "Goodbye.",
    # whose boundary lookahead held because no trailing token followed it).
    for sentence in stream.flush():
        speak(sentence)
        spoken.append(sentence)

    # Sanity: TTS spoke every character exactly once, in order, no duplication.
    full = "".join(t for t in fake_llm_token_stream())
    assert "".join(spoken) == full, "TTS stream dropped or duplicated text!"
    print(f"\nVerified: spoke {len(spoken)} sentences covering the full output exactly once.")


if __name__ == "__main__":
    main()
