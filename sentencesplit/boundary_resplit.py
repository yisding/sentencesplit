# -*- coding: utf-8 -*-
"""Post-split boundary resplitting and quote-continuation merging.

The segmentation pipeline first protects whole quoted/parenthesized regions from
splitting (``between_punctuation``), then splits on terminal punctuation. That
leaves two classes of segment that need a second look *after* the main split:

* segments that should be split further — a period inside a closing paren before
  a new capitalized sentence (``.) Capital``), a multi-character terminator run
  (``Top!!! Der``) whose continuous-punctuation protection suppressed the split,
  a clean multi-sentence quotation collapsed into one region, or (for CJK) a
  closing quote immediately followed by a new clause; and
* segments that should be *merged* back together — a CJK quote closer followed by
  a reporting clause (``"…" 他说。``), which is one reported sentence.

This module owns the regexes and helpers for both directions so the Processor and
the CJK / combined-profile processors share one implementation instead of three.
"""

from __future__ import annotations

import re
from typing import Callable

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.utils import _next_nonspace_char_starts_sentence

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
_QUOTE_ABBREVIATION_SCAN_TRANS = str.maketrans({char: " " for char in "".join(_QUOTE_PAIR_BY_OPENER) + "([{"})
# Any quotation character — used to reject quotes with nested quotes/attribution.
# Intentionally quotes-only (no brackets): a narrower set than
# ``_normalize._TRAILING_SENTENCE_CLOSERS`` for this specific role, not a duplicate.
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


def _quote_abbreviation_scan_text(text: str) -> str:
    return text.translate(_QUOTE_ABBREVIATION_SCAN_TRANS)


# ``replace_abbreviations`` rewrites ``<number-abbr>∯ ??`` to
# ``<number-abbr>∯ <_UNKNOWN_PLACEHOLDER>`` (e.g. "No. ??" -> "No∯ &ᓷ&&ᓷ&").
# That expansion (3 input chars "\s??" -> 7 chars " " + placeholder) is the only
# operation that makes the abbreviation-protected scan a different length than
# the restored segment. _resplit_multi_sentence_quote only consults the protected
# scan to ask whether a candidate boundary period is an abbreviation sentinel
# ("∯"), so collapsing this single expansion back to its original literal " ??"
# restores exact length parity without disturbing any ∯ position.
_UNKNOWN_PLACEHOLDER_EXPANSION = " " + AbbreviationReplacer._UNKNOWN_PLACEHOLDER


def _length_align_protected_scan(protected_text: str | None, text: str) -> str | None:
    """Restore length parity between the protected scan and the restored segment.

    Returns *protected_text* with the (non-length-preserving) unknown-placeholder
    expansion collapsed back to its literal ``" ??"``. When the result is the same
    length as *text* it is positionally aligned with it and the ``∯`` sentinel
    lookup is valid; otherwise ``None`` is returned so the caller falls back to the
    unprotected scan rather than reading a misaligned position.
    """
    if protected_text is None:
        return None
    aligned = protected_text.replace(_UNKNOWN_PLACEHOLDER_EXPANSION, " ??")
    return aligned if len(aligned) == len(text) else None


def _resplit_multi_sentence_quote(
    text: str,
    min_interior_sentences: int = _QUOTE_MIN_INTERIOR_SENTENCES,
    min_words: int = _QUOTE_MIN_WORDS,
    protected_text: str | None = None,
) -> list[str] | None:
    """Re-split a self-contained quotation at its interior period boundaries.

    *min_interior_sentences* / *min_words* are the split-bias thresholds (lower =
    more eager to split). When provided, *protected_text* is the same segment with
    abbreviation periods protected as sentinels so restored abbreviations are not
    treated as quote-internal sentence boundaries. Returns the split pieces, or
    ``None`` when *text* should be left intact.
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

    # Use the abbreviation-protected scan only when it is positionally aligned
    # with *text*. The unknown-placeholder expansion ("No. ??" -> "No∯ &ᓷ&&ᓷ&")
    # is the lone length-changing rewrite; collapsing it restores parity so an
    # abbreviation period inside the quote is still recognized as a sentinel and
    # not over-split. If alignment cannot be restored, fall back to *text*.
    protected = _length_align_protected_scan(protected_text, text) or text
    spans = []
    last = 0
    for boundary in _QUOTE_INTERIOR_BOUNDARY_RE.finditer(text):
        # The lookahead is zero-width, so boundary.end() is the candidate start
        # letter itself. Split only before an uppercase letter (any cased script);
        # skip a lowercase or caseless follower so the boundary count stays exact.
        if not text[boundary.end() : boundary.end() + 1].isupper():
            continue
        if protected[boundary.start() - 1 : boundary.start()] == "∯":
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


def _split_on_uppercase_boundary(
    text: str,
    whitespace_re: re.Pattern[str],
    starts_sentence: Callable[[str, int], bool] = _next_nonspace_char_starts_sentence,
) -> list[str] | None:
    # *starts_sentence* is the boundary predicate (default: the base Latin
    # uppercase-start test); en_es_zh passes its combined-profile variant so the
    # split loop is shared instead of copied.
    parts = []
    last = 0
    for match in whitespace_re.finditer(text):
        if not starts_sentence(text, match.end()):
            continue
        parts.append(text[last : match.start()])
        last = match.end()
    if not parts:
        return None
    parts.append(text[last:])
    return [part for part in parts if part]


def merge_quote_continuations(
    sentences: list[str],
    *,
    closer_re: re.Pattern[str],
    reporting_clause_re: re.Pattern[str] | None = None,
    latin_lowercase_continuation: bool = False,
    cjk_closers: frozenset[str] = frozenset(),
    cjk_follower_re: re.Pattern[str] | None = None,
) -> list[str]:
    """Merge a quote closer followed by a continuation into the preceding sentence.

    A segment that ends with a quote closer (matched by *closer_re*) and is
    followed by a continuation is one reported/quoted sentence, so the two are
    re-joined. The continuation qualifies when either:

    * *reporting_clause_re* matches it (e.g. a CJK reporting clause ``他说。``); or
    * *latin_lowercase_continuation* is set and the continuation starts with a
      lowercase letter *and* the matched closer is not one of *cjk_closers* (a
      lowercase Latin word after a Latin closer continues the quote, but after a
      CJK closer 」』》】 it is a separate sentence).

    The merge separator is empty when *cjk_follower_re* is ``None`` (the CJK
    variant, which always concatenates directly) or when it matches the start of
    the continuation (a CJK ideograph follower needs no space); otherwise a single
    space joins a Latin continuation.
    """
    if reporting_clause_re is None and not latin_lowercase_continuation:
        return sentences

    merged: list[str] = []
    for current in sentences:
        if merged and _should_merge_quote_continuation(
            merged[-1],
            current,
            closer_re=closer_re,
            reporting_clause_re=reporting_clause_re,
            latin_lowercase_continuation=latin_lowercase_continuation,
            cjk_closers=cjk_closers,
        ):
            continuation = current.lstrip()
            if cjk_follower_re is None or cjk_follower_re.match(continuation):
                separator = ""
            else:
                separator = " "
            merged[-1] = merged[-1] + separator + continuation
        else:
            merged.append(current)
    return merged


def _should_merge_quote_continuation(
    previous: str,
    current: str,
    *,
    closer_re: re.Pattern[str],
    reporting_clause_re: re.Pattern[str] | None,
    latin_lowercase_continuation: bool,
    cjk_closers: frozenset[str],
) -> bool:
    previous = previous.rstrip()
    current = current.lstrip()
    if not previous or not current:
        return False
    closer = closer_re.search(previous)
    if not closer:
        return False
    if latin_lowercase_continuation:
        # A lowercase Latin continuation is only a quote continuation after a
        # Latin quote closer ("…" then he said). After a CJK closer (」』》】) a
        # lowercase word is a separate sentence; only the reporting clause merges
        # those.
        is_cjk_closer = any(c in cjk_closers for c in closer.group())
        if current[0].islower() and not is_cjk_closer:
            return True
    if reporting_clause_re is not None and reporting_clause_re.match(current):
        return True
    return False
