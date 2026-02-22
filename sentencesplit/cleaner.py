# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.clean.rules import HTML, PDF
from sentencesplit.clean.rules import CleanRules as cr
from sentencesplit.utils import apply_rules


class Cleaner:
    def __init__(self, text: str | None, lang, doc_type: str | None = None) -> None:
        self.text = text
        self.lang = lang
        self.doc_type = doc_type

    def clean(self) -> str | None:
        if not self.text:
            return self.text
        self.remove_all_newlines()
        self.replace_double_newlines()
        self.replace_newlines()
        self.replace_escaped_newlines()
        self.text = apply_rules(self.text, *HTML.All)
        self.replace_punctuation_in_brackets()
        self.text = apply_rules(self.text, cr.InlineFormattingRule)
        self.clean_quotations()
        self.clean_table_of_contents()
        self.check_for_no_space_in_between_sentences()
        self.clean_consecutive_characters()
        return self.text

    def remove_all_newlines(self):
        self.remove_newline_in_middle_of_sentence()
        self.remove_newline_in_middle_of_word()

    def remove_newline_in_middle_of_sentence(self):
        def replace_w_blank(match):
            match = match.group()
            sub = re.sub(cr.NEWLINE_IN_MIDDLE_OF_SENTENCE_REGEX, "", match)
            return sub

        self.text = re.sub(r"(?:[^\.])*", replace_w_blank, self.text)

    def remove_newline_in_middle_of_word(self):
        self.text = apply_rules(self.text, cr.NewLineInMiddleOfWordRule)

    def replace_double_newlines(self):
        self.text = apply_rules(
            self.text,
            cr.DoubleNewLineWithSpaceRule,
            cr.DoubleNewLineRule,
        )

    def remove_pdf_line_breaks(self):
        self.text = apply_rules(
            self.text,
            cr.NewLineFollowedByBulletRule,
            PDF.NewLineInMiddleOfSentenceRule,
            PDF.NewLineInMiddleOfSentenceNoSpacesRule,
        )

    def replace_newlines(self):
        if self.doc_type == "pdf":
            self.remove_pdf_line_breaks()
        else:
            self.text = apply_rules(
                self.text,
                cr.NewLineFollowedByPeriodRule,
                cr.ReplaceNewlineWithCarriageReturnRule,
            )

    def replace_escaped_newlines(self):
        self.text = apply_rules(
            self.text,
            cr.EscapedNewLineRule,
            cr.EscapedCarriageReturnRule,
            cr.TypoEscapedNewLineRule,
            cr.TypoEscapedCarriageReturnRule,
        )

    def replace_punctuation_in_brackets(self):
        def replace_punct(match):
            match = match.group()
            if "?" in match:
                sub = re.sub(re.escape("?"), "&ᓷ&", match)
                return sub
            return match

        self.text = re.sub(r"\[(?:[^\]])*\]", replace_punct, self.text)

    def clean_quotations(self):
        # method added explicitly
        # pragmatic-segmenter applies this method
        # at different location
        self.text = re.sub("`", "'", self.text)
        self.text = apply_rules(
            self.text,
            cr.QuotationsFirstRule,
            cr.QuotationsSecondRule,
        )

    def clean_table_of_contents(self):
        self.text = apply_rules(
            self.text,
            cr.TableOfContentsRule,
            cr.ConsecutivePeriodsRule,
            cr.ConsecutiveForwardSlashRule,
        )

    def search_for_connected_sentences(self, word: str, regex, rule) -> str:
        if not re.search(regex, word):
            return word
        if any(k in word for k in cr.URL_EMAIL_KEYWORDS):
            return word
        new_word = apply_rules(word, rule)
        return new_word

    def check_for_no_space_in_between_sentences(self):
        words = self.text.split(" ")
        for idx, word in enumerate(words):
            word = self.search_for_connected_sentences(
                word,
                cr.NO_SPACE_BETWEEN_SENTENCES_REGEX,
                cr.NoSpaceBetweenSentencesRule,
            )
            word = self.search_for_connected_sentences(
                word,
                cr.NO_SPACE_BETWEEN_SENTENCES_DIGIT_REGEX,
                cr.NoSpaceBetweenSentencesDigitRule,
            )
            words[idx] = word
        self.text = " ".join(words)

    def clean_consecutive_characters(self):
        self.text = apply_rules(
            self.text,
            cr.ConsecutivePeriodsRule,
            cr.ConsecutiveForwardSlashRule,
        )
