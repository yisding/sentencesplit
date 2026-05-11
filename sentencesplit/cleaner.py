# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.utils import Rule, apply_rules


class CleanRules:
    # NOTE: Caution: Might require \\ for special characters
    # if regex is defined with r'' then dont
    # add extra \\ for special characters
    # Rubular: http://rubular.com/r/V57WnM9Zut
    NewLineInMiddleOfWordRule = Rule(r"\n(?=[a-zA-Z]{1,2}\n)", "")

    # Rubular: http://rubular.com/r/dMxp5MixFS
    DoubleNewLineWithSpaceRule = Rule(r"\n \n", "\r")

    # Rubular: http://rubular.com/r/H6HOJeA8bq
    DoubleNewLineRule = Rule(r"\n\n", "\r")

    # Rubular: http://rubular.com/r/FseyMiiYFT
    NewLineFollowedByPeriodRule = Rule(r"\n(?=\.(\s|\n))", "")

    ReplaceNewlineWithCarriageReturnRule = Rule(r"\n", "\r")

    EscapedNewLineRule = Rule(r"\\n", "\n")

    EscapedCarriageReturnRule = Rule(r"\\r", "\r")

    TypoEscapedNewLineRule = Rule(r"\\\ n", "\n")

    TypoEscapedCarriageReturnRule = Rule(r"\\\ r", "\r")

    # Rubular: http://rubular.com/r/bAJrhyLNeZ
    InlineFormattingRule = Rule(r"{b\^&gt;\d*&lt;b\^}|{b\^>\d*<b\^}", "")

    # Rubular: http://rubular.com/r/8mc1ArOIGy
    TableOfContentsRule = Rule(r"\.{4,}\s*\d+-*\d*", "\r")

    # Rubular: http://rubular.com/r/DwNSuZrNtk
    ConsecutivePeriodsRule = Rule(r"\.{5,}", " ")

    # Rubular: http://rubular.com/r/IQ4TPfsbd8
    ConsecutiveForwardSlashRule = Rule(r"\/{3}", "")

    # Rubular: http://rubular.com/r/6dt98uI76u
    _NO_SPACE_BETWEEN_SENTENCES_PATTERN = r"(?<=[a-z])\.(?=[A-Z])"
    NO_SPACE_BETWEEN_SENTENCES_REGEX = re.compile(_NO_SPACE_BETWEEN_SENTENCES_PATTERN)
    NoSpaceBetweenSentencesRule = Rule(_NO_SPACE_BETWEEN_SENTENCES_PATTERN, ". ")

    # Rubular: http://rubular.com/r/l6KN6rH5XE
    _NO_SPACE_BETWEEN_SENTENCES_DIGIT_PATTERN = r"(?<=\d)\.(?=[A-Z])"
    NO_SPACE_BETWEEN_SENTENCES_DIGIT_REGEX = re.compile(_NO_SPACE_BETWEEN_SENTENCES_DIGIT_PATTERN)
    NoSpaceBetweenSentencesDigitRule = Rule(_NO_SPACE_BETWEEN_SENTENCES_DIGIT_PATTERN, ". ")

    URL_EMAIL_KEYWORDS = ["@", "http", ".com", "net", "www", "//"]

    # Rubular: http://rubular.com/r/3GiRiP2IbD
    NEWLINE_IN_MIDDLE_OF_SENTENCE_REGEX = re.compile(r"(?<=\s)\n(?=([a-z]|\())")

    # Rubular: http://rubular.com/r/Gn18aAnLdZ
    NewLineFollowedByBulletRule = Rule(r"\n(?=•')", "\r")

    QuotationsFirstRule = Rule(r"''", '"')
    QuotationsSecondRule = Rule(r"``", '"')


cr = CleanRules


class HTML:
    # Rubular: http://rubular.com/r/9d0OVOEJWj
    HTMLTagRule = Rule(r"<\/?\w+((\s+\w+(\s*=\s*(?:\".*?\"|'.*?'|[\^'\">\s]+))?)+\s*|\s*)\/?>", "")

    # Rubular: http://rubular.com/r/XZVqMPJhea
    EscapedHTMLTagRule = Rule(r"&lt;\/?[^gt;]*gt;", "")

    All = [HTMLTagRule, EscapedHTMLTagRule]


class PDF:
    # Rubular: http://rubular.com/r/UZAVcwqck8
    NewLineInMiddleOfSentenceRule = Rule(r"(?<=[^\n]\s)\n(?=\S)", "")

    # Rubular: http://rubular.com/r/eaNwGavmdo
    NewLineInMiddleOfSentenceNoSpacesRule = Rule(r"\n(?=[a-z])", " ")


_NON_DOT_RE = re.compile(r"[^.]+")
_BRACKET_RE = re.compile(r"\[(?:[^\]])*\]")
_BACKTICK_RE = re.compile(r"`")


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
            sub = cr.NEWLINE_IN_MIDDLE_OF_SENTENCE_REGEX.sub("", match)
            return sub

        self.text = _NON_DOT_RE.sub(replace_w_blank, self.text)

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
                return match.replace("?", "&ᓷ&")
            return match

        self.text = _BRACKET_RE.sub(replace_punct, self.text)

    def clean_quotations(self):
        # method added explicitly
        # pragmatic-segmenter applies this method
        # at different location
        self.text = _BACKTICK_RE.sub("'", self.text)
        self.text = apply_rules(
            self.text,
            cr.QuotationsFirstRule,
            cr.QuotationsSecondRule,
        )

    def clean_table_of_contents(self):
        self.text = apply_rules(self.text, cr.TableOfContentsRule)

    def search_for_connected_sentences(self, word: str, regex: re.Pattern[str], rule: Rule) -> str:
        if not regex.search(word):
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
