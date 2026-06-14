# -*- coding: utf-8 -*-
"""Focused unit tests for the V2 English ``PeriodClassifier`` decision logic.

These exercise each branch of ``classify`` in isolation (REGULAR / PREPOSITIVE /
NUMBER, with the upper/Roman/?? sub-cases and the multi-char number -> regular
fallthrough), the candidate enumeration reachability gate, the dedup +
global-per-unit realization, the PLACEHOLDER edit shape, and the ``_rebuild``
non-overlap guard. The maintainability deliverable of Phase 2 is that each
per-period decision is unit-testable without driving the whole pipeline.
"""

from __future__ import annotations

import pytest

from sentencesplit.languages import Language
from sentencesplit.period_classifier import BASE_POLICY, Decision, Edit, PeriodClassifier


def _classifier(code: str = "en", split_mode: str = "balanced") -> PeriodClassifier:
    lang = Language.get_language_code(code)
    replacer = lang.AbbreviationReplacer("x", lang, split_mode=split_mode)
    return replacer._period_classifier()


def _classify_one(pc: PeriodClassifier, line: str, abbr_lower: str, follower: str) -> Decision:
    """Classify the candidate for *abbr_lower* with the given *follower* char on *line*."""
    for c in pc.enumerate_candidates(line):
        a_low = pc._elision_strip(c.am_stripped).lower()
        if a_low == abbr_lower and c.follower_char == follower:
            return pc.classify(c, line)
    raise AssertionError(f"no candidate for ({abbr_lower!r}, {follower!r}) on {line!r}")


# --------------------------------------------------------------- REGULAR branch
def test_regular_protect_before_lowercase() -> None:
    pc = _classifier()
    # "Dr." here is prepositive in English; use a regular abbr ("etc") instead.
    assert _classify_one(pc, "etc. and so on here.", "etc", "a") is Decision.PROTECT


def test_regular_boundary_before_capital() -> None:
    pc = _classifier()
    # "Inc." is a regular abbr (not prepositive/number); a capital follower with
    # CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE leaves it a BOUNDARY.
    assert _classify_one(pc, "He works for Google Inc. They left.", "inc", "T") is Decision.BOUNDARY


def test_regular_protect_before_lowercase_follower_inc() -> None:
    pc = _classifier()
    assert _classify_one(pc, "He works for Google Inc. and likes it.", "inc", "a") is Decision.PROTECT


# ------------------------------------------------------------ PREPOSITIVE branch
def test_prepositive_protect_before_capital() -> None:
    pc = _classifier()
    # "Dr." is prepositive: it protects even before a capital follower (titled name).
    assert _classify_one(pc, "Dr. Smith arrived here.", "dr", "S") is Decision.PROTECT


def test_prepositive_protect_before_lowercase() -> None:
    pc = _classifier()
    assert _classify_one(pc, "Sen. jones spoke today.", "sen", "j") is Decision.PROTECT


def test_prepositive_blocklist_st_boundary_in_aggressive() -> None:
    pc = _classifier(split_mode="aggressive")
    # "st" is in AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST: aggressive => BOUNDARY.
    assert _classify_one(pc, "He lives on Main St. The road ends.", "st", "T") is Decision.BOUNDARY


def test_prepositive_blocklist_st_protected_in_balanced() -> None:
    pc = _classifier(split_mode="balanced")
    # Outside aggressive, the blocklist does not fire; "St." stays protected.
    assert _classify_one(pc, "He lives on Main St. The road ends.", "st", "T") is Decision.PROTECT


# ----------------------------------------------------- STARTER_AWARE (en_legal)
def test_starter_aware_boundary_before_sentence_start() -> None:
    pc = _classifier("en_legal", split_mode="aggressive")
    # "Cir." (starter-aware prepositive) before a likely sentence start => BOUNDARY.
    assert _classify_one(pc, "The 9th Cir. The panel reversed.", "cir", "T") is Decision.BOUNDARY


def test_starter_aware_protect_before_colon_numbered() -> None:
    pc = _classifier("en_legal", split_mode="aggressive")
    # A ':' immediately after the starter-aware prepositive period forces PROTECT
    # (the legacy callback's first arm), even in aggressive mode.
    assert _classify_one(pc, "Bankr.:12 was filed.", "bankr", "") is Decision.PROTECT


def test_starter_aware_protect_before_lowercase_continuation() -> None:
    pc = _classifier("en_legal", split_mode="aggressive")
    # A lowercase follower is not a likely sentence start, so the starter-aware
    # prepositive stays PROTECTED (continuation reading).
    assert _classify_one(pc, "The bankr. court ruled today.", "bankr", "c") is Decision.PROTECT


# ----------------------------------------------------------------- NUMBER branch
def test_number_protect_before_digit() -> None:
    pc = _classifier()
    assert _classify_one(pc, "See No. 5 for details.", "no", "5") is Decision.PROTECT


def test_number_protect_before_roman() -> None:
    pc = _classifier()
    assert _classify_one(pc, "Vol. IV is here.", "vol", "I") is Decision.PROTECT


def test_number_boundary_before_capital_word() -> None:
    pc = _classifier()
    # "No." before a capital word (not digit/Roman) is a real boundary.
    assert _classify_one(pc, "No. The answer is no.", "no", "T") is Decision.BOUNDARY


def test_number_placeholder_before_qq() -> None:
    pc = _classifier()
    assert _classify_one(pc, "See No. ?? for details.", "no", "?") is Decision.PLACEHOLDER


def test_number_protect_before_paren() -> None:
    pc = _classifier()
    # "p. (" -> protect (number-abbr lower suffix \s+\().
    assert _classify_one(pc, "According to the report (see p. (a)).", "p", "(") is Decision.PROTECT


def test_number_multichar_regular_fallthrough() -> None:
    pc = _classifier()
    # multi-char number abbr "pp" before lowercase falls through to REGULAR.
    assert _classify_one(pc, "Read pp. and stop.", "pp", "a") is Decision.PROTECT


# ------------------------------------------------------ enumerate / reachability
def test_enumerate_skips_period_less_occurrence() -> None:
    pc = _classifier("en_legal")  # "cir" is an en_legal abbreviation
    # "Cir held" (no period) must not produce a candidate; only "Cir." does.
    line = "The Cir held that the Cir. reversed."
    cands = [c for c in pc.enumerate_candidates(line) if pc._elision_strip(c.am_stripped).lower() == "cir"]
    # exactly one candidate, at the period that exists
    assert len(cands) == 1
    assert line[cands[0].period_idx] == "."


def test_enumerate_dedup_by_abbr_and_follower() -> None:
    pc = _classifier()
    # Two "No. <digit>" occurrences with the same follower char class but different
    # actual chars are distinct followers; same exact follower dedups to one unit.
    line = "See No. 5 and No. 5 again."
    cands = [c for c in pc.enumerate_candidates(line) if pc._elision_strip(c.am_stripped).lower() == "no"]
    assert len(cands) == 1  # (no, '5') deduped to one classify-unit


# -------------------------------------------------- global-per-unit realization
def test_global_realization_protects_every_occurrence() -> None:
    pc = _classifier()
    # One classify decision for ("etc", "a") must protect BOTH "etc." occurrences.
    line = "etc. and more etc. and so on."
    out = pc.rewrite(line)
    assert out == "etc∯ and more etc∯ and so on."


def test_mixed_follower_only_protects_matching_suffix() -> None:
    pc = _classifier()
    # "Inc. and" protects (lowercase follower); "Inc. They" stays a boundary.
    line = "ABC Inc. and DEF Inc. They left."
    out = pc.rewrite(line)
    assert out == "ABC Inc∯ and DEF Inc. They left."


# ------------------------------------------------------------- PLACEHOLDER shape
def test_placeholder_edit_shape() -> None:
    pc = _classifier()
    line = "See No. ?? for details."
    out = pc.rewrite(line)
    placeholder = pc.r._UNKNOWN_PLACEHOLDER
    assert out == f"See No∯ {placeholder} for details."
    # protect_positions reports ONLY the period index.
    positions = pc.protect_positions(line)
    assert positions == [line.index("No.") + 2]


# --------------------------------------------------------- _rebuild non-overlap
def test_rebuild_applies_sorted_edits() -> None:
    line = "abXcdYef"
    edits = [Edit(2, 3, "∯", 2), Edit(5, 6, "∯", 5)]
    assert PeriodClassifier._rebuild(line, edits) == "ab∯cdYef".replace("Y", "∯")


def test_rebuild_overlap_asserts() -> None:
    line = "abcdef"
    edits = [Edit(1, 3, "X", 1), Edit(2, 4, "Y", 2)]  # overlapping
    with pytest.raises(AssertionError):
        PeriodClassifier._rebuild(line, edits)


# --------------------------------------------------------------- policy / wiring
def test_english_uses_base_policy() -> None:
    pc = _classifier()
    assert pc.policy is BASE_POLICY
    assert pc.policy.follower_class == "[a-z]"


def test_classifier_reuses_same_abbreviation_data() -> None:
    lang = Language.get_language_code("en")
    replacer = lang.AbbreviationReplacer("x", lang)
    pc = replacer._period_classifier()
    assert pc.data is replacer._data  # never rebuild the automaton/keys
