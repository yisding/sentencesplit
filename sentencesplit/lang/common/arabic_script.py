# -*- coding: utf-8 -*-
import re

from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.period_classifier import AbbrPolicy, Candidate, Decision, PeriodClassifier
from sentencesplit.utils import Rule

# Arabic / Persian (Phase 5): the legacy
# ``ArabicScriptProfile.AbbreviationReplacer`` overrode ``scan_for_replacements``
# with a SINGLE rule, ``re.sub(r"(?<={re.escape(am)})\.", "∯", txt)``, bypassing
# the base prepositive / number / regular trichotomy entirely. The effective
# behavior: PROTECT a known abbreviation's period whenever the abbreviation sits
# at a word boundary, REGARDLESS of the follower (a BARE ``\.`` suffix — any
# follower, including end-of-line, a non-space char, or a capital). Arabic script
# has no letter case, so there is no capital-follower boundary cue to consult;
# every matched abbreviation's period is non-terminal. Both ``ar`` and ``fa`` use
# this profile; Persian additionally inherits the full English abbreviation lists
# (``Standard.Abbreviation`` — including prepositive/number entries like ``e.g``),
# so the bare-protect applies uniformly to all of them, never the trichotomy.
# ``classify_special`` replaces every branch (always PROTECT); ``realize_suffix``
# pins the global realization pass to the same bare ``\.`` so PROTECT is realized
# over every occurrence with the rule that decided it.
#
# Already-correct (not a quirk fix): the legacy rule escaped ``am`` before
# interpolation (the only Arabic-script override that did — see
# tests/regression/test_arabic_script_abbreviation_metachar.py), so a dotted
# abbreviation like ``e.g`` did not wildcard-match an unrelated ``egg.``. The V2
# path uses ``data.abbreviations[idx][2]`` (the pre-built ``re.escape``) for the
# lookbehind in ``_full_pattern``, so the literal ``.`` stays escaped and the same
# regression case keeps splitting.
_AR_PROTECT_BARE = re.compile(r"\.")


def _ar_classify_special(pc: "PeriodClassifier", line: str, c: Candidate) -> object:
    """Arabic / Persian: every candidate period PROTECTs (bare ``\\.``).

    Reproduces ``ArabicScriptProfile.AbbreviationReplacer.scan_for_replacements``
    (one rule, all branches collapsed, any follower). The candidate is already a
    known ``<abbr>.`` at a word boundary (enumeration's reachability gate), so the
    decision is unconditionally PROTECT.
    """
    return Decision.PROTECT


def _ar_realize_suffix(pc: "PeriodClassifier", c: Candidate, line: str, d: "Decision") -> str:
    """Arabic / Persian global-realization suffix: bare ``\\.`` for every PROTECT."""
    return _AR_PROTECT_BARE.pattern


AR_POLICY = AbbrPolicy(
    classify_special=_ar_classify_special,
    realize_suffix=_ar_realize_suffix,
)


class ArabicScriptProfile:
    """Shared hooks for Arabic-script languages (Arabic, Persian).

    Mixed in before ``Common, Standard`` so it provides the colon boundary rule
    (protecting ``10:30``-style times) and an abbreviation replacer that protects
    the period after a matched abbreviation. Languages still set their own
    ``Punctuations`` and ``SENTENCE_BOUNDARY_REGEX``. Neither language treats the
    Arabic comma ``،`` as a sentence terminator, so no comma rule is needed.
    """

    # Rubular: http://rubular.com/r/RX5HpdDIyv
    ReplaceColonBetweenNumbersRule = Rule(r"(?<=\d):(?=\d)", "♭")

    class AbbreviationReplacer(AbbreviationReplacer):
        # V2 single-pass classifier (Phase 5). ``AR_POLICY`` reproduces the legacy
        # bare-period protect (any follower) as an ``AbbrPolicy`` hook: the matched
        # abbreviation occurs at a word boundary and its period is always
        # non-terminal (Arabic script has no letter case, so no capital-follower
        # cue). The pre-escaped abbreviation in the classifier's lookbehind keeps a
        # dotted form like "e.g" from wildcard-matching an unrelated "egg."
        # (tests/regression/test_arabic_script_abbreviation_metachar.py).
        ABBR_POLICY = AR_POLICY
