# -*- coding: utf-8 -*-
"""Dedicated unit suite for ``processor.Processor``'s two pipeline phase lists.

``Processor`` organizes its work into two explicit, ordered pipelines:

* ``_text_processing_phases()`` — newline normalization -> list-item markers ->
  abbreviation replacement -> (optional CJK abbreviation rules) -> numbers ->
  continuous punctuation -> numeric refs -> special-token protection;
* ``_boundary_processing_phases()`` — terminal marker -> exclamation words ->
  between-punctuation -> double-punctuation -> quotation-punctuation -> list parens.

The phase lists are the contract every per-language ``Processor`` override and the
``process()`` / ``process_text()`` drivers depend on, so they get first-class
coverage here: the exact ordered membership, the CJK-abbreviation phase being
conditional on the language profile, that each phase is a callable ``str -> str``
bound to the live instance, and that the drivers compose them in order. The
individual phase methods are also pinned at the unit level (newline normalization,
terminal marker, the abbreviation-protection delegation) so a refactor that reorders
or drops a phase is caught without driving a full ``segment()`` call.
"""

from __future__ import annotations

import pytest

from sentencesplit.languages import Language
from sentencesplit.processor import Processor

# Languages WITHOUT CJK abbreviation rules (base text pipeline).
_NON_CJK = ["en", "en_legal", "de", "fr", "ru", "bg", "nl"]
# Languages WITH CJK abbreviation rules (text pipeline grows the CJK phase).
_CJK = ["zh", "ja", "en_es_zh"]

_BASE_TEXT_PHASES = (
    "_normalize_newlines",
    "_mark_list_item_boundaries",
    "replace_abbreviations",
    "replace_numbers",
    "replace_continuous_punctuation",
    "replace_periods_before_numeric_references",
    "_protect_special_tokens",
)
_BOUNDARY_PHASES = (
    "_ensure_terminal_marker",
    "_apply_exclamation_word_rules",
    "between_punctuation",
    "_apply_double_punctuation_rules",
    "_apply_quotation_punctuation_rules",
    "_replace_list_parens",
)


def _processor(code: str, text: str = "x") -> Processor:
    return Processor(text, Language.get_language_code(code))


def _phase_names(phases) -> list[str]:
    return [p.__name__ for p in phases]


# --------------------------------------------------------------------------- #
# _text_processing_phases — ordered membership.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", _NON_CJK)
def test_text_phases_non_cjk_exact_order(code: str) -> None:
    p = _processor(code)
    assert not p.profile.cjk_abbreviation_rules
    assert tuple(_phase_names(p._text_processing_phases())) == _BASE_TEXT_PHASES


@pytest.mark.parametrize("code", _CJK)
def test_text_phases_cjk_inserts_abbreviation_rules_after_abbreviations(code: str) -> None:
    p = _processor(code)
    assert p.profile.cjk_abbreviation_rules  # the conditional phase fires
    names = _phase_names(p._text_processing_phases())
    # The CJK phase sits immediately AFTER abbreviation replacement and BEFORE numbers.
    assert names == [
        "_normalize_newlines",
        "_mark_list_item_boundaries",
        "replace_abbreviations",
        "_apply_cjk_abbreviation_rules",
        "replace_numbers",
        "replace_continuous_punctuation",
        "replace_periods_before_numeric_references",
        "_protect_special_tokens",
    ]


def test_cjk_phase_is_exactly_one_addition() -> None:
    # The only structural difference between the CJK and base text pipelines is the
    # single inserted ``_apply_cjk_abbreviation_rules`` phase.
    base = _phase_names(_processor("en")._text_processing_phases())
    cjk = _phase_names(_processor("zh")._text_processing_phases())
    assert len(cjk) == len(base) + 1
    assert [n for n in cjk if n != "_apply_cjk_abbreviation_rules"] == base


# --------------------------------------------------------------------------- #
# _boundary_processing_phases — ordered membership (language-independent).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", _NON_CJK + _CJK)
def test_boundary_phases_exact_order(code: str) -> None:
    p = _processor(code)
    assert tuple(_phase_names(p._boundary_processing_phases())) == _BOUNDARY_PHASES


# --------------------------------------------------------------------------- #
# Phase shape: each phase is a bound, callable str -> str (boundary phases) /
# str -> str (text phases) on the live instance.
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


def test_phase_lists_are_fresh_tuples_per_call() -> None:
    # The drivers iterate a freshly-built tuple each call (no shared mutable state),
    # so the phase composition cannot drift between invocations on one instance.
    p = _processor("en")
    a = p._text_processing_phases()
    b = p._text_processing_phases()
    assert isinstance(a, tuple) and isinstance(b, tuple)
    assert _phase_names(a) == _phase_names(b)
    assert isinstance(p._boundary_processing_phases(), tuple)
