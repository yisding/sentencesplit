# -*- coding: utf-8 -*-
"""Differential oracle for the V2 abbreviation engine (DEBUGGING AID, not a gate).

Per ``analysis/ABBREVIATION_ENGINE_V2_PLAN.md`` §1.5 and §5.1, a position-level
``legacy == new`` equality check *is byte-identity in disguise*: it re-imports
the constraint the V2 effort explicitly dropped and freezes today's occasionally
buggy behavior as the spec. So this module is used only to **locate** positions
where the legacy and V2 paths protect different periods, and to **adjudicate**
each such divergence against the Golden Rules — never to require equality.

What "protected" means here
---------------------------
The thing the ``PeriodClassifier`` (V2) replaces is exactly one step:
``AbbreviationReplacer.search_for_abbreviations_in_string`` (the per-line
abbreviation-protection step invoked from ``replace()``'s per-line loop,
``abbreviation_replacer.py:365-368``). That step turns a candidate ``.`` into the
sentinel ``∯`` when the period is judged intra-abbreviation. It does NOT cover
the later passes (``replace_multi_period_abbreviations``, the a.m./p.m. passes,
the all-caps imprint pass, the standalone-``I`` pass) — those run after it and
stay unchanged in V2.

It also is NOT the upstream single-letter / possessive /
Kommanditgesellschaft rules that ``replace()`` runs *before* the per-line loop
(``abbreviation_replacer.py:359-364``); those can themselves emit ``∯`` (e.g.
``A. B.`` -> ``A∯ B∯``) but are left in place by V2. The oracle therefore
attributes a protected position to "legacy" only when the *per-line protection
step* is what turned that original ``.`` into ``∯`` — measured on the text as it
enters that step (i.e. after the upstream rules) and mapped back to the ORIGINAL
text's character indices.

Length changes
--------------
The per-line step is length-preserving except for the rare number-abbreviation
``??`` placeholder, where `` ??`` expands to `` &ᓷ&&ᓷ&`` (a known, fixed-shape
insertion). The protected period that triggers it always precedes the
placeholder, and we resync the alignment across that expansion, so protected
positions are reported correctly even when a placeholder is present on the line.
"""

from __future__ import annotations

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.languages import Language
from sentencesplit.utils import apply_rules

_SENTINEL = "∯"
_PLACEHOLDER = AbbreviationReplacer._UNKNOWN_PLACEHOLDER  # "&ᓷ&&ᓷ&"


class ClassifierUnavailable(RuntimeError):
    """Raised when the V2 classifier path is requested but not yet wired in."""


def _resolve(lang_code: str):
    """Return (language module/class, AbbreviationReplacer subclass) for *lang_code*."""
    lang = Language.get_language_code(lang_code)
    replacer_cls = getattr(lang, "AbbreviationReplacer", AbbreviationReplacer)
    return lang, replacer_cls


def _apply_upstream_rules(lang, text: str) -> str:
    """Run the pre-per-line rules ``replace()`` applies before the protection step.

    These are length-preserving (``.`` -> ``∯`` in place), so the returned text
    is index-aligned with *text* and we can map protected positions back 1:1.
    """
    return apply_rules(
        text,
        lang.PossessiveAbbreviationRule,
        lang.KommanditgesellschaftRule,
        *lang.SingleLetterAbbreviationRules.All,
    )


def _protect_line(replacer, line: str) -> str:
    """Run only the LEGACY per-line abbreviation-protection step on a single line.

    Once a language opts into the V2 classifier (``USE_PERIOD_CLASSIFIER = True``),
    ``search_for_abbreviations_in_string`` routes through the classifier. To keep
    this a genuine *differential* oracle (legacy vs new), force the legacy branch
    for this measurement by disabling the flag on this per-call replacer instance;
    the instance is discarded after the oracle runs, so nothing else is affected.
    """
    prior = replacer.USE_PERIOD_CLASSIFIER
    replacer.USE_PERIOD_CLASSIFIER = False
    try:
        return replacer.search_for_abbreviations_in_string(line)
    finally:
        replacer.USE_PERIOD_CLASSIFIER = prior


def _diff_line_positions(original_line: str, protected_line: str) -> set[int]:
    """Return offsets within *original_line* whose ``.`` became ``∯``.

    Walks both strings in lockstep. The only divergences the per-line protection
    step can introduce are:
      * ``.`` -> ``∯`` (same length) — a protected period; record its offset.
      * `` ??`` -> `` &ᓷ&&ᓷ&`` — the number-abbr placeholder; resync past it.
    Any other mismatch raises, so a silent alignment bug can never masquerade as
    "no protected positions".
    """
    positions: set[int] = set()
    i = j = 0
    n, m = len(original_line), len(protected_line)
    while i < n and j < m:
        oc = original_line[i]
        pc = protected_line[j]
        if oc == pc:
            i += 1
            j += 1
            continue
        if oc == "." and pc == _SENTINEL:
            positions.add(i)
            i += 1
            j += 1
            continue
        # Number-abbr placeholder expansion: original "??" -> "&ᓷ&&ᓷ&".
        if original_line.startswith("??", i) and protected_line.startswith(_PLACEHOLDER, j):
            i += 2
            j += len(_PLACEHOLDER)
            continue
        raise AssertionError(
            f"unexpected legacy-protection divergence at orig[{i}]={oc!r} / "
            f"prot[{j}]={pc!r}\n  original:  {original_line!r}\n  protected: {protected_line!r}"
        )
    return positions


def legacy_protect_positions(text: str, lang_code: str = "en") -> list[int]:
    """Indices in *text* whose ``.`` the LEGACY per-line protection step turns into ``∯``.

    Replays ``AbbreviationReplacer.replace()``'s upstream rules + per-line
    protection loop (``abbreviation_replacer.py:359-368``) against the current,
    unmodified engine and returns a sorted list of ORIGINAL-text character
    offsets. Works today, before any V2 code lands.
    """
    lang, replacer_cls = _resolve(lang_code)
    replacer = replacer_cls(text, lang, split_mode="balanced")

    upstream = _apply_upstream_rules(lang, text)
    # The upstream rules are length-preserving; assert it so a future rule that
    # breaks the assumption fails loudly instead of silently shifting offsets.
    if len(upstream) != len(text):
        raise AssertionError(
            f"upstream rules changed length for lang={lang_code!r}: "
            f"{len(text)} -> {len(upstream)}; oracle alignment assumption broken"
        )

    positions: set[int] = set()
    base = 0  # offset of the current line within `upstream` (== within `text`)
    # Replicate replace()'s `for line in self.text.splitlines(True)` loop.
    for line in upstream.splitlines(True):
        protected = _protect_line(replacer, line)
        for off in _diff_line_positions(line, protected):
            # `line` is index-aligned with `text` because upstream is
            # length-preserving and splitlines(True) keeps every character.
            positions.add(base + off)
        base += len(line)
    return sorted(positions)


def classifier_protect_positions(text: str, lang_code: str = "en") -> list[int]:
    """Indices in *text* whose ``.`` the V2 PeriodClassifier path protects.

    Stub until the V2 path lands. It activates only when the resolved
    ``AbbreviationReplacer`` opts in via ``USE_PERIOD_CLASSIFIER = True`` AND
    exposes a position-returning hook ``classifier_protect_positions_for_line``.
    Until then it raises :class:`ClassifierUnavailable` with a clear message so
    callers (and ``diff_positions``) fail loudly rather than silently no-op.
    """
    lang, replacer_cls = _resolve(lang_code)
    if not getattr(replacer_cls, "USE_PERIOD_CLASSIFIER", False):
        raise ClassifierUnavailable(
            f"V2 PeriodClassifier not enabled for lang={lang_code!r} "
            f"(AbbreviationReplacer.USE_PERIOD_CLASSIFIER is False / unset). "
            f"This stub activates once the classifier path is wired in."
        )
    hook = getattr(replacer_cls, "classifier_protect_positions_for_line", None)
    if hook is None:
        raise ClassifierUnavailable(
            f"USE_PERIOD_CLASSIFIER is True for lang={lang_code!r} but the "
            f"replacer exposes no `classifier_protect_positions_for_line` hook; "
            f"the oracle adapter must be implemented alongside the classifier."
        )

    replacer = replacer_cls(text, lang, split_mode="balanced")
    upstream = _apply_upstream_rules(lang, text)
    if len(upstream) != len(text):
        raise AssertionError(
            f"upstream rules changed length for lang={lang_code!r}: "
            f"{len(text)} -> {len(upstream)}; oracle alignment assumption broken"
        )
    positions: set[int] = set()
    base = 0
    for line in upstream.splitlines(True):
        for off in replacer.classifier_protect_positions_for_line(line):
            positions.add(base + off)
        base += len(line)
    return sorted(positions)


def diff_positions(text: str, lang_code: str = "en") -> tuple[list[int], list[int]]:
    """Return ``(legacy_only, new_only)`` protected-position offsets in *text*.

    ``legacy_only`` = positions the legacy path protects but the V2 path does
    not; ``new_only`` = the reverse. An empty pair means the two paths agree on
    this input (a *target* for English, never a hard requirement). Raises
    :class:`ClassifierUnavailable` until the V2 path is wired in.
    """
    legacy = set(legacy_protect_positions(text, lang_code))
    new = set(classifier_protect_positions(text, lang_code))
    return sorted(legacy - new), sorted(new - legacy)
