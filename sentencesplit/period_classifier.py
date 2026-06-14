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
import unicodedata
from dataclasses import dataclass, field
from enum import auto
from typing import Callable

from sentencesplit.utils import split_mode_rank


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
    occ_start: int  # m.start() (for elision/possessive context if ever needed)
    am_stripped: str  # abbreviation text as stored (elision NOT yet stripped)
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
    # An extra follower alternative WITHOUT a leading ``\s`` (so it matches a
    # follower that sits immediately after the period). en_es_zh uses the CJK
    # ideograph class ``[㐀-鿿]`` here: "U.S.标准" / "etc.标准" protect even
    # without an intervening space. Woven into the regular / prepositive /
    # number-lower suffix patterns. Base = "" (inert).
    cjk_follower_class: str = ""
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
    candidate_filter: Callable[[Candidate, str], bool] | None = None  # base None == accept all
    # When a policy collapses every branch onto ONE suffix (german: protect any
    # period before whitespace, regardless of follower case), the branch-based
    # ``_suffix_for`` selection no longer describes the decision that
    # ``classify_special`` actually made. ``realize_suffix`` lets the policy name
    # the lookbehind-free suffix used for the GLOBAL realization pass directly, so
    # PROTECT is realized over every occurrence with the same rule that decided it.
    # base None == fall back to the branch-derived suffix.
    realize_suffix: Callable[["PeriodClassifier", Candidate, str, "Decision"], str] | None = None
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
    pre_stages: tuple = field(default_factory=tuple)  # tuple[Callable[[str, replacer], str]]; base empty
    post_stages: tuple = field(default_factory=tuple)  # base empty


BASE_POLICY = AbbrPolicy()  # module-level frozen constant; shared, read-only (free-threaded-safe)
# Combined en/es/zh profile (Phase 5): any-Unicode-letter follower class, a CJK
# ideograph follower that protects even without an intervening space, and the
# ASCII-only restriction on the capital-follower-is-boundary heuristic. This
# reproduces the legacy ``EnglishSpanishChinese.AbbreviationReplacer``
# (``replace_period_of_abbr`` + ``scan_for_replacements`` overrides) as data.
EN_ES_ZH_POLICY = AbbrPolicy(
    follower_class=r"[^\W\d_]",
    cjk_follower_class="[㐀-鿿]",  # CJK unified ideographs (Ext-A start .. BMP end)
    ascii_only_upper_heuristic=True,
)

# German (Phase 5): the legacy ``Deutsch.AbbreviationReplacer`` overrode
# ``scan_for_replacements`` to a SINGLE rule, ``re.sub(r"(?<={am})\.(?=\s)", "∯")``,
# bypassing the base prepositive / number / regular trichotomy entirely. The
# effective behavior: PROTECT a known abbreviation's period whenever it is
# followed by whitespace, REGARDLESS of the follower's case — so "Dr. med. Meyer"
# keeps both periods even though "Meyer" is capitalized (German capitalizes all
# nouns, so a capital follower is NOT a sentence-start cue). ``classify_special``
# below replaces every branch; ``realize_suffix`` pins the realization pass to the
# same ``\.(?=\s)`` suffix so global PROTECT matches the decision exactly.
#
# Quirk FIXED (BC not required, plan §3): the legacy interpolated ``{am}``
# (== ``m.group()``, the boundary char + abbreviation) UNescaped into the
# lookbehind. ``_full_pattern`` re.escapes the abbreviation, so the V2 path is
# escape-everything-correct. The legacy "" works only by accident of the German
# abbreviation list containing no regex metacharacters; the V2 path is robust.
_DE_PROTECT_BEFORE_WHITESPACE = re.compile(r"\.(?=\s)")


def _de_classify_special(pc: "PeriodClassifier", line: str, c: Candidate) -> object:
    """German: every candidate period before whitespace PROTECTs; else BOUNDARY.

    Reproduces ``Deutsch.AbbreviationReplacer.scan_for_replacements`` (one rule,
    all branches collapsed). The candidate is already a known ``<abbr>.`` at a
    word boundary (enumeration's reachability gate), so only the suffix
    ``\\.(?=\\s)`` is tested here.
    """
    if _DE_PROTECT_BEFORE_WHITESPACE.match(line, c.period_idx):
        return Decision.PROTECT
    return Decision.BOUNDARY


def _de_realize_suffix(pc: "PeriodClassifier", c: Candidate, line: str, d: "Decision") -> str:
    """German global-realization suffix: ``\\.(?=\\s)`` for every PROTECT."""
    return _DE_PROTECT_BEFORE_WHITESPACE.pattern


DE_POLICY = AbbrPolicy(
    classify_special=_de_classify_special,
    realize_suffix=_de_realize_suffix,
)


# Russian (Phase 5): the legacy ``Russian.AbbreviationReplacer`` overrode ONLY the
# regular branch (``replace_period_of_abbr``); PREPOSITIVE/NUMBER lists are empty,
# so every Russian abbreviation flows through it. The override protects a known
# abbreviation's period UNCONDITIONALLY (no follower-class lookahead — the legacy
# ``re.sub(r"(^|\s)(abbr)\.")`` matches any period, so "5 куб.м." protects ``куб.``
# even though a Cyrillic ``м`` follows immediately with no space), EXCEPT:
#   - a SENTENCE_FINAL language-tag abbreviation (``рус.`` / ``англ.`` / ``др.`` …)
#     directly before a Cyrillic capital stays a BOUNDARY ("…и др. Она" splits),
#     unless the capital is a foreign-language gloss (``англ. Moscow`` → Latin, no
#     split) handled by the Cyrillic-capital gate; and
#   - ``ср.`` ("cf.") carries its own compare-phrase heuristic (russian.py:159-177).
# ``classify_special`` handles EVERY candidate (never NOT_HANDLED), so the base
# trichotomy never runs. ``realize_per_occurrence`` honors the per-match context
# the legacy callback read (``_sr_continues_compare_phrase`` scans downstream), so
# two ``ср.`` on one line may decide differently.
#
# Offset mapping from the legacy regex groups: legacy ``match.end()`` (just after
# the period) == ``period_idx + 1``; legacy ``match.start(2)`` (the abbreviation
# start) == ``period_idx - len(am_stripped)``.
_RU_CONJUNCTION_CONTINUATION_RE = re.compile(r"\sи\s+[А-ЯЁ]")
_RU_SENTENCE_START_OPENERS = frozenset("\"'“”‘’«„([{")


def _ru_content_start(text: str, start: int) -> int:
    index = start
    n = len(text)
    while index < n and (text[index].isspace() or text[index] in _RU_SENTENCE_START_OPENERS):
        index += 1
    return index


def _ru_starts_with_cyrillic_upper(text: str, start: int) -> bool:
    index = _ru_content_start(text, start)
    if index >= len(text):
        return False
    char = text[index]
    return char.isupper() and unicodedata.name(char, "").startswith("CYRILLIC")


def _ru_is_embedded_occurrence(text: str, abbr_start: int) -> bool:
    index = abbr_start - 1
    while index >= 0 and text[index].isspace():
        index -= 1
    if index < 0:
        return False
    return text[index] not in ".!?\r\n"


def _ru_continues_compare_phrase(text: str, start: int) -> bool:
    index = _ru_content_start(text, start)
    sentence_end = len(text)
    for boundary in ".!?":
        found = text.find(boundary, index)
        if found != -1:
            sentence_end = min(sentence_end, found)
    return _RU_CONJUNCTION_CONTINUATION_RE.search(text[index:sentence_end]) is not None


def _ru_classify_special(pc: "PeriodClassifier", line: str, c: Candidate) -> object:
    """Russian regular-branch override (russian.py:154-179), per occurrence.

    Returns PROTECT/BOUNDARY for every candidate (never NOT_HANDLED), reading the
    candidate's own ORIGINAL context. Mirrors the legacy ``replacement`` callback:
    ``match.group()[:-1] + "∯"`` == PROTECT, ``match.group()`` == BOUNDARY.
    """
    abbr_lower = c.am_stripped.strip().lower()
    period_idx = c.period_idx
    match_end = period_idx + 1  # legacy match.end()
    abbr_start = period_idx - len(c.am_stripped.strip())  # legacy match.start(2)
    if abbr_lower == "ср":
        if not _ru_starts_with_cyrillic_upper(line, match_end):
            return Decision.PROTECT
        if _ru_is_embedded_occurrence(line, abbr_start):
            return Decision.PROTECT
        if _ru_continues_compare_phrase(line, match_end):
            return Decision.BOUNDARY if pc._leans_split else Decision.PROTECT
        if pc._leans_join:
            return Decision.PROTECT
        return Decision.BOUNDARY
    sentence_final = getattr(pc.r, "SENTENCE_FINAL_ABBREVIATIONS", frozenset())
    if abbr_lower in sentence_final and _ru_starts_with_cyrillic_upper(line, match_end):
        return Decision.BOUNDARY
    return Decision.PROTECT


RU_POLICY = AbbrPolicy(
    classify_special=_ru_classify_special,
    realize_per_occurrence=True,
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
        cjk = ("|" + policy.cjk_follower_class) if policy.cjk_follower_class else ""
        self.RE_REGULAR = re.compile(r"\.(?=((\.|\:|-|\?|,)" + cjk + r"|(\s(" + fc + r"|I\s|I'm|I'll|\d|\())))")
        self.RE_PREPOSITIVE = re.compile(r"\.(?=(\s|:\d+" + cjk + r"))")
        # The number UPPER arms intentionally carry NO ``cjk`` alternative: in the
        # legacy en_es_zh override the upper branch fires only for an ASCII-upper
        # follower (so the period is not adjacent to a CJK char), and a CJK
        # follower is always a SEPARATE no-space candidate that flows through the
        # number-lower arm below. Keeping CJK out here matches legacy exactly.
        self.RE_NUM_UP_JOIN = re.compile(r"\.(?=\s[^\W\d_])")
        self.RE_NUM_UP_SPLIT = re.compile(r"\.(?=\s(?:[IVXLCDM]{2,}|[VXLCDM])\b)")
        self.RE_NUM_LOW = re.compile(r"\.(?=(\s\d|\s+\(|\s\?\?(?!\?)|\s[IVXLCDM]+\b" + cjk + r"))")
        # Conservative variant of the number-lower suffix used ONLY by
        # ``ascii_only_upper_heuristic`` policies (en_es_zh). There a non-ASCII
        # uppercase follower ("Vol. Él") is ascii-gated out of the UPPER arm, so
        # in 'conservative' mode it must still be JOINED — legacy widened the
        # letter slot from ``\s[IVXLCDM]+\b`` to ``\s[^\W\d_]`` (any letter,
        # including capitals). Base/balanced/aggressive keep the Roman-only slot.
        self.RE_NUM_LOW_JOIN = re.compile(r"\.(?=(\s\d|\s+\(|\s\?\?(?!\?)|\s[^\W\d_]" + cjk + r"))")
        self.RE_NUM_QQ = re.compile(r"\.(?=\s\?\?(?!\?))")  # the PLACEHOLDER alternative, isolated
        # Lookbehind-anchored full patterns for the GLOBAL realization pass, keyed by
        # the suffix that drove the decision. Built lazily per (am_escaped, suffix).
        self._full_cache: dict[tuple[str, str], re.Pattern[str]] = {}

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
            stripped, _stripped_lower, escaped, match_re, _next_word_re = self.data.abbreviations[idx]
            for m in match_re.finditer(line):  # ORIGINAL line, word-boundary-prefixed, IGNORECASE
                end = m.end()
                if line[end : end + 1] != ".":  # period-less skip (@601)
                    continue
                fch = line[end + 2 : end + 3] if line[end : end + 2] == ". " else ""  # follower-char (@603)
                cands.append(Candidate(end, m.start(), stripped, escaped, fch))
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
        # (elision-stripped am_lower, follower_char); each PROTECT is realized
        # GLOBALLY over the line in rewrite().
        seen: dict[tuple[str, str], bool] = {}
        out: list[Candidate] = []
        for c in cands:
            a_low = self._elision_strip(c.am_stripped).lower()
            k = (a_low, c.follower_char)
            if k not in seen:
                seen[k] = True
                out.append(c)
        return out

    # ------------------------------------------------------------------- classify
    def classify(self, c: Candidate, line: str) -> Decision:
        """PURE: reads ONLY *c* + the ORIGINAL *line*; never a sentinel.

        Reproduces the branch dispatch from scan_for_replacements @644-680.
        """
        # 1) language override seam (inert for BASE_POLICY)
        if self.policy.classify_special is not None:
            d = self.policy.classify_special(self, line, c)
            if d is not NOT_HANDLED:
                return Decision.BOUNDARY if d is None else d
        am_lower = self._elision_strip(c.am_stripped).lower()
        upper = self._follower_is_upper(c)  # @652
        prep = self.data.prepositive_set
        num = self.data.number_abbr_set
        # 2) the gate that LEAVES a capital-follower plain abbr as a BOUNDARY (@661 negated):
        if upper and am_lower not in prep and am_lower not in num:
            return Decision.BOUNDARY  # period stays '.'
        # 3) PREPOSITIVE branch (@663-669)
        if am_lower in prep:
            return self._classify_prepositive(c, line, am_lower)
        # 4) NUMBER branch (@613-624, @670-677)
        if am_lower in num:
            return self._classify_number(c, line, upper)
        # 5) REGULAR branch (@568/574/679)
        return Decision.PROTECT if self.RE_REGULAR.match(line, c.period_idx) else Decision.BOUNDARY

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

    def _classify_number(self, c: Candidate, line: str, upper: bool) -> Decision:
        """NUMBER branch (_replace_number_abbr @613-624, dispatch @670-677)."""
        i = c.period_idx
        if upper:
            rx = self.RE_NUM_UP_JOIN if self._leans_join else self.RE_NUM_UP_SPLIT  # @619 / @622
            return Decision.PROTECT if rx.match(line, i) else Decision.BOUNDARY
        if self.RE_NUM_QQ.match(line, i):  # @623 ?? arm + @626 placeholder
            return Decision.PLACEHOLDER
        num_low = self._num_low_pattern()
        if num_low.match(line, i):  # @623 the rest
            return Decision.PROTECT
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
                return Decision.BOUNDARY
            return Decision.PROTECT if self.RE_REGULAR.match(line, i) else Decision.BOUNDARY
        return Decision.BOUNDARY  # single-char 'p' excluded (@676)

    def _num_low_pattern(self) -> re.Pattern[str]:
        """Select the number-lower suffix: conservative join-variant for
        ``ascii_only_upper_heuristic`` policies (en_es_zh) in 'conservative'
        mode, else the Roman-only base pattern."""
        if self.policy.ascii_only_upper_heuristic and self._leans_join:
            return self.RE_NUM_LOW_JOIN
        return self.RE_NUM_LOW

    # -------------------------------------------------------- suffix selection
    def _suffix_for(self, c: Candidate, line: str, d: Decision) -> str:
        """Return the suffix pattern (sans lookbehind) that drove decision *d*.

        Used to re-anchor the global realization pass. Mirrors classify()'s branch
        selection so the SAME suffix that PROTECTed/PLACEHOLDERed is applied to
        every occurrence of this abbr on the line.
        """
        if self.policy.realize_suffix is not None:
            return self.policy.realize_suffix(self, c, line, d)
        am_lower = self._elision_strip(c.am_stripped).lower()
        upper = self._follower_is_upper(c)
        prep = self.data.prepositive_set
        num = self.data.number_abbr_set
        if am_lower in prep:
            # STARTER_AWARE / base prepositive both protect via the PREPOSITIVE suffix.
            return self.RE_PREPOSITIVE.pattern
        if am_lower in num:
            if upper:
                return self.RE_NUM_UP_JOIN.pattern if self._leans_join else self.RE_NUM_UP_SPLIT.pattern
            if d is Decision.PLACEHOLDER:
                return self.RE_NUM_QQ.pattern
            num_low = self._num_low_pattern()
            if num_low.match(line, c.period_idx):
                return num_low.pattern
            # multi-char NUMBER -> REGULAR fallthrough (@676)
            return self.RE_REGULAR.pattern
        return self.RE_REGULAR.pattern

    def _full_pattern(self, am_escaped: str, suffix: str) -> re.Pattern[str]:
        key = (am_escaped, suffix)
        pat = self._full_cache.get(key)
        if pat is None:
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

    # -------------------------------------------------------------------- rewrite
    def _collect_edits(self, line: str) -> list[Edit]:
        edits: list[Edit] = []
        for c in self.enumerate_candidates(line):
            if self.policy.candidate_filter is not None and not self.policy.candidate_filter(c, line):
                continue
            d = self.classify(c, line)  # decided ONCE from original text for this (am, char)
            if d is Decision.BOUNDARY:
                continue
            if self.policy.realize_per_occurrence:
                # Anchor the edit to THIS occurrence's own period only — never a
                # global re-anchored suffix — so position-dependent decisions
                # (russian ``ср.``) are honored per occurrence. Mirrors the legacy
                # per-match ``re.sub`` callback returning ``group()[:-1] + "∯"``.
                p = c.period_idx
                if d is Decision.PROTECT:
                    edits.append(Edit(p, p + 1, "∯", p))
                else:  # PLACEHOLDER (unused by current per-occurrence policies)
                    qq_end = (p + 1) + len(self._qq_span(line, p))
                    edits.append(Edit(p, qq_end, "∯ " + self.r._UNKNOWN_PLACEHOLDER, p))
                continue
            suffix = self._suffix_for(c, line, d)
            # Realize GLOBALLY over the line (legacy global re.sub semantics): the
            # chosen suffix regex, re-anchored with the lookbehind, applied to EVERY
            # occurrence of THIS abbr on the line. Leading-space prefix matches the
            # legacy _replace_with_escape/replace_period_of_abbr " " + txt trick.
            full = self._full_pattern(c.am_escaped, suffix)
            probe = " " + line
            for m in full.finditer(probe):
                p = m.start() - 1  # original-line period index
                if d is Decision.PROTECT:
                    edits.append(Edit(p, p + 1, "∯", p))
                else:  # PLACEHOLDER
                    qq_end = (p + 1) + len(self._qq_span(line, p))
                    edits.append(Edit(p, qq_end, "∯ " + self.r._UNKNOWN_PLACEHOLDER, p))
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
        return sorted(seen.values(), key=lambda e: (e.start, e.end))

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

        PLACEHOLDER contributes ONLY its period_idx (oracle.py:105-109).
        """
        return sorted({e.period_idx for e in self._dedup_sorted(self._collect_edits(line))})
