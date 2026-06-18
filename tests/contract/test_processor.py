# -*- coding: utf-8 -*-
"""Dedicated unit suite for ``processor.Processor``'s two pipeline phase lists.

``Processor`` organizes its work into two explicit pipelines:

* ``_text_processing_phases()`` — newline normalization, list-item markers,
  abbreviation replacement, (optional CJK abbreviation rules), numbers,
  continuous punctuation, numeric refs, special-token protection;
* ``_boundary_processing_phases()`` — terminal marker, exclamation words,
  between-punctuation, double-punctuation, quotation-punctuation, list parens.

The phase lists are the contract every per-language ``Processor`` override and the
``process()`` / ``process_text()`` drivers depend on. This suite pins that contract
at the level that actually matters and stays robust to harmless refactors:

* **Membership** of each pipeline (which phases are present), as an unordered set —
  not an exact ``__name__`` tuple, so renaming/reordering an unrelated phase does
  not red the suite. Ordering correctness is covered behaviorally by the snapshot
  and Golden-Rule suites.
* **Wiring** of the conditional CJK abbreviation phase: present for CJK profiles,
  absent otherwise. This is a plant-a-regression guard — dropping the phase from
  the pipeline fails here. (The base initials logic happens to subsume the phase's
  effect on ``segment()`` output today, so the wiring cannot be guarded via
  ``segment()`` output; it is guarded at the pipeline level instead, with the
  phase's own transformation pinned by a behavioral unit test below.)
* **Shape**: each phase is a callable ``str -> str`` bound to the live instance.
* **Behavior** of the load-bearing individual phases and the drivers.
"""

from __future__ import annotations

import pytest

from sentencesplit.languages import Language
from sentencesplit.processor import Processor

# Languages WITHOUT CJK abbreviation rules (base text pipeline).
_NON_CJK = ["en", "en_legal", "de", "fr", "ru", "bg", "nl"]
# Languages WITH CJK abbreviation rules (text pipeline grows the CJK phase).
_CJK = ["zh", "ja", "en_es_zh"]

# Expected pipeline membership as unordered sets (NOT exact-ordered tuples).
_BASE_TEXT_PHASE_NAMES = {
    "_normalize_newlines",
    "_mark_list_item_boundaries",
    "replace_abbreviations",
    "replace_numbers",
    "replace_continuous_punctuation",
    "replace_periods_before_numeric_references",
    "_protect_special_tokens",
}
_BOUNDARY_PHASE_NAMES = {
    "_ensure_terminal_marker",
    "_apply_exclamation_word_rules",
    "between_punctuation",
    "_apply_double_punctuation_rules",
    "_apply_quotation_punctuation_rules",
    "_replace_list_parens",
}
_CJK_PHASE = "_apply_cjk_abbreviation_rules"


def _processor(code: str, text: str = "x") -> Processor:
    return Processor(text, Language.get_language_code(code))


def _phase_names(phases) -> list[str]:
    return [p.__name__ for p in phases]


# --------------------------------------------------------------------------- #
# Pipeline membership (unordered).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", _NON_CJK)
def test_non_cjk_text_pipeline_membership(code: str) -> None:
    p = _processor(code)
    assert not p.profile.cjk_abbreviation_rules
    assert set(_phase_names(p._text_processing_phases())) == _BASE_TEXT_PHASE_NAMES


@pytest.mark.parametrize("code", _CJK)
def test_cjk_text_pipeline_adds_exactly_the_cjk_phase(code: str) -> None:
    p = _processor(code)
    assert p.profile.cjk_abbreviation_rules  # the conditional phase fires
    names = set(_phase_names(p._text_processing_phases()))
    # The CJK pipeline is the base pipeline plus exactly the CJK abbreviation phase.
    assert names == _BASE_TEXT_PHASE_NAMES | {_CJK_PHASE}


@pytest.mark.parametrize("code", _NON_CJK + _CJK)
def test_boundary_pipeline_membership(code: str) -> None:
    p = _processor(code)
    assert set(_phase_names(p._boundary_processing_phases())) == _BOUNDARY_PHASE_NAMES


# --------------------------------------------------------------------------- #
# CJK abbreviation phase: wiring (plant-a-regression guard) + behavior.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", _CJK)
def test_cjk_abbreviation_phase_is_wired_into_text_pipeline(code: str) -> None:
    # If the CJK abbreviation phase is dropped from the text pipeline, this fails.
    assert _CJK_PHASE in _phase_names(_processor(code)._text_processing_phases())


@pytest.mark.parametrize("code", _NON_CJK)
def test_cjk_abbreviation_phase_absent_for_non_cjk(code: str) -> None:
    assert _CJK_PHASE not in _phase_names(_processor(code)._text_processing_phases())


@pytest.mark.parametrize("code", _CJK)
def test_cjk_abbreviation_rules_protect_latin_acronym_before_cjk(code: str) -> None:
    # The phase sentinelizes the interior/terminal periods of a Latin acronym that
    # directly precedes a CJK character (no space), e.g. "I.B.M.公司" -> the
    # ``∯`` form, so the acronym is not split from the CJK text that follows.
    p = _processor(code)
    assert p._apply_cjk_abbreviation_rules("I.B.M.公司") == "I∯B∯M∯公司"
    # No Latin acronym before CJK -> the phase is a no-op.
    assert p._apply_cjk_abbreviation_rules("你好世界。") == "你好世界。"


# --------------------------------------------------------------------------- #
# Phase shape: each phase is a bound, callable str -> str on the live instance.
# --------------------------------------------------------------------------- #
def test_text_phases_are_bound_callables_returning_str() -> None:
    p = _processor("en")
    for phase in p._text_processing_phases():
        assert callable(phase)
        assert getattr(phase, "__self__", None) is p
        assert isinstance(phase("Hello world."), str)


def test_boundary_phases_are_bound_callables_returning_str() -> None:
    p = _processor("en")
    for phase in p._boundary_processing_phases():
        assert callable(phase)
        assert getattr(phase, "__self__", None) is p
        assert isinstance(phase("Hello world."), str)


# --------------------------------------------------------------------------- #
# Individual phase behavior (pin the load-bearing primitives).
# --------------------------------------------------------------------------- #
def test_normalize_newlines_phase() -> None:
    p = _processor("en")
    assert p._normalize_newlines("a\nb\nc") == "a\rb\rc"


def test_ensure_terminal_marker_adds_when_missing() -> None:
    p = _processor("en")
    # No terminal punctuation -> append the internal terminal sentinel.
    assert p._ensure_terminal_marker("hello world") == "hello worldȸ"


def test_ensure_terminal_marker_keeps_when_present() -> None:
    p = _processor("en")
    # Already terminated -> unchanged (the period is in profile.punctuations).
    assert "." in p.profile.punctuations
    assert p._ensure_terminal_marker("hello world.") == "hello world."


def test_replace_abbreviations_phase_protects_known_abbreviation() -> None:
    p = _processor("en")
    # The abbreviation phase routes through the language's AbbreviationReplacer and
    # sentinelizes the protected period (∯).
    assert p.replace_abbreviations("See Mr. Smith here.") == "See Mr∯ Smith here."


# --------------------------------------------------------------------------- #
# Drivers compose the phase lists in order.
# --------------------------------------------------------------------------- #
def test_process_runs_text_phases_then_splits() -> None:
    lang = Language.get_language_code("en")
    out = Processor("Hello world. This is a test. Mr. Smith left.", lang).process()
    # The abbreviation phase kept "Mr." joined; the other periods are boundaries.
    assert out == ["Hello world.", "This is a test.", "Mr. Smith left."]


def test_process_text_runs_boundary_phases_then_returns_list() -> None:
    p = _processor("en")
    result = p.process_text("Hello world")
    assert isinstance(result, list)


def test_process_empty_and_none_text_short_circuit() -> None:
    lang = Language.get_language_code("en")
    assert Processor("", lang).process() == []
    assert Processor(None, lang).process() == []
    assert Processor("x", lang).split_into_segments("") == []
