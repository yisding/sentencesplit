# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.cleaner import Cleaner
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import CJKBoundaryProfile, CJKProcessor
from sentencesplit.punctuation_replacer import replace_punctuation
from sentencesplit.utils import Rule, apply_rules


class Japanese(CJKBoundaryProfile, Common, Standard):
    iso_code = "ja"
    CJK_REPORTING_CLAUSE_REGEX = re.compile(
        r"^(?:彼|彼女|私は|僕は|俺は|記者は|母は|父は).{0,6}(?:言った|話した|尋ねた|答えた|叫んだ|述べた|説明した)"
    )

    class Cleaner(Cleaner):
        def __init__(self, text, lang, doc_type=None):
            super().__init__(text, lang)

        def clean(self):
            self.remove_newline_in_middle_of_word()
            return self.text

        def remove_newline_in_middle_of_word(self):
            # Only join lines when the preceding character is a common Japanese
            # particle, which strongly indicates the sentence continues on the
            # next line (e.g. line-wrapped text).  Matching any Japanese character
            # would incorrectly merge headings/short paragraphs that lack
            # terminal punctuation (e.g. 第一章\n概要).
            continuation_particle = r"[のはがをにでともへ]"
            japanese_char = r"[\u3040-\u30FF\u3400-\u9FFF々〆〤]"
            list_like_line_start = r"(?:[・●○◦▪■□◆◇▼▽▶▷►▸※]|[-*]|[0-9０-９]+[.)、．]|[一二三四五六七八九十]+[、.)])"
            NewLineInMiddleOfWordRule = Rule(
                rf"(?<={continuation_particle})\n(?=(?!\s*{list_like_line_start}){japanese_char})",
                "",
            )
            self.text = apply_rules(self.text, NewLineInMiddleOfWordRule)

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

        def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
            txt = " " + txt
            if escaped is None:
                escaped = re.escape(abbr.strip())
            txt = re.sub(
                r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())|[\u3040-\u30ff\u4e00-\u9fff]))".format(
                    abbr=escaped
                ),
                "∯",
                txt,
            )
            return txt[1:]

    class CjkAbbreviationRules:
        IntraAbbreviationPeriodRule = Rule(r"(?<=[A-Za-z])\.(?=[A-Za-z]\.)", "∯")
        EndAbbreviationBeforeCjkRule = Rule(r"(?<=[A-Za-z]∯[A-Za-z])\.(?=[\u3040-\u30ff\u4e00-\u9fff])", "∯")

        All = [IntraAbbreviationPeriodRule, EndAbbreviationBeforeCjkRule]

    class Processor(CJKProcessor):
        pass

    class BetweenPunctuation(BetweenPunctuation):
        def __init__(self, text):
            super().__init__(text)

        def replace(self):
            self.text = super().sub_punctuation_between_quotes_and_parens(self.text)
            self.sub_punctuation_between_quotes_and_parens()
            return self.text

        def sub_punctuation_between_parens_ja(self):
            regex = r"（(?=(?P<tmp>[^（）]+|\\{2}|\\.)*)(?P=tmp)）"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_ja(self):
            regex = r"「(?=(?P<tmp>[^「」]+|\\{2}|\\.)*)(?P=tmp)」"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_corner_quotes_ja(self):
            regex = r"『(?=(?P<tmp>[^『』]+|\\{2}|\\.)*)(?P=tmp)』"
            self.text = re.sub(regex, replace_punctuation, self.text)

        def sub_punctuation_between_quotes_and_parens(self):
            self.sub_punctuation_between_parens_ja()
            self.sub_punctuation_between_quotes_ja()
            self.sub_punctuation_between_corner_quotes_ja()
