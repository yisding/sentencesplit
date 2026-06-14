# -*- coding: utf-8 -*-
"""Differential oracle for the V2 abbreviation engine (DEBUGGING AID, not a gate).

Per ``analysis/ABBREVIATION_ENGINE_V2_PLAN.md`` §1.5 and §5.1, a position-level
``legacy == new`` equality check *is byte-identity in disguise*: it re-imports
the constraint the V2 effort explicitly dropped and freezes today's occasionally
buggy behavior as the spec. So this module is used only to **locate** positions
where the legacy and V2 paths protect different periods, and to **adjudicate**
each such divergence against the Golden Rules — never to require equality.

The legacy per-line protection engine itself was deleted at Phase 6 (cutover);
the ``PeriodClassifier`` is now the sole path. The oracle already served its
purpose (English parity was proven before the cutover), so ``legacy`` here is a
**frozen snapshot** of the positions the retired legacy engine protected on a
fixed corpus, captured while it was still live. The classifier-vs-legacy parity
checks therefore assert the classifier reproduces that historical output without
re-running (or depending on) any deleted code.

What "protected" means here
---------------------------
The thing the ``PeriodClassifier`` (V2) replaces is exactly one step:
``AbbreviationReplacer.search_for_abbreviations_in_string`` (the per-line
abbreviation-protection step invoked from ``replace()``'s per-line loop,
``abbreviation_replacer.py``). That step turns a candidate ``.`` into the
sentinel ``∯`` when the period is judged intra-abbreviation. It does NOT cover
the later passes (``replace_multi_period_abbreviations``, the a.m./p.m. passes,
the all-caps imprint pass, the standalone-``I`` pass) — those run after it and
stay unchanged in V2.

It also is NOT the upstream single-letter / possessive /
Kommanditgesellschaft rules that ``replace()`` runs *before* the per-line loop;
those can themselves emit ``∯`` (e.g. ``A. B.`` -> ``A∯ B∯``) but are left in
place by V2. The frozen snapshot below therefore attributes a protected position
to "legacy" only when the *per-line protection step* was what turned that
original ``.`` into ``∯`` — measured on the text as it entered that step (i.e.
after the upstream rules) and mapped back to the ORIGINAL text's character
indices.

Length changes
--------------
The per-line step is length-preserving except for the rare number-abbreviation
``??`` placeholder, where `` ??`` expands to `` &ᓷ&&ᓷ&`` (a known, fixed-shape
insertion). The protected period that triggers it always precedes the
placeholder, and the classifier-side adapter resyncs the alignment across that
expansion, so protected positions are reported correctly even when a placeholder
is present on the line.
"""

from __future__ import annotations

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.languages import Language
from sentencesplit.utils import apply_rules

_SENTINEL = "∯"
_PLACEHOLDER = AbbreviationReplacer._UNKNOWN_PLACEHOLDER  # "&ᓷ&&ᓷ&"


# Frozen snapshot of the protected-period offsets the (now-deleted) legacy
# per-line protection engine produced, captured in balanced split_mode while the
# engine was still live (Phase-6 cutover). Keyed by (lang_code, text). This is
# the historical "legacy" reference the classifier-parity checks compare against;
# it intentionally encodes today's known-good English output as a regression
# anchor, NOT a hard equality requirement for every input.
_LEGACY_SNAPSHOT: dict[tuple[str, str], list[int]] = {
    ("ar", "هذا مثل ذلك. وهكذا."): [],
    ("bg", "Това е напр. важно. Г-н Иванов дойде."): [],
    ("de", "Das ist z.B. wichtig. Hr. Müller kam am 5. Mai."): [11],
    ("en", "Dr. Smith met Sen. Jones. See No. 5 and Vol. IV. The 9th Cir. reversed."): [2, 17, 32, 43],
    ("en", "Dr. Smith met Sen. Jones. The U.S. agreed."): [2, 17, 33],
    ("en", "Line one with etc. trailing.\nLine two has Dr. Adams here."): [17, 44],
    ("en", "See No. ?? for details."): [6],
    ("en", "The U.S.A. is large."): [],
    ("en_legal", "Dr. Smith met Sen. Jones. See No. 5 and Vol. IV. The 9th Cir. reversed."): [2, 17, 32, 43, 60],
    ("en_legal", "See Bankr. Court. The 9th Cir. reversed. Cf. id. at 5."): [9, 29, 47],
    ("fr", "C'est M. Dupont. Voir p. 5 svp."): [23],
    ("it", "Il Sig. Rossi è qui. Vedi p. 10."): [6, 27],
    ("kk", "Бұл мысалы. Қараңыз 5-бет."): [],
    ("kk", "Бұл мысалы. Қараңыз 5-бет. См. рис. 3 ниже."): [],
    ("nl", "Dhr. Jansen kwam. Zie blz. 3."): [25],
    ("ru", "Это рус. Большой текст. См. рис. 3 ниже."): [],
    ("sk", "To je napr. dôležité. Pán Dr. Novák prišiel."): [10, 28],
    ("zh", "这是中文。Dr. Smith 来了。"): [],
}


class ClassifierUnavailable(RuntimeError):
    """Raised when the V2 classifier path is requested but not available."""


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


def legacy_protect_positions(text: str, lang_code: str = "en") -> list[int]:
    """Indices in *text* the (retired) LEGACY per-line protection step protected.

    Reads from the FROZEN snapshot captured before the legacy engine was deleted
    (Phase-6 cutover). The snapshot is keyed by ``(lang_code, text)``; an input
    that is not in the snapshot raises :class:`KeyError` (the snapshot is a closed
    corpus — add the input + its captured positions to ``_LEGACY_SNAPSHOT`` to
    extend it, do not silently return ``[]``).
    """
    key = (lang_code, text)
    if key not in _LEGACY_SNAPSHOT:
        raise KeyError(
            f"no frozen legacy snapshot for {key!r}; the legacy engine was deleted "
            f"at the Phase-6 cutover, so positions can no longer be computed live. "
            f"Add the input and its captured positions to oracle._LEGACY_SNAPSHOT."
        )
    return list(_LEGACY_SNAPSHOT[key])


def classifier_protect_positions(text: str, lang_code: str = "en") -> list[int]:
    """Indices in *text* whose ``.`` the V2 PeriodClassifier path protects.

    Activates when the resolved ``AbbreviationReplacer`` exposes the
    position-returning hook ``classifier_protect_positions_for_line``; raises
    :class:`ClassifierUnavailable` otherwise so callers fail loudly.
    """
    lang, replacer_cls = _resolve(lang_code)
    hook = getattr(replacer_cls, "classifier_protect_positions_for_line", None)
    if hook is None:
        raise ClassifierUnavailable(
            f"the resolved replacer for lang={lang_code!r} exposes no "
            f"`classifier_protect_positions_for_line` hook; the oracle adapter must "
            f"be implemented alongside the classifier."
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

    ``legacy_only`` = positions the frozen legacy snapshot protects but the V2
    path does not; ``new_only`` = the reverse. An empty pair means the classifier
    reproduces the historical legacy output on this input (a *target* for
    English, never a hard requirement). Raises :class:`KeyError` for an input
    absent from the frozen snapshot.
    """
    legacy = set(legacy_protect_positions(text, lang_code))
    new = set(classifier_protect_positions(text, lang_code))
    return sorted(legacy - new), sorted(new - legacy)
