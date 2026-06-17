# -*- coding: utf-8 -*-
"""First-class, multi-language unit suite for the V2 ``PeriodClassifier``.

``tests/v2/test_classifier_en.py`` already covers the English (``BASE_POLICY``)
decision logic branch-by-branch. This module is the cross-language companion T4
asks for: it exercises every *policy seam* the classifier exposes through the
shipping languages that actually use it, so a regression in one language's
``AbbrPolicy`` is caught at the classifier level instead of only at ``segment()``:

* the three base classify branches (REGULAR / PREPOSITIVE / NUMBER) plus the
  capital-follower-is-boundary cue, on a non-English base-policy language;
* the ``cjk_follower_class`` arm (zh / ja regular-only, en_es_zh woven-everywhere
  with ``ascii_only_upper_heuristic``);
* ``classify_special`` + ``realize_suffix_pattern`` collapsing every branch onto
  one constant rule (Arabic bare-period protect / German "protect any period
  before whitespace, even before a capital");
* ``classify_special`` + ``protect_edit`` + ``realize_per_occurrence`` for the
  whole-span splice (Bulgarian ``б.р.`` -> ``б∯р∯``);
* the per-occurrence realization path (Russian ``ср.``: two occurrences sharing
  one dedup key that decide differently from their own original context);
* the ``post_stages`` seam (S1): the default full pipeline is inherited when a
  policy leaves it empty, German swaps in a reduced pipeline, and Kazakh appends
  an extra stage.

These read the classifier through the real per-language ``AbbreviationReplacer``
so the policy wiring (``ABBR_POLICY``) is exercised end-to-end, not mocked.
"""

from __future__ import annotations

import pytest

from sentencesplit.abbreviation_replacer import (
    DEFAULT_POST_STAGES,
    GERMAN_POST_STAGES,
)
from sentencesplit.languages import Language
from sentencesplit.period_classifier import BASE_POLICY, Decision, PeriodClassifier


def _classifier(code: str, split_mode: str = "balanced") -> PeriodClassifier:
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


# --------------------------------------------------------------------------- #
# Base trichotomy on a non-English base-policy language (Dutch rides BASE_POLICY).
# --------------------------------------------------------------------------- #
def test_dutch_rides_base_policy() -> None:
    pc = _classifier("nl")
    # Dutch does not override ABBR_POLICY, so it shares the module-level base.
    assert pc.policy is BASE_POLICY
    assert pc.policy.follower_class == "[a-z]"
    # Dutch does NOT set the capital-follower-is-boundary cue.
    assert pc.r.CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE is False


def test_dutch_regular_protect_before_lowercase() -> None:
    pc = _classifier("nl")
    # "etc" is a plain (regular) abbreviation: a lowercase follower protects it.
    assert _classify_one(pc, "appels etc. en peren hier.", "etc", "e") is Decision.PROTECT


def test_dutch_regular_boundary_before_capital_follower() -> None:
    pc = _classifier("nl")
    # The REGULAR suffix requires a LOWERCASE follower (or I / digit / opener), so a
    # capital follower is a BOUNDARY even with no capital-is-boundary cue: the cue is
    # only the discriminator for the prepositive / number arms, not the regular one.
    assert _classify_one(pc, "appels etc. En peren hier.", "etc", "E") is Decision.BOUNDARY


# --------------------------------------------------------------------------- #
# REGULAR / PREPOSITIVE / NUMBER + the capital-is-boundary cue on English. These
# mirror the EN suite but assert the cue is the discriminator between the regular
# and prepositive/number arms.
# --------------------------------------------------------------------------- #
def test_english_capital_cue_is_enabled() -> None:
    pc = _classifier("en")
    assert pc.r.CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE is True


def test_english_capital_cue_exempts_prepositive() -> None:
    pc = _classifier("en")
    # The cue's gate (classify step 2) exempts prepositive abbreviations, so a
    # capital follower after "Dr." still PROTECTs (titled name) where a plain
    # regular abbr ("Inc. They") would be a boundary.
    assert _classify_one(pc, "Dr. Smith arrived here.", "dr", "S") is Decision.PROTECT
    assert _classify_one(pc, "He joined Acme Inc. They left.", "inc", "T") is Decision.BOUNDARY


def test_english_capital_cue_exempts_number() -> None:
    pc = _classifier("en")
    # Number abbr "Vol." before a Roman numeral (capital "I") PROTECTs: the cue
    # exempts the number branch, which then matches the Roman-numeral suffix.
    assert _classify_one(pc, "Vol. IV is here.", "vol", "I") is Decision.PROTECT


# --------------------------------------------------------------------------- #
# CJK follower arm — regular-only (zh / ja).
# --------------------------------------------------------------------------- #
def test_zh_cjk_follower_regular_only_policy_shape() -> None:
    pc = _classifier("zh")
    assert pc.policy.cjk_follower_class == "[一-鿿]"
    assert pc.policy.cjk_follower_regular_only is True
    # zh inherits the base regular follower class.
    assert pc.policy.follower_class == "[a-z]"


def test_zh_cjk_follower_protects_without_space() -> None:
    pc = _classifier("zh")
    # "U.S.标准": a CJK ideograph immediately after the period (no space) protects.
    line = "U.S.标准是这样的。"
    assert pc.rewrite(line) == "U.S∯标准是这样的。"


def test_ja_cjk_follower_protects_without_space() -> None:
    pc = _classifier("ja")
    assert pc.policy.cjk_follower_regular_only is True
    line = "U.S.標準はこうです。"
    assert pc.rewrite(line) == "U.S∯標準はこうです。"


# --------------------------------------------------------------------------- #
# CJK follower woven everywhere + ascii_only_upper_heuristic (en_es_zh).
# --------------------------------------------------------------------------- #
def test_en_es_zh_policy_shape() -> None:
    pc = _classifier("en_es_zh")
    assert pc.policy.cjk_follower_class == "[㐀-鿿]"
    assert pc.policy.cjk_follower_regular_only is False  # woven into every branch
    assert pc.policy.ascii_only_upper_heuristic is True


def test_en_es_zh_cjk_follower_protects_regular_and_no_space() -> None:
    pc = _classifier("en_es_zh")
    assert pc.rewrite("etc.标准") == "etc∯标准"
    assert pc.rewrite("U.S.标准是这样的。") == "U.S∯标准是这样的。"


def test_en_es_zh_ascii_only_upper_lets_non_ascii_capital_protect() -> None:
    pc = _classifier("en_es_zh")
    # "Sr." (prepositive) before a non-ASCII capital: the ASCII-gated cue does not
    # fire, so the prepositive branch still PROTECTs (no false boundary on "Élena").
    assert _classify_one(pc, "El Sr. Élena llegó aquí.", "sr", "É") is Decision.PROTECT


# --------------------------------------------------------------------------- #
# classify_special + realize_suffix collapsing every branch (German).
# --------------------------------------------------------------------------- #
def test_german_policy_uses_classify_special_and_realize_suffix_pattern() -> None:
    pc = _classifier("de")
    assert pc.policy.classify_special is not None
    assert pc.policy.realize_suffix_pattern == r"\.(?=\s)"
    assert pc.policy.realize_suffix is None


def test_german_protects_before_capital_follower() -> None:
    pc = _classifier("de")
    # German capitalizes all nouns, so a capital follower is NOT a sentence-start
    # cue: every known abbr before whitespace PROTECTs, regardless of follower case.
    line = "Dr. med. Meyer kam an."
    assert pc.rewrite(line) == "Dr∯ med∯ Meyer kam an."


def test_german_boundary_when_no_whitespace_follower() -> None:
    pc = _classifier("de")
    # classify_special PROTECTs only before whitespace; an immediate
    # non-whitespace follower is a BOUNDARY (the suffix \.(?=\s) fails to match).
    # "z. B." -> "z" then "B."; check a known abbr followed directly by a period.
    for c in pc.enumerate_candidates("Das ist Dr.Meyer hier."):
        if pc._elision_strip(c.am_stripped).lower() == "dr":
            assert pc.classify(c, "Das ist Dr.Meyer hier.") is Decision.BOUNDARY
            break
    else:
        pytest.skip("no 'dr' candidate enumerated")


def test_arabic_policy_uses_realize_suffix_pattern() -> None:
    pc = _classifier("ar")
    # Arabic collapses every branch onto a constant bare ``\.`` realization suffix
    # named directly as a string (no wrapper Callable).
    assert pc.policy.classify_special is not None
    assert pc.policy.realize_suffix_pattern == r"\."
    assert pc.policy.realize_suffix is None


def test_realize_suffix_pattern_matches_legacy_wrapper_constant() -> None:
    # Lock the stored strings to the pre-existing compiled-pattern constants so a
    # future edit to either constant can't silently drift the global realization.
    from sentencesplit.lang import deutsch
    from sentencesplit.lang.common import arabic_script

    ar = _classifier("ar")
    de = _classifier("de")
    assert ar.policy.realize_suffix_pattern == arabic_script._AR_PROTECT_BARE.pattern
    assert de.policy.realize_suffix_pattern == deutsch._DE_PROTECT_BEFORE_WHITESPACE.pattern


# --------------------------------------------------------------------------- #
# Whole-span splice: classify_special + protect_edit + realize_per_occurrence (bg).
# --------------------------------------------------------------------------- #
def test_bulgarian_whole_span_policy_shape() -> None:
    pc = _classifier("bg")
    assert pc.policy.classify_special is not None
    assert pc.policy.protect_edit is not None
    assert pc.policy.realize_per_occurrence is True


def test_bulgarian_whole_span_protects_every_interior_period() -> None:
    pc = _classifier("bg")
    # The whole-span protect splices EVERY interior period of a multi-period
    # Cyrillic abbreviation, not just the trailing one.
    assert pc.rewrite("Това е б.р. текст") == "Това е б∯р∯ текст"
    # protect_positions reports every period the whole-span edit sentinelizes.
    line = "Това е б.р. текст"
    first = line.index("б.р.")
    assert pc.protect_positions(line) == [first + 1, first + 3]


def test_bulgarian_prepositive_falls_through_to_base_trichotomy() -> None:
    pc = _classifier("bg")
    # classify_special returns NOT_HANDLED for prepositive/number abbreviations, so
    # the base trichotomy runs; here a regular abbr is unconditionally PROTECTed
    # even before a capital follower (no capital-is-boundary cue for Bulgarian).
    assert _classify_one(pc, "Това е напр. Текст тук.", "напр", "Т") is Decision.PROTECT


# --------------------------------------------------------------------------- #
# Per-occurrence realization path (Russian ср.).
# --------------------------------------------------------------------------- #
def test_russian_policy_is_per_occurrence() -> None:
    pc = _classifier("ru")
    assert pc.policy.classify_special is not None
    assert pc.policy.realize_per_occurrence is True


def test_russian_same_key_occurrences_decide_independently() -> None:
    # The per-occurrence path is REQUIRED here: two "ср." share one dedup key
    # ('ср', 'А') yet must decide differently from their own original context.
    # The global per-unit model would collapse them; realize_per_occurrence keeps
    # both, anchoring each edit to its own period.
    pc = _classifier("ru", split_mode="aggressive")
    line = "Ср. Андрей и Капитал. Текст ср. Андрей."
    cands = [c for c in pc.enumerate_candidates(line) if pc._elision_strip(c.am_stripped).lower() == "ср"]
    assert len(cands) == 2  # both occurrences kept (no global dedup)
    keys = {(pc._elision_strip(c.am_stripped).lower(), c.follower_char) for c in cands}
    assert keys == {("ср", "А")}  # ... and they share ONE dedup key
    decisions = [pc.classify(c, line) for c in sorted(cands, key=lambda c: c.period_idx)]
    assert decisions == [Decision.BOUNDARY, Decision.PROTECT]  # decided independently
    # The rewrite protects only the second (embedded) occurrence's period.
    assert pc.rewrite(line) == "Ср. Андрей и Капитал. Текст ср∯ Андрей."
    assert pc.protect_positions(line) == [line.index("ср.", line.index("Текст")) + 2]


# --------------------------------------------------------------------------- #
# post_stages seam (S1).
# --------------------------------------------------------------------------- #
def _replacer(code: str):
    lang = Language.get_language_code(code)
    return lang.AbbreviationReplacer("x", lang)


@pytest.mark.parametrize("code", ["en", "en_legal", "zh", "ja", "en_es_zh", "ru", "bg"])
def test_empty_post_stages_inherits_default(code: str) -> None:
    # A policy that leaves post_stages empty inherits the historical full sequence.
    r = _replacer(code)
    assert not r._period_classifier().policy.post_stages
    assert r._post_stages() is DEFAULT_POST_STAGES


def test_default_post_stage_names_and_order() -> None:
    names = [s.__name__ for s in DEFAULT_POST_STAGES]
    assert names == [
        "_stage_multi_period",
        "_stage_compact_ampm",
        "_stage_uppercase_initialism",
        "_stage_allcaps_imprint",
        "_stage_ampm_rules",
        "_stage_standalone_i",
    ]


def test_german_swaps_in_reduced_post_stages() -> None:
    r = _replacer("de")
    assert r._period_classifier().policy.post_stages == GERMAN_POST_STAGES
    assert r._post_stages() is GERMAN_POST_STAGES
    # German's reduced pipeline: multi-period + ASCII-only a.m./p.m. (no compact-ampm
    # / uppercase-initialism / allcaps-imprint / standalone-I).
    assert [s.__name__ for s in r._post_stages()] == [
        "_stage_multi_period",
        "_stage_ampm_rules_ascii_only",
    ]


def test_kazakh_appends_extra_post_stage() -> None:
    r = _replacer("kk")
    stages = r._post_stages()
    # Kazakh rides the default sequence and appends ONE extra paren-protection pass.
    assert tuple(stages[: len(DEFAULT_POST_STAGES)]) == DEFAULT_POST_STAGES
    assert len(stages) == len(DEFAULT_POST_STAGES) + 1
    assert stages[-1].__name__ == "_kk_protect_before_parenthesis"
