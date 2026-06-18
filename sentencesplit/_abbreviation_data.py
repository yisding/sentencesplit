# -*- coding: utf-8 -*-
from __future__ import annotations

import re

from sentencesplit._aho_corasick import AhoCorasickAutomaton


class _AbbreviationData:
    """Pre-computed abbreviation data for a language, cached per Abbreviation class."""

    __slots__ = (
        "abbreviations",
        "abbr_set",
        "prepositive_set",
        "number_abbr_set",
        "automaton",
        "elision_chars",
        "boundary_class",
        # Persistent cache of PeriodClassifier instances keyed by
        # ``(id(policy), split_mode, replacer_cls)``. The classifier's compiled
        # ``RE_*`` suffix patterns and its ``_full_cache`` are line-independent and
        # depend only on ``(policy, split_mode, data)`` — all immutable for a given
        # ``_AbbreviationData`` — so reusing one classifier across the per-call
        # ``AbbreviationReplacer`` instances avoids recompiling ~9 regexes and
        # rebuilding the full-pattern cache on every ``segment()`` call. The
        # replacer CLASS is part of the key because two replacer classes can share
        # one ``_AbbreviationData`` (e.g. English and Urdu both use
        # ``Standard.Abbreviation``) yet differ in the class-level flags the
        # classifier reads (``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE`` …); keying by
        # class keeps each its own classifier. Published after full construction
        # under ``AbbreviationReplacer._cache_lock``.
        "_classifier_cache",
    )

    def __init__(self, lang_abbreviation_class):
        raw = lang_abbreviation_class.ABBREVIATIONS
        elision = getattr(lang_abbreviation_class, "ELISION_CHARACTERS", "")
        self.elision_chars = elision
        if elision:
            escaped_elision = re.escape(elision)
            self.boundary_class = rf"\s{escaped_elision}"
        else:
            self.boundary_class = r"\s"
        sorted_abbrs = sorted(raw, key=len, reverse=True)
        self.abbreviations = []
        self.automaton = AhoCorasickAutomaton()
        for idx, abbr in enumerate(sorted_abbrs):
            stripped = abbr.strip()
            stripped_lower = stripped.lower()
            escaped = re.escape(stripped)
            # Pre-compile the word-boundary-prefixed match pattern for this abbr.
            if elision:
                match_re = re.compile(r"(?:^|\s|\r|\n|[{ec}]){esc}".format(ec=escaped_elision, esc=escaped), re.IGNORECASE)
            else:
                match_re = re.compile(r"(?:^|\s|\r|\n){}".format(escaped), re.IGNORECASE)
            self.abbreviations.append(
                (
                    stripped,
                    stripped_lower,
                    escaped,
                    match_re,
                )
            )
            # Add the trailing period to the automaton key. search_for_abbreviations
            # only ever acts on an abbreviation when it occurs at a word boundary
            # *followed by a period*; any such occurrence contains the substring
            # "<abbr>.", so keying on "<abbr>." is a byte-identical pre-filter that
            # skips the per-abbreviation full-text finditer for abbreviations whose
            # bare form merely appears inside other words (e.g. "al" in "called",
            # "no" in "no one") with no following period — the dominant cost on
            # real prose, where common short abbreviations match everywhere.
            #
            # Exception: the automaton is searched on ``text.lower()`` and U+0130
            # 'İ' is the only Unicode char whose .lower() changes length ('İ' ->
            # 'i' + U+0307 combining dot). An occurrence ending in 'İ' followed by
            # a period lowers to '...i̇.', so the "<abbr>." key (e.g. "vi.") would
            # not match. Abbreviations ending in 'i' therefore keep the bare key
            # (the original, always-correct behavior).
            key = stripped_lower if stripped_lower.endswith("i") else stripped_lower + "."
            self.automaton.add_pattern(key, idx)
        self.automaton.build()
        self.abbr_set = frozenset(a.strip().lower() for a in raw)
        self.prepositive_set = frozenset(a.lower() for a in lang_abbreviation_class.PREPOSITIVE_ABBREVIATIONS)
        self.number_abbr_set = frozenset(a.lower() for a in lang_abbreviation_class.NUMBER_ABBREVIATIONS)
        self._classifier_cache: dict[tuple[int, str, type], object] = {}
