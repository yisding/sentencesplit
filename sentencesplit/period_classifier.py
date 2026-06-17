# -*- coding: utf-8 -*-
"""Single-pass period classifier for abbreviation boundary protection (V2 engine).

This module implements the ``PeriodClassifier`` that replaces ONLY the per-line
abbreviation-protection step inside
``AbbreviationReplacer.search_for_abbreviations_in_string``
(``abbreviation_replacer.py:582``). Everything else in ``replace()`` is unchanged:
the upstream single-letter/possessive rules, ``replace_multi_period_abbreviations``,
the compact-ampm / uppercase-initialism / allcaps-imprint / ampm / standalone-I
passes all still run after this step and still see the same ``∯``/``.`` mix.

Design (per ``analysis/ABBREVIATION_ENGINE_V2_PLAN.md`` §2): each candidate period
is classified ONCE from the ORIGINAL line text (never from a sentinel left by a
prior decision), into one of three decisions — PROTECT (``.`` -> ``∯``), BOUNDARY
(``.`` stays), or PLACEHOLDER (the rare number-abbr ``??`` case). The decisions
are then realized GLOBALLY per (abbr, follower-char) unit — mirroring the legacy
``re.sub`` semantics — and the line is rebuilt in a single pass.

Zero third-party dependencies: stdlib ``re``/``enum``/``dataclasses`` plus the
package's own ``split_mode_rank``.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from enum import auto
from threading import Lock
from typing import Callable

from sentencesplit.utils import split_mode_rank


class Decision(enum.Enum):
    PROTECT = auto()
    BOUNDARY = auto()
    PLACEHOLDER = auto()


# Tri-state sentinel for ``AbbrPolicy.classify_special``: distinct from ``None``
# (which means BOUNDARY) and from any ``Decision`` (which is honored verbatim).
NOT_HANDLED = object()


def _spans_intersect(sorted_edits: list["Edit"]) -> bool:
    """True if any two of *sorted_edits* (sorted by start) overlap.

    The common paths emit only lone single-period edits whose ``[start, end)``
    intervals never intersect; this fast check lets ``_dedup_sorted`` skip the
    longest-first overlap resolution entirely for them.
    """
    prev_end = -1
    for e in sorted_edits:
        if e.start < prev_end:
            return True
        prev_end = max(prev_end, e.end)
    return False


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


class PeriodClassifier:
    """PORT-FIRST engine; constructed once per replacer instance, cached.

    All ``RE_*`` patterns are SUFFIX-ONLY (no lookbehind): the legacy
    ``(?<=[B]{escaped})`` lookbehind is DISCHARGED by candidate enumeration (the
    period already sits right after a word-boundary ``<abbr>``), so we never
    re-test it. Each is matched with ``.match(line, c.period_idx)`` — the ``.``
    itself is at ``period_idx`` and the suffix lookaheads test from there.
    """

    def __init__(self, replacer, data, policy: AbbrPolicy) -> None:
        self.r = replacer  # back-ref: flags + STARTER_AWARE_PREPOSITIVE + helpers + split_mode
        self.data = data  # the SAME _AbbreviationData (automaton, abbreviations, sets, boundary_class)
        self.policy = policy
        self.rank = split_mode_rank(replacer.split_mode)
        # data.boundary_class ("\\s" or "\\s<escaped-elision>") is read off `data`
        # in _full_pattern; the suffix patterns below are lookbehind-free.
        fc = policy.follower_class
        # ``cjk`` is an extra follower alternative WITHOUT a leading ``\s`` (it
        # matches a CJK ideograph sitting immediately after the period). Base
        # policy leaves it empty, so ``cjk`` contributes nothing to any pattern.
        # ``cjk_follower_regular_only`` (standalone zh) restricts that alternative
        # to the REGULAR branch only, matching the legacy zh override that wove CJK
        # into ``replace_period_of_abbr`` alone; ``cjk_other`` is then inert for the
        # prepositive / number-lower suffixes (they keep the base no-CJK shape).
        cjk = ("|" + policy.cjk_follower_class) if policy.cjk_follower_class else ""
        cjk_other = "" if policy.cjk_follower_regular_only else cjk

        def _regular(follower: str) -> re.Pattern[str]:
            return re.compile(r"\.(?=((\.|\:|-|\?|,)" + cjk + r"|(\s(" + follower + r"|I\s|I'm|I'll|\d|\())))")

        self.RE_REGULAR = _regular(fc)
        # Per-stem REGULAR follower-class override (kazakh): a second REGULAR regex
        # with a widened follower class, selected by ``_regular_re`` for the
        # override stems only. Inert (empty set) for every other policy.
        if policy.regular_follower_overrides is not None:
            self._regular_override_stems, override_class = policy.regular_follower_overrides
            self.RE_REGULAR_OVERRIDE = _regular(override_class)
        else:
            self._regular_override_stems = frozenset()
            self.RE_REGULAR_OVERRIDE = self.RE_REGULAR
        self.RE_PREPOSITIVE = re.compile(r"\.(?=(\s|:\d+" + cjk_other + r"))")
        # The number UPPER arms intentionally carry NO ``cjk`` alternative: in the
        # legacy en_es_zh override the upper branch fires only for an ASCII-upper
        # follower (so the period is not adjacent to a CJK char), and a CJK
        # follower is always a SEPARATE no-space candidate that flows through the
        # number-lower arm below. Keeping CJK out here matches legacy exactly.
        self.RE_NUM_UP_JOIN = re.compile(r"\.(?=\s[^\W\d_])")
        self.RE_NUM_UP_SPLIT = re.compile(r"\.(?=\s(?:[IVXLCDM]{2,}|[VXLCDM])\b)")
        self.RE_NUM_LOW = re.compile(r"\.(?=(\s\d|\s+\(|\s\?\?(?!\?)|\s[IVXLCDM]+\b" + cjk_other + r"))")
        # Conservative variant of the number-lower suffix used ONLY by
        # ``ascii_only_upper_heuristic`` policies (en_es_zh). There a non-ASCII
        # uppercase follower ("Vol. Él") is ascii-gated out of the UPPER arm, so
        # in 'conservative' mode it must still be JOINED — legacy widened the
        # letter slot from ``\s[IVXLCDM]+\b`` to ``\s[^\W\d_]`` (any letter,
        # including capitals). Base/balanced/aggressive keep the Roman-only slot.
        self.RE_NUM_LOW_JOIN = re.compile(r"\.(?=(\s\d|\s+\(|\s\?\?(?!\?)|\s[^\W\d_]" + cjk_other + r"))")
        self.RE_NUM_QQ = re.compile(r"\.(?=\s\?\?(?!\?))")  # the PLACEHOLDER alternative, isolated
        # Lookbehind-anchored full patterns for the GLOBAL realization pass, keyed by
        # the suffix that drove the decision. Built lazily per (am_escaped, suffix).
        # The classifier is shared across concurrent ``segment()`` calls, so the
        # lazy write is guarded (double-checked) under ``_full_cache_lock`` — a free-
        # threaded build has no GIL to make the dict insert implicitly atomic.
        self._full_cache: dict[tuple[str, str], re.Pattern[str]] = {}
        self._full_cache_lock = Lock()

    @property
    def _leans_split(self) -> bool:
        return self.rank >= 2

    @property
    def _leans_join(self) -> bool:
        return self.rank <= 0

    def _elision_strip(self, am: str) -> str:
        if self.data.elision_chars and am and am[0] in self.data.elision_chars:
            return am[1:]
        return am

    def _regular_re(self, am_lower: str) -> re.Pattern[str]:
        """REGULAR-branch suffix regex for *am_lower*: the per-stem widened variant
        for an override stem (kazakh), else the base ``RE_REGULAR``."""
        if am_lower in self._regular_override_stems:
            return self.RE_REGULAR_OVERRIDE
        return self.RE_REGULAR

    def _follower_is_upper(self, c: Candidate) -> bool:
        """Whether *c*'s follower counts as the capital-is-boundary cue (@652).

        Gated by ``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`` (off for most languages).
        ``AbbrPolicy.ascii_only_upper_heuristic`` (en_es_zh) further restricts the
        cue to ASCII uppercase, so a non-ASCII capital ("Sr. Élena") is NOT a
        boundary cue and flows through the normal protection branches.
        """
        ch = c.follower_char
        if not ch or not self.r.CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE:
            return False
        if self.policy.ascii_only_upper_heuristic and not ch.isascii():
            return False
        return ch.isupper()

    # ------------------------------------------------------------------ enumerate
    def enumerate_candidates(self, line: str) -> list[Candidate]:
        """Reproduce the reachability gate EXACTLY (search_for_abbreviations_in_string @582-611).

        Enumerate candidates via the automaton ``<abbr>.`` prefilter (key @190, with
        the U+0130 İ bare-key exception inherited by reusing ``data.automaton``
        verbatim — never rebuild keys), then ``match_re.finditer(line)`` on the
        ORIGINAL line, period-less skip ``if line[end:end+1] != '.'`` @601, and
        follower-char ``line[end+2:end+3] if line[end:end+2]=='. ' else ''`` @603
        read from the SAME occurrence. Dedup by (elision-stripped am_lower,
        follower_char) @609, paired with GLOBAL-per-unit realization in ``rewrite``.
        """
        lowered = line.lower()
        found = self.data.automaton.search(lowered)
        cands: list[Candidate] = []
        for idx in sorted(found):  # legacy ID order (@587)
            stripped, _stripped_lower, escaped, match_re = self.data.abbreviations[idx]
            # The elision-stripped lowercase form is identical for every occurrence
            # of this abbr on the line, so derive it once here (set lookups / dedup /
            # classify all read it off the Candidate instead of recomputing).
            am_lower = self._elision_strip(stripped).lower()
            for m in match_re.finditer(line):  # ORIGINAL line, word-boundary-prefixed, IGNORECASE
                end = m.end()
                if line[end : end + 1] != ".":  # period-less skip (@601)
                    continue
                fch = line[end + 2 : end + 3] if line[end : end + 2] == ". " else ""  # follower-char (@603)
                cands.append(Candidate(end, stripped, am_lower, escaped, fch))
        # PER-OCCURRENCE policies (russian) classify + anchor every occurrence at
        # its own period from its own ORIGINAL context, so the (am, char) dedup
        # that the global-realize model relies on would lose distinct positions.
        # Keep every occurrence; only collapse exact-duplicate periods (same idx).
        if self.policy.realize_per_occurrence:
            by_idx: dict[int, Candidate] = {}
            for c in cands:
                by_idx.setdefault(c.period_idx, c)
            return [by_idx[i] for i in sorted(by_idx)]
        # DEDUP exactly as legacy @609: classify ONE representative per
        # (elision-stripped am_lower, follower_char) — PLUS a structural
        # follower-class discriminator computed from the period position on the
        # ORIGINAL line. ``follower_char`` is populated ONLY for the ``". "``
        # (period + ASCII space) case, so every other real follower — an immediate
        # non-space follower (``inc.)`` / ``inc.x``) or a non-ASCII / other-
        # whitespace follower (``inc.\xa0`` / ``inc.\t`` / EOL) — collapses to
        # follower_char "". Without the discriminator two occurrences of the SAME
        # abbr with genuinely different real followers shared one key and only the
        # FIRST (representative) was classified: if it was a BOUNDARY, the global
        # realization was skipped and a colliding sibling that should PROTECT was
        # dropped, making the output depend on clause order. The follower-class
        # ('I' immediate non-space / 'S' ASCII-space / 'W' other-whitespace /
        # 'E' end-of-line) keeps those distinct real followers from colliding so
        # each is classified on its own period. This is a STRICT REFINEMENT of the
        # old key (a former key only ever splits into finer keys, never merges),
        # so every former representative is still a representative and the
        # GLOBAL per-unit realization in rewrite() — which re-tests each
        # occurrence's own follower via the case-sensitive full.finditer — is
        # unchanged.
        seen: dict[tuple[str, str, str], bool] = {}
        out: list[Candidate] = []
        for c in cands:
            k = (c.am_lower, c.follower_char, self._follower_class(line, c.period_idx))
            if k not in seen:
                seen[k] = True
                out.append(c)
        return out

    @staticmethod
    def _follower_class(line: str, p: int) -> str:
        """Structural follower-class at period index *p* on the ORIGINAL *line*.

        Dedup-key discriminator ONLY (never stored on the Candidate, so
        ``follower_char`` and all its readers stay byte-identical):
          - 'E' end-of-line / no follower: ``p + 1 >= len(line)``
          - 'I' immediate non-space follower: ``not line[p + 1].isspace()``
          - 'S' ASCII-space follower: ``line[p : p + 2] == ". "``
          - 'W' other-whitespace follower (``\\xa0``/``\\t``/``\\n``/…): otherwise
        Whitespace is judged with ``str.isspace`` (Unicode-aware), matching the
        suffix regexes' Unicode ``\\s`` so the realization re-test agrees.
        """
        if p + 1 >= len(line):
            return "E"
        if not line[p + 1].isspace():
            return "I"
        if line[p : p + 2] == ". ":
            return "S"
        return "W"

    # ------------------------------------------------------------------- classify
    def classify(self, c: Candidate, line: str) -> Decision:
        """PURE: reads ONLY *c* + the ORIGINAL *line*; never a sentinel.

        Reproduces the branch dispatch from scan_for_replacements @644-680. Thin
        wrapper over ``_classify_with_suffix`` (oracle / per-occurrence callers want
        just the decision); the global-realize hot path calls the combined method
        directly to avoid recomputing ``am_lower``/``upper``/the branch in
        ``_suffix_for``.
        """
        return self._classify_with_suffix(c, line)[0]

    def _classify_with_suffix(self, c: Candidate, line: str) -> tuple[Decision, str | None]:
        """Decide *c* AND return the global-realization suffix in one pass.

        The suffix is ``None`` for BOUNDARY (no realization) and for decisions made
        by ``classify_special`` (the per-occurrence / ``realize_suffix`` paths handle
        their own realization). Otherwise it is the SAME suffix pattern that drove
        the decision, so the caller never re-derives ``am_lower``/``upper``/the
        branch in a second ``_suffix_for`` pass.
        """
        # 1) language override seam (inert for BASE_POLICY)
        if self.policy.classify_special is not None:
            d = self.policy.classify_special(self, line, c)
            if d is not NOT_HANDLED:
                # realize_suffix / realize_per_occurrence own realization for these.
                return (Decision.BOUNDARY if d is None else d), None
        am_lower = c.am_lower
        upper = self._follower_is_upper(c)  # @652
        prep = self.data.prepositive_set
        num = self.data.number_abbr_set
        # 2) the gate that LEAVES a capital-follower plain abbr as a BOUNDARY (@661 negated):
        if upper and am_lower not in prep and am_lower not in num:
            return Decision.BOUNDARY, None  # period stays '.'
        # 3) PREPOSITIVE branch (@663-669)
        if am_lower in prep:
            d = self._classify_prepositive(c, line, am_lower)
            return d, (self.RE_PREPOSITIVE.pattern if d is not Decision.BOUNDARY else None)
        # 4) NUMBER branch (@613-624, @670-677)
        if am_lower in num:
            return self._classify_number_with_suffix(c, line, upper)
        # 5) REGULAR branch (@568/574/679)
        regular = self._regular_re(am_lower)
        if regular.match(line, c.period_idx):
            return Decision.PROTECT, regular.pattern
        return Decision.BOUNDARY, None

    def _classify_prepositive(self, c: Candidate, line: str, am_lower: str) -> Decision:
        """PREPOSITIVE branch (scan_for_replacements @663-669)."""
        if self._leans_split and am_lower in self.r.AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST:
            return Decision.BOUNDARY  # should_protect False (@664)
        if am_lower in self.r.STARTER_AWARE_PREPOSITIVE and self._leans_split:  # @666 callback (@631-642)
            i = c.period_idx
            if line[i + 1 : i + 2] == ":":
                return Decision.PROTECT
            return Decision.BOUNDARY if self.r._follower_is_likely_sentence_start(line, i + 1) else Decision.PROTECT
        return Decision.PROTECT if self.RE_PREPOSITIVE.match(line, c.period_idx) else Decision.BOUNDARY  # @669

    def _classify_number_with_suffix(self, c: Candidate, line: str, upper: bool) -> tuple[Decision, str | None]:
        """NUMBER branch returning ``(decision, realization-suffix)`` in one pass.

        Suffix mirrors ``_suffix_for``'s number arm exactly; ``None`` for BOUNDARY.
        """
        i = c.period_idx
        if upper:
            rx = self.RE_NUM_UP_JOIN if self._leans_join else self.RE_NUM_UP_SPLIT  # @619 / @622
            if rx.match(line, i):
                return Decision.PROTECT, rx.pattern
            return Decision.BOUNDARY, None
        if self.RE_NUM_QQ.match(line, i):  # @623 ?? arm + @626 placeholder
            return Decision.PLACEHOLDER, self.RE_NUM_QQ.pattern
        num_low = self._num_low_pattern()
        if num_low.match(line, i):  # @623 the rest
            return Decision.PROTECT, num_low.pattern
        if len(self._elision_strip(c.am_stripped)) > 1:  # @676 multi-char regular fallthrough
            # en_es_zh guard (legacy ``not (char and char.isupper())`` @141):
            # under ``ascii_only_upper_heuristic`` a NON-ASCII uppercase follower
            # ("Fig. Él") reached this branch only because the capital cue was
            # ASCII-gated and (in 'conservative') the join arm did not catch it;
            # it must still START A SENTENCE, so the regular fallthrough (whose
            # ``[^\W\d_]`` class would otherwise PROTECT a capital) is skipped.
            # Inert for base policy: there ``upper`` is the ungated capital cue,
            # so any uppercase follower already took the UPPER arm above.
            if self.policy.ascii_only_upper_heuristic and c.follower_char and c.follower_char.isupper():
                return Decision.BOUNDARY, None
            regular = self._regular_re(c.am_lower)
            if regular.match(line, i):
                return Decision.PROTECT, regular.pattern
            return Decision.BOUNDARY, None
        return Decision.BOUNDARY, None  # single-char 'p' excluded (@676)

    def _num_low_pattern(self) -> re.Pattern[str]:
        """Select the number-lower suffix: conservative join-variant for
        ``ascii_only_upper_heuristic`` policies (en_es_zh) in 'conservative'
        mode, else the Roman-only base pattern."""
        if self.policy.ascii_only_upper_heuristic and self._leans_join:
            return self.RE_NUM_LOW_JOIN
        return self.RE_NUM_LOW

    # -------------------------------------------------------- suffix selection
    def _suffix_for(self, c: Candidate, line: str, d: Decision) -> str:
        """Return the global-realization suffix for a ``classify_special`` decision.

        Only reached from ``_collect_edits`` when ``_classify_with_suffix`` returned
        no suffix, which happens exclusively for a ``classify_special`` decision on a
        non-per-occurrence policy. Every such policy owns its realization via
        ``realize_suffix`` (the generic 3-branch dispatch in ``_classify_with_suffix``
        already returns the suffix for all non-special decisions, so it is never
        re-derived here). A ``classify_special`` policy that sets neither
        ``realize_suffix`` nor ``realize_per_occurrence`` is a policy bug and is
        rejected loudly rather than silently re-deriving a possibly-wrong suffix.
        """
        if self.policy.realize_suffix_pattern is not None:
            return self.policy.realize_suffix_pattern
        if self.policy.realize_suffix is not None:
            return self.policy.realize_suffix(self, c, line, d)
        raise ValueError(  # pragma: no cover - policy contract; no shipping policy hits this
            "classify_special policy must set realize_suffix or realize_per_occurrence "
            f"to own its global realization (decision={d!r})"
        )

    def _full_pattern(self, am_escaped: str, suffix: str) -> re.Pattern[str]:
        key = (am_escaped, suffix)
        pat = self._full_cache.get(key)
        if pat is not None:
            return pat
        with self._full_cache_lock:
            pat = self._full_cache.get(key)
            if pat is not None:
                return pat
            # The stored ``am_escaped`` is the lowercase abbreviation form, but the
            # line carries the occurrence's ORIGINAL case ("Dr."). Legacy escapes
            # the original-case ``am.strip()`` and runs a case-SENSITIVE ``re.sub``
            # per occurrence; the union over every IGNORECASE occurrence of this
            # abbr (all sharing one classify decision via ``am_lower``) is an
            # IGNORECASE match of the ABBREVIATION only — while the suffix follower
            # class (e.g. base ``[a-z]``) must stay case-SENSITIVE so "Ltd. She"
            # (capital follower) does NOT match the lowercase-follower regular
            # suffix. Scope IGNORECASE to the lookbehind abbreviation only via the
            # inline ``(?i:...)`` group; the suffix keeps the pattern's default
            # (case-sensitive) flags.
            pat = re.compile(
                r"(?<=[" + self.data.boundary_class + r"](?i:" + am_escaped + r"))" + suffix,
            )
            self._full_cache[key] = pat
        return pat

    @staticmethod
    def _qq_span(line: str, p: int) -> str:
        """Return the trailing ' ??' substring after the period at *p* (incl. leading space)."""
        # period at p; matched RE_NUM_QQ means line[p+1:] starts with \s\?\?(?!\?)
        # capture exactly the single whitespace + the two '?'.
        return line[p + 1 : p + 4]  # e.g. " ??"

    def _placeholder_edit(self, line: str, p: int) -> Edit:
        """The PLACEHOLDER splice for the candidate period at *p*: overwrite the
        '. ??' run with '∯ <placeholder>'. Shared by the per-occurrence and global
        branches of ``_collect_edits`` so the qq-span width lives in one place."""
        qq_end = (p + 1) + len(self._qq_span(line, p))
        return Edit(p, qq_end, "∯ " + self.r._UNKNOWN_PLACEHOLDER, p)

    # -------------------------------------------------------------------- rewrite
    def _collect_edits(self, line: str) -> list[Edit]:
        edits: list[Edit] = []
        per_occurrence = self.policy.realize_per_occurrence
        # The leading-space probe is candidate-independent (it just lets the
        # lookbehind match an abbr that opens the line, the legacy " " + txt trick),
        # so build it once per line instead of once per candidate.
        probe = " " + line
        for c in self.enumerate_candidates(line):
            # Decided ONCE from original text for this (am, char); the combined call
            # also yields the global-realization suffix so the global path never
            # re-derives am_lower/upper/branch in a second pass.
            d, suffix = self._classify_with_suffix(c, line)
            if d is Decision.BOUNDARY:
                continue
            if per_occurrence:
                # Anchor the edit to THIS occurrence's own period only — never a
                # global re-anchored suffix — so position-dependent decisions
                # (russian ``ср.``) are honored per occurrence. Mirrors the legacy
                # per-match ``re.sub`` callback returning ``group()[:-1] + "∯"``.
                p = c.period_idx
                if d is Decision.PROTECT:
                    # ``protect_edit`` (slovak) may splice a whole multi-period span;
                    # default is the lone trailing period.
                    if self.policy.protect_edit is not None:
                        edits.append(self.policy.protect_edit(self, c, line))
                    else:
                        edits.append(Edit(p, p + 1, "∯", p))
                else:  # PLACEHOLDER (unused by current per-occurrence policies)
                    edits.append(self._placeholder_edit(line, p))
                continue
            # ``_classify_with_suffix`` returns None for decisions made by
            # ``classify_special`` (the ``realize_suffix`` policies own realization):
            # fall back to ``_suffix_for`` there, which honors ``policy.realize_suffix``.
            if suffix is None:
                suffix = self._suffix_for(c, line, d)
            # Realize GLOBALLY over the line (legacy global re.sub semantics): the
            # chosen suffix regex, re-anchored with the lookbehind, applied to EVERY
            # occurrence of THIS abbr on the line. Leading-space prefix matches the
            # legacy _replace_with_escape/replace_period_of_abbr " " + txt trick.
            full = self._full_pattern(c.am_escaped, suffix)
            for m in full.finditer(probe):
                p = m.start() - 1  # original-line period index
                if d is Decision.PROTECT:
                    edits.append(Edit(p, p + 1, "∯", p))
                else:  # PLACEHOLDER
                    edits.append(self._placeholder_edit(line, p))
        return edits

    @staticmethod
    def _dedup_sorted(edits: list[Edit]) -> list[Edit]:
        # A doubly protected period (multi-char NUMBER hitting both NUM_LOW and
        # REGULAR realizations) collapses to one edit — idempotent, matches legacy's
        # two idempotent re.subs. Dedup by (start, end, replacement).
        seen: dict[tuple[int, int, str], Edit] = {}
        for e in edits:
            k = (e.start, e.end, e.replacement)
            if k not in seen:
                seen[k] = e
        ordered = sorted(seen.values(), key=lambda e: (e.start, e.end))
        # Resolve overlapping spans longest-first, mirroring the legacy
        # length-descending mutating ``str.replace`` where a shorter span embedded
        # in an already-rewritten longer span becomes a no-op (slovak whole-span:
        # "a.s.a.p." enumerates both ``a.s.a.p`` [0:8] and ``a.s`` [0:4]). For the
        # non-whole-span paths every edit is a single trailing period and these
        # spans never intersect, so this pass is an identity there.
        if not _spans_intersect(ordered):
            return ordered
        kept: list[Edit] = []
        for e in sorted(ordered, key=lambda x: (x.start - x.end, x.start)):  # widest first
            if any(e.start < k.end and k.start < e.end for k in kept):
                continue  # embedded in / overlapping an already-kept wider edit
            kept.append(e)
        return sorted(kept, key=lambda e: (e.start, e.end))

    @staticmethod
    def _rebuild(line: str, edits: list[Edit]) -> str:
        parts: list[str] = []
        cur = 0
        for e in edits:
            assert e.start >= cur, f"overlapping edits at {e.start} (cur={cur})"  # loud non-overlap guard
            parts.append(line[cur : e.start])
            parts.append(e.replacement)
            cur = e.end
        parts.append(line[cur:])
        return "".join(parts)

    def rewrite(self, line: str) -> str:
        edits = self._dedup_sorted(self._collect_edits(line))
        if not edits:
            return line
        return self._rebuild(line, edits)

    # ------------------------------------------------------------ oracle adapter
    def protect_positions(self, line: str) -> list[int]:
        """Oracle adapter: period indices protected on *line* (matches oracle.py:184).

        Reported by walking the original line against the rebuilt line in lockstep
        (identical semantics to ``oracle._diff_line_positions``): every ``.`` -> ``∯``
        offset is recorded, the ``??`` -> placeholder expansion is resynced. A
        single-period PROTECT therefore reports its ``period_idx``; a whole-span
        PROTECT (slovak) reports EVERY interior+trailing period it sentinelizes; a
        PLACEHOLDER contributes ONLY the period before it (oracle.py:105-109).
        """
        edits = self._dedup_sorted(self._collect_edits(line))
        if not edits:
            return []
        rebuilt = self._rebuild(line, edits)
        positions: list[int] = []
        i = j = 0
        n, m = len(line), len(rebuilt)
        placeholder = self.r._UNKNOWN_PLACEHOLDER
        while i < n and j < m:
            oc, pc = line[i], rebuilt[j]
            if oc == pc:
                i += 1
                j += 1
            elif oc == "." and pc == "∯":
                positions.append(i)
                i += 1
                j += 1
            elif line.startswith("??", i) and rebuilt.startswith(placeholder, j):
                i += 2
                j += len(placeholder)
            else:  # pragma: no cover - alignment invariant; loud if ever violated
                raise AssertionError(f"unexpected rebuild divergence at orig[{i}]={oc!r} / rebuilt[{j}]={pc!r}")
        return sorted(set(positions))
