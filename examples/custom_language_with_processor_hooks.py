"""
Example of registering a custom language profile with processor hook overrides.

Run with:
    uv run python examples/custom_language_with_processor_hooks.py
"""

from __future__ import annotations

import sentencesplit
from sentencesplit.lang.common import Common, Standard
from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.processor import Processor


class Demo(Common, Standard):
    iso_code = "demo"

    class Processor(Processor):
        def replace_numbers(self, text: str) -> str:
            text = super().replace_numbers(text)
            # Treat "§." as a protected non-boundary marker in this custom profile.
            return text.replace("§.", "§∯")

        def _resplit_segments(self, sentences: list[str]) -> list[str]:
            return super()._resplit_segments(sentences)


if __name__ == "__main__":
    LANGUAGE_CODES["demo"] = Demo
    try:
        seg = sentencesplit.Segmenter(language="demo", clean=False)
        print(seg.segment("Section §. 5 applies. Next sentence."))
    finally:
        del LANGUAGE_CODES["demo"]
