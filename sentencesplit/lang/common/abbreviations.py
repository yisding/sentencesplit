# -*- coding: utf-8 -*-
"""Canonical storage form for per-language abbreviation lists.

Lives in its own module (not ``__init__``/``standard``) so any language module —
including ``Standard`` itself — can import it without an import cycle.
"""

from __future__ import annotations


def canonical_abbreviations(*lists: list[str]) -> list[str]:
    """Return the canonical stored form for an ABBREVIATIONS list.

    The canonical form is ``sorted(set(...))`` over the lowercased entries: a
    one-time normalization that lowercases, de-duplicates, and sorts. Adopting it
    as the stored form (mirroring the pattern already used by ``en_legal`` and
    ``en_es_zh``) keeps every list dedup-free and ordering-stable, and lets a lint
    (``tests/test_languages.py``) assert each list equals its canonical form so a
    future non-canonical addition is caught.

    Lowercasing is behavior-neutral for the V2 engine: the Aho-Corasick automaton
    keys on ``stripped.lower()``, ``match_re`` is ``re.IGNORECASE``, and the
    ``abbr_set``/``prepositive_set``/``number_abbr_set`` are all lowercased — so an
    entry's stored case never reaches a behavioral decision. Accepts one or more
    lists so callers that merge multiple sources (greek, en_legal, en_es_zh) get
    the canonical union directly.
    """
    return sorted({entry.lower() for entries in lists for entry in entries})
