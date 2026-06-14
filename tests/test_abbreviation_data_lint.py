# -*- coding: utf-8 -*-
"""Behavioral data-lint for every declared abbreviation.

The four storage-shape data tests in ``test_languages.py`` only check that the
``ABBREVIATIONS`` lists are well-formed (deduped, trimmed, no single-token
trailing dot, canonical order). None of them checks that an entry actually *works*
— i.e. that the engine keeps the period after it NON-terminal. Hundreds of
declared entries silently rot because the V2 automaton + ``match_re`` +
``PeriodClassifier`` path cannot enumerate them.

This module renders each entry in a neutral lowercase-follower carrier
(``"foo <abbr>. bar baz"``) and asserts ``segment()`` keeps it joined — the
"if it's in the list, it works" contract. A lowercase follower is the easiest
possible context to protect (the base REGULAR branch's follower class is
``[a-z]``), so a failure here means the entry can *never* protect its period.

QUARANTINE (discoverable backlog)
---------------------------------
~70 declared entries fail this contract today (down from ~95: S6 made the base
``MULTI_PERIOD_ABBREVIATION_REGEX`` Unicode-aware and sentinel-aware, promoting
the ~26 non-ASCII single-final-letter multi-period initialisms out of the list).
The remaining failures are NOT bugs introduced here; they are a pre-existing,
now-*measured* gap. Rather than red CI, each known failure is listed in
``QUARANTINE`` below and converted to an ``xfail`` at runtime (``pytest.xfail`` is
unaffected by the global ``xfail_strict=true``, so a quarantined entry that later
starts working simply turns GREEN — it never XPASS-reds the suite). The allowlist
is the remaining backlog for S6's successors; promote entries out of it as they
are made to work.

The remaining failures fall into two families (see
``analysis/V2_REFACTOR_ROADMAP.md`` S5/S6):

1. **Mid-token breaks.** The entry contains structure the engine cannot carry
   through one ``match_re`` + automaton key — and which the now-Unicode base
   MULTI_PERIOD regex still does not span (it only protects single-final-letter
   ``LETTER{1,3}`` chains, never a hyphen / ``&`` / ``(`` / ``!`` / ``/`` / quote
   / inter-token space):
   - hyphenated initialisms (``c.-à-d``, ``dipl.-ing``, ``r.-v``, ``адм.-терр``);
   - ``&`` / ``(`` / ``!`` / ``/`` / quote entries (``b.&w``, ``magg.(maj)``,
     ``news!``, ``pag./p``, ``riv.dir.int."le priv``);
   - 3+ token spaced entries (``cod. proc. civ``, ``rass. avv. stato``,
     ``trav.com.ét.et lég.not``, ``т. б.``);
   - multi-letter-*final* initialisms (``κ.λπ``) that exceed the base regex's
     single-final-letter limit (kept to avoid mis-matching ``example.co.uk.``).
2. **Single-letter false positives.** A one-character NUMBER abbreviation
   (``p`` in most languages, ``s`` in Danish, ``č`` in Slovak) never protects a
   period before a plain lowercase word: the NUMBER branch only joins before a
   digit / ``(`` / ``??`` / Roman numeral, and the multi-char REGULAR fallthrough
   excludes single-character tokens. These are arguably *correct* to split (a lone
   "p." before a lowercase word is rarely an abbreviation), so they may stay
   quarantined permanently.
"""

from __future__ import annotations

import pytest

from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.segmenter import Segmenter

# Seeded quarantine allowlist: ``{code: frozenset(entries)}`` of the known
# data-lint failures. An entry here is rendered as an xfail (not a hard failure)
# when it fails; an entry NOT here that fails reds the suite immediately, so a
# newly-rotted or newly-added-but-broken abbreviation is caught at once. Keep
# this list minimal — remove an entry the moment the engine can keep it joined.
QUARANTINE: dict[str, frozenset[str]] = {
    # S6 promoted the non-ASCII multi-period initialisms (Arabic ``ا.ش.ا``/``ص.ب``,
    # Danish ``d.å``, German ``o.ä``, Greek ``μ.χ``, the single-final-letter Dutch
    # chains) out of this list once the base MULTI_PERIOD regex became Unicode and
    # sentinel-aware; what remains here is genuinely out of reach of that fix
    # (hyphenated, ``&``/``(``/``!``/``/`` / quote, 3+-token-spaced, or
    # single-letter NUMBER entries).
    "da": frozenset({"s"}),
    "de": frozenset({"c.-à-d", "dipl.-ing", "o.univ.-prof", "univ.-doz", "univ.-prof"}),
    "el": frozenset({"p", "κ.λπ"}),
    "en": frozenset({"p"}),
    "en_es_zh": frozenset({"bs. as", "ff. aa", "n. del t", "ntra. sra", "p", "rr. hh"}),
    "en_legal": frozenset({"p"}),
    "es": frozenset({"bs. as", "ff. aa", "n. del t", "ntra. sra", "p", "rr. hh"}),
    "fr": frozenset({"c.-à-d", "ch.-l", "p", "r.-v"}),
    "it": frozenset(
        {
            "cod. deont. not",
            "cod. proc. civ",
            "cod. proc. pen",
            "dig. iv",
            "estr. min",
            "magg.(maj)",
            "magg.gen.(maj.gen.)",
            "news!",
            "pag./p",
            "pagg./pp",
            "rass. avv. stato",
            "serg.magg.(sgm)",
            "ten.(lt)",
            "ten.col.(ltc)",
        }
    ),
    "ja": frozenset({"p"}),
    "kk": frozenset({"б. т.", "т. б."}),
    "mr": frozenset({"p"}),
    "nl": frozenset(
        {
            "acc.& fisc",
            "ann.ét.eur",
            "b.&w",
            "b.verg.r.b",
            "bijbl.n.bijdr",
            "bull.trim.b.dr.comp",
            "c.& f",
            "c.& f.p",
            "comm.v.en v",
            "confl.w.huwbetr",
            "harv.l.rev",
            "l'exp.-compt.b.",
            "ll.(l.)l.r",
            "l’exp.-compt.b",
            "p.& b",
            "rev.dr.étr",
            'riv.dir.int."le priv',
            "trav.com.ét.et lég.not",
            "v.& f",
            "v.toep.r.vert",
        }
    ),
    "pl": frozenset({"pod red.", "sp. z o.o"}),
    "ru": frozenset({"адм.-терр", "вост.-европ"}),
    "sk": frozenset({"č"}),
    "zh": frozenset({"p"}),
}


def _carrier(abbr: str) -> str:
    """A neutral lowercase-follower carrier for *abbr*.

    Word-boundary before the abbreviation, ``". "`` then a plain lowercase word —
    the easiest context for the REGULAR branch (follower class ``[a-z]``) to
    protect. If the engine still splits here, the entry cannot work anywhere.
    """
    return f"foo {abbr}. bar baz"


def _cases() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for code in sorted(LANGUAGE_CODES):
        for entry in LANGUAGE_CODES[code].Abbreviation.ABBREVIATIONS:
            stripped = entry.strip()
            if stripped:
                out.append((code, stripped))
    return out


@pytest.mark.parametrize(("code", "abbr"), _cases(), ids=lambda v: v)
def test_declared_abbreviation_keeps_period_joined(code: str, abbr: str) -> None:
    """A declared abbreviation must keep its period non-terminal in a neutral carrier.

    Quarantined failures (``QUARANTINE``) are converted to xfails at runtime; an
    un-quarantined failure reds the suite.
    """
    segments = Segmenter(language=code, clean=False).segment(_carrier(abbr))
    joined = len(segments) == 1
    if not joined and abbr in QUARANTINE.get(code, frozenset()):
        pytest.xfail(f"quarantined data-lint gap (S6 backlog): {code} {abbr!r} -> {segments}")
    assert joined, f"{code} {abbr!r}: declared abbreviation split its period: {segments}"


def test_quarantine_allowlist_has_no_stale_entries() -> None:
    """Every quarantined entry must still be a declared abbreviation.

    Guards the backlog against drift: if a quarantined entry is renamed or removed
    from a language's ABBREVIATIONS list, its allowlist entry must be removed too
    (otherwise the allowlist silently masks nothing).
    """
    stale: list[tuple[str, str]] = []
    for code, entries in QUARANTINE.items():
        declared = {a.strip() for a in LANGUAGE_CODES[code].Abbreviation.ABBREVIATIONS}
        for entry in entries:
            if entry not in declared:
                stale.append((code, entry))
    assert stale == [], f"stale quarantine entries (no longer declared): {stale}"
