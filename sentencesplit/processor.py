# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from itertools import product

from sentencesplit.exclamation_words import ExclamationWords
from sentencesplit.language_profile import LanguageProfile
from sentencesplit.utils import (
    ZERO_WIDTH_CHARS,
    SplitMode,
    _next_nonspace_char_starts_sentence,
    apply_rules,
    split_mode_rank,
)

# Pre-compiled patterns used on the hot path
_ALPHA_ONLY_RE = re.compile(r"\A[a-zA-Z]*\Z")
_ELLIPSIS_RE = re.compile(r"\A\.{3,}\Z")
_TRAILING_EXCL_RE = re.compile(r"&ᓴ&$")
_PAREN_SPACE_BEFORE_RE = re.compile(r"\s(?=\()")
_PAREN_SPACE_AFTER_RE = re.compile(r"(?<=\))\s")
_ORPHAN_SINGLE_CHARS = frozenset("'\")\u2019\u201d")
# Shared with segmenter.py via utils so the two stay in sync. A lone zero-width
# char (e.g. a Wikipedia U+200B reference marker) survives str.strip() and would
# otherwise become a phantom empty sentence or fold into the next sentence.
_ZERO_WIDTH_CHARS = ZERO_WIDTH_CHARS
_CJK_QUOTE_RESPLIT_RE = re.compile(
    r"(?<=[。．][\]\"')”’」』】）》])(?=[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ffA-Za-z0-9「『【（《])"
)
# Fullwidth exclamation/question terminals inside a CJK quote or paren also end a
# sentence when a new clause follows (e.g. 「快跑！」大家都散开了。). Like the period rule,
# only the fullwidth marks ！？ are matched (not ASCII !/?), so a Latin exclamation
# in CJK-profile text — "(Help!)was great." — is not over-split. Title marks 《》【】
# hold non-terminal punctuation (book titles), and a closer immediately followed by
# the Japanese quotative と (or っ for って) marks an embedded reported quote
# (彼は「来るの？」と聞いた。) — neither is a sentence boundary.
_CJK_BANG_RESPLIT_RE = re.compile(
    r"(?<=[！？][\]\"')”’」』）])(?![とっ])(?=[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ffA-Za-z0-9「『【（《])"
)
_LATIN_RESPLIT_RE = re.compile(r"(?<=[a-zA-Z]{2}\.\))\s+")
# A run of 2+ '!'/'?' (restored from the continuous-punctuation placeholders) that
# ends a sentence: the boundary check itself is delegated to
# _next_nonspace_char_starts_sentence so accented Latin capitals (Ä/Ö/Ü, É, …) count.
# The cluster is left intact; only the whitespace after it becomes a split point.
_MULTI_TERMINATOR_RESPLIT_RE = re.compile(r"(?<=[!?]{2})\s+")
# A period immediately followed (after optional spaces) by a *single* comma can
# never be a sentence boundary, since no sentence starts with a comma. This
# protects the final period of unlisted multi-period abbreviations such as the
# botanical author tag "N.E.Br.," from being treated as terminal. The negative
# lookahead excludes a doubled comma (",,"), which in Dutch typography is an
# *opening* quotation mark beginning a new sentence (e.g. "...einde. ,,Nieuwe...").
_PERIOD_BEFORE_COMMA_RE = re.compile(r"\.(?=\s*,(?!,))")

# The between-punctuation pass protects everything from an opening quote to its
# closing quote as one unsplittable region, so a quotation that wraps several
# complete sentences collapses into a single segment when the closing quote is
# far away. _resplit_multi_sentence_quote re-splits such a segment, but only for
# a self-contained, un-nested quotation: a single matched quote pair (one opener
# near the start, the matching closer at the end) whose interior contains NO
# other quote characters at all. That excludes dialogue with embedded attribution
# or nested quotes (e.g. '"X," said Alice; "Y. Z. W."' or '"...\'William...\'"'),
# which the existing gold keeps whole, while still catching a clean run such as
# '“A. B. C.”' (case_0080).
_QUOTE_PAIRS = (("“", "”"), ('"', '"'), ("«", "»"))
_QUOTE_PAIR_BY_OPENER = {opener: closer for opener, closer in _QUOTE_PAIRS}
_LEADING_QUOTE_RE = re.compile(r"\A[\s_]*([“\"«])")
# Any quotation character — used to reject quotes with nested quotes/attribution.
_ANY_QUOTE_CHARS = frozenset("“”\"«»‘’'")
# Interior boundary inside a restored (already de-protected) quoted segment: a
# single PERIOD, optional whitespace, then an uppercase-letter sentence start.
# Only periods count — runs of '!'/'?' inside a quote are usually one emphatic
# speech act ("Oh dear! Oh dear!" / "As if I would! ... again!"), not separate
# sentences. The follower may be an uppercase letter of any cased script — ASCII,
# accented Latin (É, Ñ, …), Greek (Η), or Cyrillic (П) — so multi-sentence
# quotations split the same way across languages. The regex matches before any
# letter and _resplit_multi_sentence_quote filters with str.isupper(), which is
# False for caseless scripts (e.g. CJK ideographs), so those never split here.
_QUOTE_INTERIOR_BOUNDARY_RE = re.compile(r"(?<=[.])\s+(?=[^\W\d_])")
# A multi-sentence quotation must contain at least this many interior pieces
# (i.e. at least two interior boundaries / three sentences) before the resplit
# fires, and every piece must be at least _QUOTE_MIN_WORDS words long. Requiring
# three keeps single-boundary quotes intact, where it is genuinely ambiguous
# whether the second clause is a new sentence or a continuation of the same
# speech act (e.g. the gold-kept "...at tea-time. Dinah, my dear, I wish...").
_QUOTE_MIN_INTERIOR_SENTENCES = 3
_QUOTE_MIN_WORDS = 5


def _resplit_multi_sentence_quote(
    text: str,
    min_interior_sentences: int = _QUOTE_MIN_INTERIOR_SENTENCES,
    min_words: int = _QUOTE_MIN_WORDS,
) -> list[str] | None:
    """Re-split a self-contained quotation at its interior period boundaries.

    *min_interior_sentences* / *min_words* are the split-bias thresholds (lower =
    more eager to split). Returns the split pieces, or ``None`` when *text*
    should be left intact.
    """
    match = _LEADING_QUOTE_RE.match(text)
    if match is None:
        return None
    closer = _QUOTE_PAIR_BY_OPENER[match.group(1)]
    body = text.rstrip()
    if not body.endswith(closer):
        return None
    # The interior must be a single, un-nested quotation: no embedded quote
    # characters (attribution, nested quotes) that signal the multi-sentence run
    # is not one clean quoted utterance.
    inner = body[match.end() : -1]
    if any(char in _ANY_QUOTE_CHARS for char in inner):
        return None

    spans = []
    last = 0
    for boundary in _QUOTE_INTERIOR_BOUNDARY_RE.finditer(text):
        # The lookahead is zero-width, so boundary.end() is the candidate start
        # letter itself. Split only before an uppercase letter (any cased script);
        # skip a lowercase or caseless follower so the boundary count stays exact.
        if not text[boundary.end() : boundary.end() + 1].isupper():
            continue
        spans.append(text[last : boundary.start()])
        last = boundary.end()
    if len(spans) + 1 < min_interior_sentences:
        return None
    spans.append(text[last:])

    if any(len(span.split()) < min_words for span in spans):
        # Short interior pieces are dialogue beats, not standalone sentences —
        # keep the quotation whole.
        return None

    return spans


# Internal placeholder ("sentinel") characters the pipeline uses to protect
# punctuation from splitting. They are ordinary printable codepoints, so if a
# user's input already contains one, naive processing would rewrite it on output
# (corrupting clean=True text) and break span mapping (silently dropping text in
# the default clean=False mode). To stay non-destructive, any pre-existing
# single-char sentinel in the input is escaped to a placeholder codepoint before
# processing and restored verbatim afterwards. Multi-char "&X&" sentinels are
# intentionally excluded: they are also produced by the Cleaner (e.g. "&ᓷ&" for a
# bracketed "?") and are not realistically present in source text.
_RESERVED_SENTINELS = "∯♬♭☉☇☈☄☊☋☌☍ȸȹƪ♟♝☏∮♨☝"
_RESERVED_SENTINEL_SET = frozenset(_RESERVED_SENTINELS)
# Private-use codepoints (BMP + both supplementary planes) used as escape
# targets. Targets are chosen per call from this pool to be absent from the
# input. If adversarial input occupies every single private-use character, the
# escape target grows into a delimited private-use string token. The delimiter
# is a noncharacter token chosen absent from the input, which keeps restore
# matches aligned to whole escape tokens instead of arbitrary private-use
# substrings.
_PRIVATE_USE_RANGES = ((0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD))
_NONCHARACTER_DELIMITER_RANGES = ((0xFDD0, 0xFDEF),) + tuple(
    (plane + 0xFFFE, plane + 0xFFFF) for plane in range(0, 0x110000, 0x10000)
)


def _iter_private_use_chars():
    for lo, hi in _PRIVATE_USE_RANGES:
        for cp in range(lo, hi + 1):
            yield chr(cp)


def _iter_delimited_private_use_tokens(body_len: int, delimiter: str):
    alphabet = tuple(_iter_private_use_chars())
    if not alphabet:
        return
    for chars in product(alphabet, repeat=body_len):
        yield delimiter + "".join(chars) + delimiter


def _iter_noncharacter_delimiters():
    for lo, hi in _NONCHARACTER_DELIMITER_RANGES:
        for cp in range(lo, hi + 1):
            yield chr(cp)


def _iter_noncharacter_delimiter_tokens():
    alphabet = tuple(_iter_noncharacter_delimiters())
    width = 1
    while alphabet:
        for chars in product(alphabet, repeat=width):
            yield "".join(chars)
        width += 1


def _absent_noncharacter_delimiter(text: str) -> str:
    for delimiter in _iter_noncharacter_delimiter_tokens():
        if delimiter not in text:
            return delimiter
    raise ValueError("At least one noncharacter delimiter token is required")


def _build_sentinel_escape_tables(
    text: str,
) -> tuple[dict[int, str], dict[str, str], re.Pattern[str]]:
    """Return escape/restore tables for reserved sentinels in *text*.

    The escape values are private-use tokens that do not occur in the input.
    Single private-use characters are used for normal inputs; if an adversarial
    input exhausts the single-character pool, longer private-use token bodies
    are wrapped in an absent delimiter. The delimiter prevents restore matches
    from starting inside neighboring original private-use text.

    Returns ``(escape, restore, restore_re)`` where ``escape`` maps codepoints to
    tokens for ``str.translate``, ``restore`` maps each token back to its
    sentinel, and ``restore_re`` is a compiled alternation that restores every
    token in a single left-to-right pass. The atomic restore is required for
    correctness: multi-character tokens are not prefix-free, so a sequential
    per-token ``str.replace`` could match a window straddling two adjacent
    escaped sentinels and corrupt the round-trip.
    """
    tokens = []
    occupied = set(text)
    for token in _iter_private_use_chars():
        if token not in occupied:
            tokens.append(token)
            if len(tokens) == len(_RESERVED_SENTINELS):
                break
    if len(tokens) < len(_RESERVED_SENTINELS):
        delimiter = _absent_noncharacter_delimiter(text)
        body_len = 1
        while len(tokens) < len(_RESERVED_SENTINELS):
            saw_candidate = False
            for token in _iter_delimited_private_use_tokens(body_len, delimiter):
                saw_candidate = True
                tokens.append(token)
                if len(tokens) == len(_RESERVED_SENTINELS):
                    break
            if not saw_candidate:
                raise ValueError("At least one private-use escape codepoint is required")
            body_len += 1
    escape = {ord(ch): token for ch, token in zip(_RESERVED_SENTINELS, tokens, strict=True)}
    restore = {token: ch for ch, token in zip(_RESERVED_SENTINELS, tokens, strict=True)}
    restore_re = re.compile("|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True)))
    return escape, restore, restore_re


def _split_on_uppercase_boundary(text: str, whitespace_re: re.Pattern[str]) -> list[str] | None:
    parts = []
    last = 0
    for match in whitespace_re.finditer(text):
        if not _next_nonspace_char_starts_sentence(text, match.end()):
            continue
        parts.append(text[last : match.start()])
        last = match.end()
    if not parts:
        return None
    parts.append(text[last:])
    return [part for part in parts if part]


def _sub_symbols_fast(text: str, lang) -> str:
    """Replace temporary symbols using str.replace() instead of regex."""
    for old, new in lang.SubSymbolsRules.SUBS_TABLE:
        text = text.replace(old, new)
    return text


class Processor:
    def __init__(self, text: str | None, lang, split_mode: SplitMode = "balanced") -> None:
        self.text = text
        self.lang = lang
        self.split_mode = split_mode
        self.profile = LanguageProfile.from_language(lang)

    def process(self) -> list[str]:
        if not self.text:
            return []
        restore = None
        restore_re = None
        text = self.text
        if not _RESERVED_SENTINEL_SET.isdisjoint(text):
            escape, restore, restore_re = _build_sentinel_escape_tables(text)
            text = text.translate(escape)
        for phase in self._text_processing_phases():
            text = phase(text)
        segments = self.split_into_segments(text)
        if restore is not None:
            # Restore atomically (single left-to-right pass) so it is the true
            # inverse of the atomic ``str.translate`` escape. A sequential
            # per-token ``str.replace`` is not overlap-safe: multi-char escape
            # tokens are not prefix-free, so an earlier token's replace could
            # consume a window straddling two adjacent escaped sentinels.
            segments = [restore_re.sub(lambda m: restore[m.group(0)], seg) for seg in segments]
        return segments

    def _text_processing_phases(self):
        phases = [
            self._normalize_newlines,
            self._mark_list_item_boundaries,
            self.replace_abbreviations,
        ]
        if self.profile.cjk_abbreviation_rules:
            phases.append(self._apply_cjk_abbreviation_rules)
        phases.extend(
            [
                self.replace_numbers,
                self.replace_continuous_punctuation,
                self.replace_periods_before_numeric_references,
                self._protect_special_tokens,
            ]
        )
        return tuple(phases)

    def _boundary_processing_phases(self):
        return (
            self._ensure_terminal_marker,
            self._apply_exclamation_word_rules,
            self.between_punctuation,
            self._apply_double_punctuation_rules,
            self._apply_quotation_punctuation_rules,
            self._replace_list_parens,
        )

    def _normalize_newlines(self, text: str) -> str:
        return text.replace("\n", "\r")

    def _mark_list_item_boundaries(self, text: str) -> str:
        return self.profile.list_item_replacer_cls(text, self.split_mode).add_line_break()

    def _apply_cjk_abbreviation_rules(self, text: str) -> str:
        return apply_rules(text, *self.profile.cjk_abbreviation_rules)

    def _protect_special_tokens(self, text: str) -> str:
        return apply_rules(
            text,
            self.lang.Abbreviation.WithMultiplePeriodsAndEmailRule,
            self.lang.GeoLocationRule,
            self.lang.FileFormatRule,
            self.lang.DotNetRule,
        )

    def rm_none_flatten(self, sents: list[str | list[str] | None]) -> list[str]:
        new_sents = []
        for s in sents:
            if not s:
                continue
            if isinstance(s, list):
                new_sents.extend(s)
            else:
                new_sents.append(s)
        return new_sents

    def split_into_segments(self, text: str | None = None) -> list[str]:
        working_text = text if text is not None else self.text
        if not working_text:
            return []

        working_text = self.check_for_parens_between_quotes(working_text)
        sents = working_text.split("\r")
        # remove empty and none values
        sents = self.rm_none_flatten(sents)
        sents = [self._apply_single_newline_and_ellipsis_rules(s) for s in sents]
        sents = [self.check_for_punctuation(s) for s in sents]
        # flatten list of list of sentences
        sents = self.rm_none_flatten(sents)
        postprocessed_sents = self._restore_and_postprocess_segments(sents)
        postprocessed_sents = [apply_rules(ns, self.lang.SubSingleQuoteRule) for ns in postprocessed_sents]
        postprocessed_sents = self._resplit_segments(postprocessed_sents)
        postprocessed_sents = self._merge_orphan_fragments(postprocessed_sents)
        return self._strip_zero_width_chars(postprocessed_sents)

    def _strip_zero_width_chars(self, postprocessed_sents: list[str]) -> list[str]:
        # str.strip() does not remove zero-width / format characters, so a lone
        # U+200B (e.g. a Wikipedia reference marker) survives as a phantom empty
        # sentence and a leading one is folded into the next sentence. Strip them
        # from the segment edges and drop segments that become empty.
        cleaned = []
        for sent in postprocessed_sents:
            stripped = sent.strip(_ZERO_WIDTH_CHARS).strip()
            if stripped:
                cleaned.append(stripped)
        return cleaned

    def _apply_single_newline_and_ellipsis_rules(self, text: str) -> str:
        ellipsis_rules = self.lang.EllipsisRules.All
        if split_mode_rank(self.split_mode) <= 0:
            # conservative: drop ThreeConsecutiveRule so "..." before a capital
            # ("Wait... She left.") is treated as a trailing-thought ellipsis
            # (joined) rather than a sentence boundary. The remaining rules then
            # protect all three dots via OtherThreePeriodRule.
            ellipsis_rules = [r for r in ellipsis_rules if r is not self.lang.EllipsisRules.ThreeConsecutiveRule]
        return apply_rules(text, self.lang.SingleNewLineRule, *ellipsis_rules)

    def _restore_and_postprocess_segments(self, sentences: list[str]) -> list[str]:
        postprocessed_sents = []
        for sent in sentences:
            restored = _sub_symbols_fast(sent, self.lang)
            for pps in self.post_process_segments(restored):
                if pps:
                    postprocessed_sents.append(pps)
        return postprocessed_sents

    def _quote_resplit_thresholds(self) -> tuple[int, int] | None:
        """(min_interior_sentences, min_words) for quotation resplit, or None to disable.

        conservative never resplits a quotation; balanced uses the historically
        tuned 3-sentence / 5-word thresholds; aggressive lowers them so even a
        two-sentence quotation splits.
        """
        rank = split_mode_rank(self.split_mode)
        if rank <= 0:  # conservative
            return None
        if rank >= 2:  # aggressive
            return (2, 3)
        return (_QUOTE_MIN_INTERIOR_SENTENCES, _QUOTE_MIN_WORDS)

    def _resplit_segments(self, postprocessed_sents: list[str]) -> list[str]:
        if self.profile.latin_uppercase_resplit:
            # Re-split at ".) Capital" boundaries (period inside closing paren before new sentence)
            # and at multi-character terminators ("Top!!! Der") whose cluster the
            # continuous-punctuation protection prevented from splitting earlier.
            quote_thresholds = self._quote_resplit_thresholds()
            resplit = []
            for pps in postprocessed_sents:
                parts = (
                    _split_on_uppercase_boundary(pps, _LATIN_RESPLIT_RE)
                    or _split_on_uppercase_boundary(pps, _MULTI_TERMINATOR_RESPLIT_RE)
                    or (quote_thresholds is not None and _resplit_multi_sentence_quote(pps, *quote_thresholds))
                    or None
                )
                if parts is None:
                    resplit.append(pps)
                else:
                    resplit.extend(parts)
            return resplit

        # CJK: Re-split at closing-quote boundaries (period terminals, then the
        # narrower exclamation/question case).
        resplit = []
        for pps in postprocessed_sents:
            for part in _CJK_QUOTE_RESPLIT_RE.split(pps):
                resplit.extend(p for p in _CJK_BANG_RESPLIT_RE.split(part) if p)
        return resplit

    def _merge_orphan_fragments(self, postprocessed_sents: list[str]) -> list[str]:
        # Merge orphan fragments into the preceding sentence.
        # An orphan is either an ellipsis (3+ periods) or a very short
        # lowercase abbreviation fragment ending with a period (e.g. "pp.").
        merged = []
        for sent in postprocessed_sents:
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
                    # Only a single short token (e.g. "pp.", "cf.") is an orphan
                    # abbreviation fragment. A fragment with internal whitespace
                    # ("3 are red.", "go away.") or one starting with a closing
                    # bracket (")", "]") is a real sentence, not an orphan.
                    and stripped[0] not in ")]}"
                    and " " not in stripped[:-1]
                    and any(c.isalnum() for c in stripped)
                ):
                    is_orphan = True
            if is_orphan:
                # Keep punctuation or quote closers attached to the previous
                # sentence without introducing an artificial space. Adding a
                # space here can make the processed sentence impossible to map
                # back to the original text span (e.g. `away.)` -> `away. )`).
                if len(stripped) == 1 and stripped in _ORPHAN_SINGLE_CHARS:
                    merged[-1] = merged[-1] + sent
                else:
                    merged[-1] = merged[-1] + " " + sent
            else:
                merged.append(sent)
        return merged

    def post_process_segments(self, txt: str) -> list[str]:
        if len(txt) > 2 and _ALPHA_ONLY_RE.search(txt):
            return [txt]

        txt = apply_rules(txt, *self.lang.ReinsertEllipsisRules.All)
        if self.profile.latin_uppercase_resplit:
            quoted_parts = _split_on_uppercase_boundary(txt, self.profile.split_quotation_re)
            if quoted_parts is not None:
                return quoted_parts
        else:
            if self.profile.quotation_end_re.search(txt):
                parts = self.profile.split_quotation_re.split(txt)
                return [t for t in parts if t]

        txt = txt.replace("\n", "")
        txt = txt.strip()
        return [txt] if txt else []

    def check_for_parens_between_quotes(self, text: str) -> str:
        def paren_replace(match):
            match = match.group()
            sub1 = _PAREN_SPACE_BEFORE_RE.sub("\r", match)
            sub2 = _PAREN_SPACE_AFTER_RE.sub("\r", sub1)
            return sub2

        return self.profile.parens_dq_re.sub(paren_replace, text)

    def replace_continuous_punctuation(self, text: str) -> str:
        def continuous_puncs_replace(match):
            match = match.group()
            match = match.replace("!", "&ᓴ&")
            match = match.replace("?", "&ᓷ&")
            return match

        return self.profile.continuous_punct_re.sub(continuous_puncs_replace, text)

    def replace_periods_before_numeric_references(self, text: str) -> str:
        """Protect the period in numeric/bracket citations and insert a sentence boundary after them.

        For matches like "see [12]. Next" or "page 1.2 3 next.", rewrites the
        period to a protected placeholder (∯) and inserts a boundary marker (\\r)
        immediately after the numeric reference, so the citation does not trigger
        a mid-sentence split but the next sentence is still recognized.

        \\2 is the numeric reference itself; \\7 is the trailing whitespace.
        Group structure is defined in lang/common/common.py NUMBERED_REFERENCE_REGEX.
        """
        # https://github.com/diasks2/pragmatic_segmenter/commit/d9ec1a352aff92b91e2e572c30bb9561eb42c703
        return self.profile.numbered_ref_re.sub(r"∯\2\r\7", text)

    def check_for_punctuation(self, txt: str) -> list[str]:
        if any(p in txt for p in self.lang.Punctuations):
            sents = self.process_text(txt)
            return sents
        else:
            # NOTE: next steps of check_for_punctuation will unpack this list
            return [txt]

    def process_text(self, txt: str) -> list[str]:
        for phase in self._boundary_processing_phases():
            txt = phase(txt)
        return self.sentence_boundary_punctuation(txt)

    def _ensure_terminal_marker(self, text: str) -> str:
        if text[-1] not in self.lang.Punctuations:
            return text + "ȸ"
        return text

    def _apply_exclamation_word_rules(self, text: str) -> str:
        return ExclamationWords.apply_rules(text)

    def _apply_double_punctuation_rules(self, text: str) -> str:
        # handle text having only doublepunctuations
        if not self.profile.double_punct_re.match(text):
            return apply_rules(text, *self.lang.DoublePunctuationRules.All)
        return text

    def _apply_quotation_punctuation_rules(self, text: str) -> str:
        exclamation_rules = self.lang.ExclamationPointRules.All
        if split_mode_rank(self.split_mode) >= 2:
            # aggressive: stop protecting "!" before a lowercase continuation
            # ("Wow! amazing.") so it ends the sentence. InQuotationRule is
            # structural ("!" before a closing quote) and kept in every mode.
            rules = self.lang.ExclamationPointRules
            drop = {id(rules.MidSentenceRule), id(rules.BeforeCommaMidSentenceRule)}
            exclamation_rules = [r for r in exclamation_rules if id(r) not in drop]
        return apply_rules(text, self.lang.QuestionMarkInQuotationRule, *exclamation_rules)

    def _replace_list_parens(self, text: str) -> str:
        return self.profile.list_item_replacer_cls(text, self.split_mode).replace_parens()

    def replace_numbers(self, text: str) -> str:
        return apply_rules(text, *self.lang.Numbers.All)

    def abbreviations_replacer(self, text: str):
        return self.profile.abbreviation_replacer_cls(text, self.lang, split_mode=self.split_mode)

    def replace_abbreviations(self, text: str) -> str:
        return self.abbreviations_replacer(text).replace()

    def between_punctuation_processor(self, txt: str):
        return self.profile.between_punctuation_cls(txt)

    def between_punctuation(self, txt: str) -> str:
        txt = self.between_punctuation_processor(txt).replace()
        return txt

    def sentence_boundary_punctuation(self, txt: str) -> list[str]:
        # A period followed by a comma is never a sentence boundary.
        txt = _PERIOD_BEFORE_COMMA_RE.sub("∯", txt)
        if self.profile.colon_rule is not None:
            txt = apply_rules(txt, self.profile.colon_rule)
        if self.profile.comma_rule is not None:
            txt = apply_rules(txt, self.profile.comma_rule)
        # retain exclamation mark if it is an ending character of a given text
        txt = _TRAILING_EXCL_RE.sub("!", txt)
        txt = [m.group() for m in self.profile.sentence_boundary_re.finditer(txt)]
        return txt
