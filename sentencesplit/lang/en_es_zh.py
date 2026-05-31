# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.between_punctuation import BetweenPunctuation
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.common.cjk import (
    _QUOTE_CLOSER_RE,
    CJK_REPORTING_CLAUSE_RE,
    CJKBetweenPunctuationMixin,
    CJKBoundaryProfile,
    make_cjk_abbreviation_rules,
)
from sentencesplit.lang.english import English
from sentencesplit.lang.spanish import Spanish
from sentencesplit.processor import (
    _CJK_BANG_RESPLIT_RE,
    _CJK_QUOTE_RESPLIT_RE,
    _ELLIPSIS_RE,
    _LATIN_RESPLIT_RE,
    _ORPHAN_SINGLE_CHARS,
    Processor,
    _split_on_uppercase_boundary,
)

_CJK_FOLLOWING_CHAR_RE = re.compile(r"[\u3400-\u9FFF]")
# The uppercase sentence-start heuristic applies to BOTH the English and Spanish
# abbreviation sets. Gating it to English-only previously made common words that
# are also Spanish abbreviations (doc, dir, dom, \u2026) under-split versus both the
# standalone "en" and "es" profiles.
_HEURISTIC_ABBREVIATIONS = frozenset(
    a.lower() for a in (Standard.Abbreviation.ABBREVIATIONS + Spanish.Abbreviation.ABBREVIATIONS)
)
# Closers that mark an embedded CJK quote/title; a lowercase Latin continuation
# after one of these is not a quote continuation (unlike a Latin quote closer).
_CJK_QUOTE_CLOSERS = frozenset("\u300d\u300f\u300b\u3011")


class EnglishSpanishChinese(CJKBoundaryProfile, Common, Standard):
    iso_code = "en_es_zh"

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = sorted(set(Standard.Abbreviation.ABBREVIATIONS + Spanish.Abbreviation.ABBREVIATIONS))
        PREPOSITIVE_ABBREVIATIONS = sorted(
            set(Standard.Abbreviation.PREPOSITIVE_ABBREVIATIONS + Spanish.Abbreviation.PREPOSITIVE_ABBREVIATIONS)
        )
        NUMBER_ABBREVIATIONS = sorted(
            set(Standard.Abbreviation.NUMBER_ABBREVIATIONS + Spanish.Abbreviation.NUMBER_ABBREVIATIONS)
        )

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = English.AbbreviationReplacer.SENTENCE_STARTERS

        def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
            txt = " " + txt
            if escaped is None:
                escaped = re.escape(abbr.strip())
            txt = re.sub(
                rf"(?<=\s{escaped})\.(?=(?:[.:\-?,]|\s(?:[^\W\d_]|I\s|I'm|I'll|\d|\()|[\u3400-\u9FFF]))",
                "∯",
                txt,
            )
            return txt[1:]

        def scan_for_replacements(
            self, txt: str, am: str, ind: int, char_array, stripped: str = "", escaped: str | None = None
        ) -> str:
            try:
                char = char_array[ind]
            except IndexError:
                char = ""
            am_lower = am.strip().lower()
            ascii_upper = bool(char) and char.isascii() and char.isupper()
            use_uppercase_heuristic = ascii_upper and am_lower in _HEURISTIC_ABBREVIATIONS
            if not use_uppercase_heuristic or am_lower in self._data.prepositive_set:
                am_escaped = re.escape(am.strip())
                txt = " " + txt
                if am_lower in self._data.prepositive_set:
                    should_protect_prepositive = not (
                        self._leans_split and am_lower in self.AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST
                    )
                    if should_protect_prepositive:
                        txt = re.sub(rf"(?<=\s{am_escaped})\.(?=(?:\s|:\d+|[\u3400-\u9FFF]))", "∯", txt)
                elif am_lower in self._data.number_abbr_set:
                    if self._leans_join:
                        # conservative: also protect before any capitalized
                        # follower ("Fig. Several"), matching the base dial.
                        txt = re.sub(rf"(?<=\s{am_escaped})\.(?=(?:\s\d|\s+\(|\s[^\W\d_]|[\u3400-\u9FFF]))", "∯", txt)
                    else:
                        txt = re.sub(rf"(?<=\s{am_escaped})\.(?=(?:\s\d|\s+\(|\s[IVXLCDM]+\b|[\u3400-\u9FFF]))", "∯", txt)
                else:
                    txt = self.replace_period_of_abbr(txt[1:], am, am_escaped)
                    return txt
                txt = txt[1:]
                # Multi-char number abbreviations (eq, pt, fig, vol, …) also
                # need regular abbreviation protection before lowercase text.
                # Guard with isupper() so uppercase starters (including non-ASCII
                # Latin like É) still trigger sentence boundaries.
                if am_lower in self._data.number_abbr_set and len(am.strip()) > 1 and not (char and char.isupper()):
                    txt = self.replace_period_of_abbr(txt, am.strip(), am_escaped)
            elif am_lower in self._data.number_abbr_set:
                # Next word starts ASCII uppercase — protect only before Roman numerals.
                # Exclude lone "I" to avoid false joins with the pronoun "I".
                am_escaped = re.escape(am.strip())
                txt = " " + txt
                if self._leans_join:
                    # conservative: protect before any capitalized follower.
                    txt = re.sub(rf"(?<=\s{am_escaped})\.(?=\s[^\W\d_])", "∯", txt)
                else:
                    txt = re.sub(rf"(?<=\s{am_escaped})\.(?=\s(?:[IVXLCDM]{{2,}}|[VXLCDM])\b)", "∯", txt)
                txt = txt[1:]
            return txt

    class CjkAbbreviationRules:
        All = make_cjk_abbreviation_rules(r"\u3400-\u9FFF")

    class BetweenPunctuation(CJKBetweenPunctuationMixin, BetweenPunctuation):
        def replace(self) -> str:
            txt = super().replace()
            return self.apply_cjk_punctuation(txt)

    class Processor(Processor):
        def _resplit_segments(self, postprocessed_sents: list[str]) -> list[str]:
            resplit = []
            for pps in postprocessed_sents:
                latin_parts = _split_on_uppercase_boundary(pps, _LATIN_RESPLIT_RE)
                for latin_part in latin_parts or [pps]:
                    if not latin_part:
                        continue
                    for part in _CJK_QUOTE_RESPLIT_RE.split(latin_part):
                        resplit.extend(p for p in _CJK_BANG_RESPLIT_RE.split(part) if p)
            return self._merge_quote_continuations(resplit or postprocessed_sents)

        def _merge_quote_continuations(self, sentences: list[str]) -> list[str]:
            merged: list[str] = []
            idx = 0
            while idx < len(sentences):
                current = sentences[idx]
                if merged and self._should_merge_quote_continuation(merged[-1], current):
                    separator = "" if _CJK_FOLLOWING_CHAR_RE.match(current.lstrip()) else " "
                    merged[-1] = merged[-1] + separator + current.lstrip()
                else:
                    merged.append(current)
                idx += 1
            return merged

        def _should_merge_quote_continuation(self, previous: str, current: str) -> bool:
            previous = previous.rstrip()
            current = current.lstrip()
            if not previous or not current:
                return False
            closer = _QUOTE_CLOSER_RE.search(previous)
            if not closer:
                return False
            # A lowercase Latin continuation is only a quote continuation after a
            # Latin quote closer ("…" then he said). After a CJK closer (」』》】)
            # a lowercase word is a separate sentence (matching standalone zh);
            # only the CJK reporting clause re-merges those.
            is_cjk_closer = any(c in _CJK_QUOTE_CLOSERS for c in closer.group())
            if current[0].islower() and not is_cjk_closer:
                return True
            if CJK_REPORTING_CLAUSE_RE.match(current):
                return True
            return False

        def _merge_orphan_fragments(self, sentences: list[str]) -> list[str]:
            merged = []
            for sent in sentences:
                stripped = sent.strip()
                is_orphan = False
                if stripped and merged:
                    if _ELLIPSIS_RE.match(stripped):
                        is_orphan = True
                    elif len(stripped) == 1 and stripped in _ORPHAN_SINGLE_CHARS:
                        is_orphan = True
                    elif (
                        len(stripped) <= 10
                        and stripped.endswith(".")
                        and not stripped[0].isupper()
                        and stripped[0] not in ")]}"
                        and " " not in stripped[:-1]
                        and any(c.isalnum() or _CJK_FOLLOWING_CHAR_RE.match(c) for c in stripped)
                    ):
                        is_orphan = True
                if is_orphan:
                    if len(stripped) == 1 and stripped in _ORPHAN_SINGLE_CHARS:
                        merged[-1] = merged[-1] + sent
                    else:
                        merged[-1] = merged[-1] + " " + sent
                else:
                    merged.append(sent)
            return merged
