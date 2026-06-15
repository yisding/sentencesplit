# -*- coding: utf-8 -*-
"""Core ``segment()`` property tests (Roadmap T3) — QUARANTINED backlog.

Three structural invariants are asserted with Hypothesis across every registered
language code:

1. **No-crash.** ``segment()`` / ``segment_spans()`` (and ``clean=True``
   segmentation) never raise on arbitrary / dirty Unicode input. This holds for
   all 26 codes and is a hard regression gate.
2. **Idempotence.** Re-segmenting an already-emitted segment reproduces it
   (modulo trailing whitespace): ``segment(s) == [s]`` for each ``s`` in
   ``segment(text)``. A boundary the engine drew once should be stable when the
   fragment is fed back in.
3. **split_mode monotonicity.** A more aggressive ``split_mode`` must never draw
   *fewer* boundaries than a more conservative one:
   ``len(segment(text, conservative)) <= ... <= len(segment(text, aggressive))``.

QUARANTINE (discoverable backlog)
---------------------------------
Invariants (2) and (3) are *not* universally true of the live v2 engine — they
are real, pre-existing gaps this module turns into a measured backlog rather
than papering over. Each known-failing code is listed in a quarantine allowlist
with a **deterministic counterexample**; for those codes the test asserts the
counterexample still reproduces the violation and then calls ``pytest.xfail()``
(immune to the suite-wide ``xfail_strict=true``: a quarantined code whose engine
behavior is later fixed simply turns GREEN, never XPASS-reds). A code that is
*not* quarantined runs the full Hypothesis property search and reds the suite on
any violation, so a newly-introduced regression on a currently-clean language is
caught at once.

Empirically (high-budget Hypothesis search, see the discovery harness):

* **Idempotence fails in ALL 26 codes.** The dominant family is repeated terminal
  punctuation: an emitted segment that *starts* with a doubled terminal (e.g.
  ``"!!H"``, ``"！！"``, ``"!? e"``) re-splits when fed back in, because the
  multi-terminator resplit / between-punctuation passes treat the run differently
  in fragment position. There is therefore no idempotence gate today; the whole
  registry is the backlog.
* **split_mode monotonicity fails in 14 codes** (the Latin/Cyrillic period
  languages) on the canonical ``". ! e."``: conservative/balanced emit 2 segments
  but aggressive merges to 1 (``len`` drops as the bias *increases*). The other
  12 codes (am, ar, el, en_es_zh, fa, hi, hy, ja, mr, my, ur, zh) hold
  monotonicity even at 4000 examples and are a live gate.

Promote a code out of the relevant allowlist the moment the engine satisfies the
invariant for it; the stale-allowlist guards below fail if a quarantined
counterexample stops reproducing (the entry must then be removed).

Hypothesis is a DEV-ONLY dependency; the zero-dependency core never imports it
(guarded by ``tests/test_zero_dependencies.py``), so this whole module is skipped
when Hypothesis is absent.
"""

from __future__ import annotations

import pytest

from sentencesplit.segmenter import Segmenter
from sentencesplit.utils import SPLIT_MODES
from tests.helpers import ALL_CODES, DIRTY_CHARS, text_strategy

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
except ImportError:  # pragma: no cover - dev-only dependency
    pytest.skip("hypothesis is a dev-only dependency", allow_module_level=True)


# --------------------------------------------------------------------------- #
# Quarantine allowlists: ``{code: counterexample}``. Each value is a concrete,
# deterministic input that reproduces the invariant violation for that code. An
# entry here is rendered as an ``xfail`` (never a hard failure); a code NOT here
# that violates the invariant under Hypothesis reds the suite immediately.
# --------------------------------------------------------------------------- #

# Idempotence is violated by every registered code. The counterexample is an
# input whose ``segment()`` output contains at least one segment that re-splits
# when fed back through ``segment()``. Most are the "doubled terminal at the
# start of a fragment" family; a few (ar/ru/hy/ur) need a zero-width-space carrier
# (``​``) so the doubled-terminal fragment is produced in non-leading
# position.
_ZWSP = "​"
IDEMPOTENCE_QUARANTINE: dict[str, str] = {
    "am": "! !!",
    "ar": f"؟{_ZWSP} {_ZWSP}م؟م",
    "bg": ". !!З",
    "da": ". !? e",
    "de": ". !? e",
    "el": ".!! ",
    "en": "H.!!H",
    "en_es_zh": ".!!",
    "en_legal": "H.!!H",
    "es": "H.!!H",
    "fa": ". . . . ",
    "fr": "w.́ x.H",
    "hi": "! !!",
    "hy": f"։{_ZWSP} {_ZWSP}Բ։Բ",
    "it": ". !? e",
    "ja": "。！！",
    "kk": "С.!!С",
    "mr": "।!!",
    "my": "? ??",
    "nl": ". !? e",
    "pl": ". !? e",
    "ru": f"П!{_ZWSP} {_ZWSP}ПП!П",
    "sk": "H.!!H",
    "tl": "H.!!H",
    "ur": f"۔{_ZWSP} {_ZWSP}س۔س",
    "zh": "。！！",
}

# split_mode monotonicity is violated by the 14 Latin/Cyrillic period languages
# on the canonical ``". ! e."``: conservative/balanced keep ``". "`` and ``"! e."``
# as 2 segments, but aggressive merges the whole run into 1 — so the segment count
# DROPS as the split bias increases. The other 12 codes hold the invariant.
_MONOTONICITY_COUNTEREXAMPLE = ". ! e."
MONOTONICITY_QUARANTINE: dict[str, str] = {
    code: _MONOTONICITY_COUNTEREXAMPLE
    for code in (
        "bg",
        "da",
        "de",
        "en",
        "en_legal",
        "es",
        "fr",
        "it",
        "kk",
        "nl",
        "pl",
        "ru",
        "sk",
        "tl",
    )
}


# --------------------------------------------------------------------------- #
# Property bodies (pure predicates returning the first violating witness, or
# ``None`` when the invariant holds for the given input).
# --------------------------------------------------------------------------- #
def _idempotence_witness(seg: Segmenter, text: str) -> tuple[str, list[str]] | None:
    """First emitted segment that does NOT re-segment to itself (mod trailing ws)."""
    for s in seg.segment(text):
        if not s.strip():
            continue
        re_segmented = seg.segment(s)
        if [part.rstrip() for part in re_segmented] != [s.rstrip()]:
            return s, re_segmented
    return None


def _monotonicity_witness(segmenters: dict[str, Segmenter], text: str) -> tuple[int, ...] | None:
    """Return the ``(conservative, balanced, aggressive)`` counts iff they are
    NOT non-decreasing (i.e. a more aggressive mode produced fewer segments)."""
    counts = tuple(len(segmenters[mode].segment(text)) for mode in SPLIT_MODES)
    ascending = all(counts[i] <= counts[i + 1] for i in range(len(counts) - 1))
    return None if ascending else counts


def _split_mode_segmenters(code: str) -> dict[str, Segmenter]:
    return {mode: Segmenter(language=code, clean=False, split_mode=mode) for mode in SPLIT_MODES}


# Codes that are a live gate for each quarantined invariant (run Hypothesis,
# must hold). Idempotence is universally broken, so its clean set is empty today.
_IDEMPOTENCE_CLEAN = [c for c in ALL_CODES if c not in IDEMPOTENCE_QUARANTINE]
_MONOTONICITY_CLEAN = [c for c in ALL_CODES if c not in MONOTONICITY_QUARANTINE]


# --------------------------------------------------------------------------- #
# 1. No-crash — hard gate across every code.
# --------------------------------------------------------------------------- #
# The engine carries decisions as in-band sentinel codepoints spliced into the
# text (processor.py ``_RESERVED_SENTINELS``); because those are printable
# characters a user can type, the escape/restore machinery must stay
# non-destructive when input *already* contains them. Feeding them in deliberately
# exercises that collision path rather than waiting for ``st.characters()`` to
# stumble onto one.
_RESERVED_SENTINELS = "∯♬♭☉☇☈☄☊☋☌☍ȸȹƪ♟♝☏∮♨☝"
_NOCRASH_STRATEGY = st.one_of(
    st.text(max_size=48),
    st.text(
        alphabet=list("Hello world.!?;:'\"()[]<>/\\\n\t ") + DIRTY_CHARS + list(_RESERVED_SENTINELS),
        max_size=64,
    ),
)


@pytest.mark.parametrize("code", ALL_CODES)
@settings(max_examples=150, deadline=None)
@given(data=st.data())
def test_segment_never_crashes(code, data):
    """``segment``/``segment_spans``/``clean=True`` never raise on dirty Unicode."""
    payload = data.draw(st.one_of(_NOCRASH_STRATEGY, text_strategy(code)))
    Segmenter(language=code, clean=False).segment(payload)
    Segmenter(language=code, clean=False).segment_spans(payload)
    Segmenter(language=code, clean=True).segment(payload)


# --------------------------------------------------------------------------- #
# 2. Idempotence — quarantined per code (backlog), Hypothesis gate for clean codes.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", ALL_CODES)
def test_segment_idempotence_quarantined(code):
    """Quarantined codes xfail on their deterministic counterexample.

    The whole registry is quarantined today (idempotence is universally broken),
    so every code lands here as a documented xfail. If a code is later promoted
    out of ``IDEMPOTENCE_QUARANTINE`` it is exercised by
    ``test_segment_idempotence_property`` instead.
    """
    counterexample = IDEMPOTENCE_QUARANTINE.get(code)
    if counterexample is None:
        pytest.skip(f"{code} is not quarantined; covered by the property gate")
    seg = Segmenter(language=code, clean=False)
    witness = _idempotence_witness(seg, counterexample)
    assert witness is not None, (
        f"{code}: quarantined idempotence counterexample {counterexample!r} no longer "
        "reproduces — promote this code out of IDEMPOTENCE_QUARANTINE."
    )
    segment, re_segmented = witness
    pytest.xfail(f"quarantined idempotence gap (T3 backlog): {code} segment {segment!r} re-segments to {re_segmented!r}")


@pytest.mark.parametrize("code", _IDEMPOTENCE_CLEAN or [pytest.param("", marks=pytest.mark.skip(reason="no clean codes"))])
@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_segment_idempotence_property(code, data):
    """Non-quarantined codes must satisfy idempotence on every Hypothesis input."""
    seg = Segmenter(language=code, clean=False)
    text = data.draw(text_strategy(code))
    witness = _idempotence_witness(seg, text)
    assert witness is None, f"{code}: idempotence violated on {text!r}: segment {witness}"


# --------------------------------------------------------------------------- #
# 3. split_mode monotonicity — quarantined per code, Hypothesis gate for clean codes.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", ALL_CODES)
def test_segment_split_mode_monotonicity_quarantined(code):
    """Quarantined codes xfail on the deterministic ``". ! e."`` counterexample."""
    counterexample = MONOTONICITY_QUARANTINE.get(code)
    if counterexample is None:
        pytest.skip(f"{code} is not quarantined; covered by the property gate")
    segmenters = _split_mode_segmenters(code)
    witness = _monotonicity_witness(segmenters, counterexample)
    assert witness is not None, (
        f"{code}: quarantined monotonicity counterexample {counterexample!r} no longer "
        "violates monotonicity — promote this code out of MONOTONICITY_QUARANTINE."
    )
    pytest.xfail(
        f"quarantined split_mode monotonicity gap (T3 backlog): {code} on "
        f"{counterexample!r} -> (conservative,balanced,aggressive) counts {witness}"
    )


@pytest.mark.parametrize("code", _MONOTONICITY_CLEAN)
@settings(max_examples=400, deadline=None)
@given(data=st.data())
def test_segment_split_mode_monotonicity_property(code, data):
    """Non-quarantined codes: segment count is non-decreasing in split bias."""
    segmenters = _split_mode_segmenters(code)
    text = data.draw(text_strategy(code))
    witness = _monotonicity_witness(segmenters, text)
    assert witness is None, (
        f"{code}: split_mode monotonicity violated on {text!r}: (conservative,balanced,aggressive) counts {witness}"
    )


# --------------------------------------------------------------------------- #
# 4. Backlog hygiene: the quarantine allowlists must not rot.
# --------------------------------------------------------------------------- #
def test_idempotence_quarantine_has_no_stale_entries():
    """Every quarantined code must be registered and still reproduce its failure."""
    stale: list[str] = []
    for code, counterexample in IDEMPOTENCE_QUARANTINE.items():
        if code not in ALL_CODES:
            stale.append(f"{code} (not a registered code)")
            continue
        seg = Segmenter(language=code, clean=False)
        if _idempotence_witness(seg, counterexample) is None:
            stale.append(f"{code} (counterexample {counterexample!r} no longer fails)")
    assert stale == [], f"stale idempotence quarantine entries: {stale}"


def test_monotonicity_quarantine_has_no_stale_entries():
    """Every quarantined code must be registered and still violate monotonicity."""
    stale: list[str] = []
    for code, counterexample in MONOTONICITY_QUARANTINE.items():
        if code not in ALL_CODES:
            stale.append(f"{code} (not a registered code)")
            continue
        segmenters = _split_mode_segmenters(code)
        if _monotonicity_witness(segmenters, counterexample) is None:
            stale.append(f"{code} (counterexample {counterexample!r} no longer violates)")
    assert stale == [], f"stale monotonicity quarantine entries: {stale}"
