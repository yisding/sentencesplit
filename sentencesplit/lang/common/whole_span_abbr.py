# -*- coding: utf-8 -*-
from sentencesplit.period_classifier import NOT_HANDLED, AbbrPolicy, Candidate, Decision, Edit, PeriodClassifier

# Shared whole-span abbreviation policy (Phase 5). Slovak and Bulgarian both
# overrode ONLY the regular branch of the legacy ``replace_period_of_abbr`` with a
# structurally identical rule: an UNCONDITIONAL, WHOLE-SPAN protect of a known
# abbreviation's periods.
#
#   1) UNCONDITIONAL — no follower-class lookahead. A known abbreviation's period
#      protects regardless of what follows (a capital follower is NOT a boundary
#      cue). Slovak abbreviations frequently precede a capitalized company/proper
#      name ("napr. XYZCorp"); Bulgarian keeps a single protected period here and a
#      LATER pass decides the boundary ("150 г. Саргон" stays "150 г∯ Саргон").
#   2) WHOLE-SPAN — every interior period of a spaced/compact abbreviation becomes
#      a sentinel too ("s. r. o." -> "s∯ r∯ o∯", "б.р." -> "б∯р∯"), keeping
#      multi-word company forms and Cyrillic multi-period abbreviations as one
#      token. The ASCII-only ``MULTI_PERIOD_ABBREVIATION_REGEX`` misses these
#      interiors, so the boundary regex would otherwise shatter the token.
#
# ``classify_special`` handles ONLY the regular branch (returns PROTECT
# unconditionally for a non-prepositive, non-number abbreviation; ``NOT_HANDLED``
# otherwise so the base prepositive/number trichotomy runs). ``protect_edit``
# realizes the whole-span splice; ``realize_per_occurrence`` anchors each
# word-boundary occurrence to its own span.
#
# Quirk FIXED (BC not required, plan §3, reviewed Golden-Rule-anchored): the legacy
# ``str.replace`` / unescaped-lookbehind ``re.sub`` were GLOBAL and could mutate an
# unrelated EMBEDDED / decoy occurrence on the same line. The V2 per-occurrence path
# classifies + splices only the candidates the reachability gate (word-boundary,
# ``re.escape``-d ``match_re``) actually enumerates, so the spurious
# cross-contamination is dropped. No Golden Rule exercises that case.


def _whole_span_classify_special(pc: "PeriodClassifier", line: str, c: Candidate) -> object:
    """Regular-branch override, per occurrence.

    REGULAR abbreviations PROTECT unconditionally; PREPOSITIVE/NUMBER fall through
    (``NOT_HANDLED``) to the base trichotomy, which neither language overrides.
    """
    if c.am_lower in pc.data.prepositive_set or c.am_lower in pc.data.number_abbr_set:
        return NOT_HANDLED
    return Decision.PROTECT


def _whole_span_protect_edit(pc: "PeriodClassifier", c: Candidate, line: str) -> "Edit":
    """Whole-span protect: ``<abbr>.`` -> ``<abbr with every '.' -> ∯>∯``.

    The abbreviation token occupies ``line[c.abbr_start : c.period_idx]`` (its
    original-case text on the line); the trailing period is at ``period_idx``.
    Reproduces ``abbr.replace(".", "∯") + "∯"`` over the full span
    ``[abbr_start, period_idx + 1)``. ``Candidate.abbr_start`` already excludes any
    leading elision boundary char, so no elision dance is needed here.
    """
    span_text = line[c.abbr_start : c.period_idx]  # original-case abbreviation, no trailing '.'
    replacement = span_text.replace(".", "∯") + "∯"
    return Edit(c.abbr_start, c.period_idx + 1, replacement, c.period_idx)


def whole_span_policy() -> AbbrPolicy:
    """Build the shared whole-span regular-branch abbreviation policy.

    Used by Slovak and Bulgarian, whose legacy ``replace_period_of_abbr`` overrides
    were structurally identical (unconditional whole-span PROTECT on the regular
    branch; ``NOT_HANDLED`` for prepositive/number so the base trichotomy runs).
    """
    return AbbrPolicy(
        classify_special=_whole_span_classify_special,
        protect_edit=_whole_span_protect_edit,
        realize_per_occurrence=True,
    )
