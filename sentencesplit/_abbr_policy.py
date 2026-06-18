# -*- coding: utf-8 -*-
from __future__ import annotations

import enum
from dataclasses import dataclass
from enum import auto
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sentencesplit.period_classifier import PeriodClassifier


class Decision(enum.Enum):
    PROTECT = auto()
    BOUNDARY = auto()
    PLACEHOLDER = auto()


# Tri-state sentinel for ``AbbrPolicy.classify_special``: distinct from ``None``
# (which means BOUNDARY) and from any ``Decision`` (which is honored verbatim).
NOT_HANDLED = object()


@dataclass(frozen=True, slots=True)
class Edit:
    """A position-anchored splice over the original line.

    PROTECT      -> Edit(p, p+1, "∯", p)
    PLACEHOLDER  -> Edit(p, qq_end, "∯ &ᓷ&&ᓷ&", p)  where qq_end spans the trailing " ??"
    BOUNDARY     -> no Edit emitted
    """

    start: int  # original-line index where the splice begins
    end: int  # original-line index (exclusive) the splice overwrites
    replacement: str
    period_idx: int  # the original index of the candidate '.' (for oracle reporting)


@dataclass(frozen=True, slots=True)
class Candidate:
    period_idx: int  # index of the '.' in the ORIGINAL line (== match.end())
    # Index where the abbreviation token begins on the ORIGINAL line, so it occupies
    # ``line[abbr_start:period_idx]``. Equal to ``period_idx - len(am_stripped)``:
    # ``match_re`` matches the stored literal under ``re.IGNORECASE``, which folds
    # 1:1 (a pattern char matches exactly one subject char), so the on-line span
    # length always equals ``len(am_stripped)``. Computed once here so the
    # per-occurrence policies (russian ``ср.``, slovak/bulgarian whole-span) read it
    # off the Candidate instead of re-deriving the offset with subtly different
    # ``.strip()`` / elision dances.
    abbr_start: int
    am_stripped: str  # abbreviation text as stored (elision NOT yet stripped)
    am_lower: str  # elision-stripped, lowercased am — the set-lookup / dedup key (computed once)
    am_escaped: str  # data.abbreviations[idx][2], the pre-built re.escape
    follower_char: str  # char after "abbr. " (line[end+2:end+3] if line[end:end+2]==". " else "")


@dataclass(frozen=True, slots=True)
class AbbrPolicy:
    """Per-language descriptor; english/en_legal ride ``BASE_POLICY`` with zero code.

    The classifier reads the English flags (``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE``,
    ``STARTER_AWARE_PREPOSITIVE``, ``AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST``) and
    ``split_mode`` off the replacer back-reference (single source), so they are NOT
    duplicated here.
    """

    # REGULAR-branch lowercase follower class; en_es_zh -> "[^\\W\\d_]".
    # boundary_class is NOT stored here: it is read off ``_AbbreviationData.boundary_class``
    # at construction so fr/it elision ("\\s’'") is automatic and never duplicated.
    follower_class: str = "[a-z]"
    # Per-stem REGULAR-branch follower-class override. ``(stems, follower_class)``:
    # any candidate whose elision-stripped lowercased abbreviation is in *stems*
    # uses *follower_class* in the REGULAR branch (and its global-realization suffix)
    # instead of ``follower_class`` above. Kazakh uses this to widen the ASCII
    # ``[a-z]`` follower to the Kazakh-Cyrillic + Latin lowercase class
    # ``[a-zа-яёәғқңөұүһі]`` for the 39 formerly-dotted stems ("обл. қала" does NOT
    # split) WITHOUT touching the always-dotless stems ("См. рис." still splits).
    # The override only widens the lowercase-letter slot; the rest of the REGULAR
    # suffix (``\.|:|-|\?|,`` and ``\s(I\s|I'm|I'll|\d|\()``) is identical, so a
    # WIDE stem rides the base REGULAR dispatch with one swapped class. Base None ==
    # every stem uses ``follower_class``.
    regular_follower_overrides: tuple[frozenset[str], str] | None = None
    # An extra follower alternative WITHOUT a leading ``\s`` (so it matches a
    # follower that sits immediately after the period). en_es_zh uses the CJK
    # ideograph class ``[㐀-鿿]`` here: "U.S.标准" / "etc.标准" protect even
    # without an intervening space. Woven into the regular / prepositive /
    # number-lower suffix patterns (or the regular branch only, see
    # ``cjk_follower_regular_only``). Base = "" (inert).
    cjk_follower_class: str = ""
    # When True the ``cjk_follower_class`` alternative is woven ONLY into the
    # REGULAR-branch suffix (and the number-branch's multi-char REGULAR
    # fallthrough, which reuses ``RE_REGULAR``), NOT into the prepositive or
    # number-lower suffixes. Standalone ``zh`` needs this: its legacy
    # ``Chinese.AbbreviationReplacer`` overrode ONLY ``replace_period_of_abbr``
    # (the regular branch), adding the CJK follower ``[一-鿿]`` there,
    # while its prepositive / number branches inherited the base (no-CJK)
    # suffixes. en_es_zh, by contrast, overrode the whole
    # ``scan_for_replacements`` and wove CJK into every branch, so it leaves this
    # False. Base = False.
    cjk_follower_regular_only: bool = False
    # When True the capital-follower-is-boundary heuristic only fires for an
    # ASCII uppercase follower (en_es_zh): a non-ASCII uppercase follower
    # ("Sr. Élena") is NOT treated as a sentence-start cue, so it falls through
    # to the normal protection branches (the regular ``[^\W\d_]`` follower class
    # then protects it). Base = False (any uppercase counts, per the flag).
    ascii_only_upper_heuristic: bool = False
    # Override seams (base = inert).
    # classify_special returns Decision.{PROTECT,BOUNDARY,PLACEHOLDER}, the module
    # sentinel NOT_HANDLED to fall through to the generic 3-branch dispatch, or
    # None == BOUNDARY. A language may override ONE branch and inherit the other two.
    classify_special: Callable[["PeriodClassifier", str, Candidate], object] | None = None
    # When a policy collapses every branch onto ONE suffix (german: protect any
    # period before whitespace, regardless of follower case), the branch-based
    # ``_suffix_for`` selection no longer describes the decision that
    # ``classify_special`` actually made. ``realize_suffix`` lets the policy name
    # the lookbehind-free suffix used for the GLOBAL realization pass directly, so
    # PROTECT is realized over every occurrence with the same rule that decided it.
    # base None == fall back to the branch-derived suffix.
    realize_suffix: Callable[["PeriodClassifier", Candidate, str, "Decision"], str] | None = None
    # When a ``classify_special`` policy collapses every branch onto ONE constant
    # suffix that is independent of (c, line, decision) — e.g. arabic "protect any
    # known abbr's bare period" or german "protect any period before whitespace" —
    # it names that lookbehind-free pattern string directly here instead of a
    # wrapper Callable. ``_suffix_for`` returns this string verbatim for the GLOBAL
    # realization pass. base None == fall back to the ``realize_suffix`` callable,
    # then (if that is also None) the branch-derived suffix / loud contract error.
    realize_suffix_pattern: str | None = None
    # When True the line is rewritten PER OCCURRENCE rather than per (abbr, char)
    # unit: every occurrence is classified from its own ORIGINAL context and its
    # edit is anchored to its own period, never realized globally. Required when
    # the decision is genuinely position-dependent so two same-key occurrences may
    # decide differently (russian ``ср.``: ``classify_special`` reads downstream
    # context — ``_sr_continues_compare_phrase`` / ``_starts_with_cyrillic_upper``
    # — that a single global re-anchored suffix cannot distinguish). This mirrors
    # the legacy per-match ``re.sub`` callback semantics exactly (russian.py:159).
    # base False == the global per-unit realization above.
    realize_per_occurrence: bool = False
    # When set (with ``realize_per_occurrence``), names the Edit a PROTECT decision
    # produces for a single occurrence — letting a policy splice MORE than the lone
    # trailing period. Slovak's legacy ``replace_period_of_abbr`` override does a
    # literal whole-span ``txt.replace(abbr + ".", abbr.replace(".", "∯") + "∯")``,
    # turning EVERY interior period of a spaced/compact abbreviation
    # ("s. r. o." -> "s∯ r∯ o∯", "a.s." -> "a∯s∯") into a sentinel, not just the
    # final one. ``protect_edit`` returns that whole-span Edit; overlapping
    # whole-span edits (e.g. "a.s.a.p." enumerating both ``a.s.a.p`` and ``a.s``)
    # are resolved longest-first, mirroring the legacy length-descending mutating
    # ``str.replace`` (shorter embedded spans become no-ops post-mutation).
    # base None == the lone-trailing-period Edit(p, p+1, "∯", p).
    protect_edit: Callable[["PeriodClassifier", Candidate, str], "Edit"] | None = None
    # Ordered downstream per-period post-classifier stages, each a
    # ``(replacer) -> None`` primitive that mutates ``replacer.text`` (defined in
    # ``abbreviation_replacer.py``: multi-period / compact-ampm / uppercase-initialism
    # / allcaps-imprint / ampm / standalone-I, plus language extras). These used to
    # be a fixed sequence hard-coded in ``AbbreviationReplacer.replace()``; owning
    # them here completes the single-pass model (S1) — a language reorders / drops /
    # augments the pipeline as data (German's reduced set, Kazakh's extra paren
    # pass). ``None`` means "inherit ``DEFAULT_POST_STAGES``" (the historical full
    # sequence), so the base languages are unchanged; an EMPTY tuple is honored as a
    # deliberate "run no post-stages" pipeline (distinct from None). Stages still
    # consume the ``∯`` IR; S4 moves them out-of-band and deletes the sentinel after.
    post_stages: tuple | None = None  # None == inherit DEFAULT_POST_STAGES; () == run nothing


BASE_POLICY = AbbrPolicy()  # module-level frozen constant; shared, read-only (free-threaded-safe)


def _cjk_regular_only_policy(cjk_follower_class: str) -> AbbrPolicy:
    """zh/ja: base ``[a-z]`` regular follower + a CJK/kana follower woven into the REGULAR branch only.

    The legacy ``Chinese``/``Japanese`` ``AbbreviationReplacer`` overrode ONLY
    ``replace_period_of_abbr`` (the regular branch), keeping the base regular suffix
    and appending a follower alternative *cjk_follower_class* with NO leading ``\\s``
    — so "U.S.标准" / "U.S.標準" / "ver.あいうえお" protect even without an
    intervening space. They did NOT override ``scan_for_replacements``, so the
    PREPOSITIVE and NUMBER branches inherit the base (no-CJK) suffixes
    (``cjk_follower_regular_only=True``), and they did NOT set
    ``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE``, so the capital-follower-is-boundary
    heuristic never fires (CJK has no letter case; a Latin capital follower flows
    through the normal split-mode dial in later passes). The base ``[a-z]`` follower
    class is kept verbatim. Verified order-independent + byte-identical to the legacy
    zh/ja protection step over every Golden/clean case and an adversarial
    regular(CJK/kana)/prepositive/number-follower corpus.
    """
    return AbbrPolicy(
        follower_class="[a-z]",
        cjk_follower_class=cjk_follower_class,
        cjk_follower_regular_only=True,
    )
