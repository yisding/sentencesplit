# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import List

from pysbd.cleaner import Cleaner
from pysbd.languages import Language
from pysbd.processor import Processor
from pysbd.utils import TextSpan


class Segmenter:
    def __init__(
        self, language: str = "en", clean: bool = False, doc_type: str | None = None, char_span: bool = False
    ) -> None:
        """Segments a text into a list of sentences
        with or without character offsets from original text

        Parameters
        ----------
        language : str, required
            specify a language use its two character ISO 639-1 code,
            by default "en"
        clean : bool, optional
            cleans original text, by default False
        doc_type : [type], optional
            Normal text or OCRed text, by default None
            set to `pdf` for OCRed text
        char_span : bool, optional
            Get start & end character offsets of each sentences
            within original text, by default False
        """
        self.language = language
        self.language_module = Language.get_language_code(language)
        self.clean = clean
        self.doc_type = doc_type
        self.char_span = char_span
        if self.clean and self.char_span:
            raise ValueError("char_span must be False if clean is True. Since `clean=True` will modify original text.")
        # when doctype is pdf then force user to clean the text
        # char_span func wont be provided with pdf doctype also
        elif self.doc_type == "pdf" and not self.clean:
            raise ValueError(
                "`doc_type='pdf'` should have `clean=True` & `char_span` should be False since originaltext will be modified."
            )

    def cleaner(self, text: str):
        if hasattr(self.language_module, "Cleaner"):
            return self.language_module.Cleaner(text, self.language_module, doc_type=self.doc_type)
        else:
            return Cleaner(text, self.language_module, doc_type=self.doc_type)

    def processor(self, text: str):
        if hasattr(self.language_module, "Processor"):
            return self.language_module.Processor(text, self.language_module, char_span=self.char_span)
        else:
            return Processor(text, self.language_module, char_span=self.char_span)

    def _match_spans(self, sentences: List[str], original_text: str):
        """Match processed sentences back to spans in the original text.

        Yields (text_slice, start, end) tuples for each sentence.
        Accounts for trailing whitespace that SENTENCE_BOUNDARY_REGEX
        does not capture, keeping the segmentation non-destructive.
        """
        prior_end = 0
        for sent in sentences:
            if not sent:
                continue
            start_idx = original_text.find(sent, prior_end)
            if start_idx == -1:
                for match in re.finditer(rf"{re.escape(sent)}\s*", original_text):
                    match_start, match_end = match.span()
                    if match_end > prior_end:
                        yield match.group(), match_start, match_end
                        prior_end = match_end
                        break
                continue
            end_idx = start_idx + len(sent)
            while end_idx < len(original_text) and original_text[end_idx].isspace():
                end_idx += 1
            yield original_text[start_idx:end_idx], start_idx, end_idx
            prior_end = end_idx

    def segment(self, text: str | None) -> List[str] | List[TextSpan]:
        if not text:
            return []

        original_text = text
        if self.clean or self.doc_type == "pdf":
            text = self.cleaner(text).clean()

        postprocessed_sents = self.processor(text).process()

        if self.char_span:
            return [TextSpan(s, start, end) for s, start, end in self._match_spans(postprocessed_sents, original_text)]
        if self.clean:
            # clean and destructed sentences
            return postprocessed_sents
        # nondestructive: return original text spans preserving whitespace
        return [s for s, _, _ in self._match_spans(postprocessed_sents, original_text)]

    def segment_spans(self, text: str | None) -> List[TextSpan]:
        """Return sentence spans regardless of the instance's char_span flag."""
        if self.clean:
            raise ValueError("segment_spans() requires clean=False.")
        seg = Segmenter(language=self.language, clean=False, doc_type=self.doc_type, char_span=True)
        return seg.segment(text)

    def segment_clean(self, text: str | None) -> List[str]:
        """Return cleaned sentences regardless of the instance's clean flag."""
        seg = Segmenter(language=self.language, clean=True, doc_type=self.doc_type, char_span=False)
        return seg.segment(text)
