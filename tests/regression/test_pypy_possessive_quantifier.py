# -*- coding: utf-8 -*-
"""Regression guard for PyPy's mishandling of possessive regex quantifiers,
which corrupted ``clean=True`` output.

PyPy 3.11 (7.3.x) does not enforce the minimum repetition count of a possessive
quantifier whose minimum is >= 1 (``++``, ``{n}+``, ``{n,m}+``, ``{n,}+``):
instead of failing when fewer than the minimum repetitions are present, it
matches *zero* repetitions and yields a spurious zero-width match. Minimal repro:

    >>> import re
    >>> re.search(r'a++', 'b')   # CPython: None ; PyPy: <empty match at 0>

The cleaner's ``TableOfContentsRule`` relied on ``\\.{4,}+`` to require a *dot
leader* of four or more dots before a trailing page number; with the minimum not
enforced it matched zero dots and deleted ordinary trailing numbers (e.g.
``"Send it to P.O. box 6554"`` lost its ``6554``). The rule now uses the atomic
group ``(?>\\.{4,})`` — a plain counted repeat (counted correctly by PyPy) made
non-backtracking — which is exactly equivalent on CPython and correct on PyPy.

These assertions run on every interpreter and pin both the underlying regex
contract and the observable cleaner behaviour, so a regression to a possessive
form with an unmet minimum fails loudly on PyPy.
"""

from sentencesplit import Segmenter
from sentencesplit.cleaner import CleanRules


def test_toc_rule_requires_a_real_dot_leader():
    pattern = CleanRules.TableOfContentsRule.regex
    # No dot leader -> must NOT match (this is what regressed on PyPy).
    assert pattern.sub("\r", "Send it to P.O. box 6554") == "Send it to P.O. box 6554"
    assert pattern.search("box 6554") is None
    # A genuine dot-leader TOC entry still collapses to a boundary.
    assert pattern.sub("\r", "About Me....5") == "About Me\r"
    # An ordinary ellipsis followed by a number is left intact.
    assert pattern.sub("\r", "wait.... 42 things") == "wait.... 42 things"


def test_clean_preserves_trailing_numbers():
    seg = Segmenter(language="en", clean=True)
    assert seg.segment("Send it to P.O. box 6554") == ["Send it to P.O. box 6554"]
    assert seg.segment("\n3\n\nIntroduction\n\n") == ["3", "Introduction"]
    assert seg.segment("Hello World. \r\n Hello.") == ["Hello World.", "Hello."]


def test_html_rules_use_minimum_safe_tag_name():
    # The HTML/escaped-HTML rules also used possessive ``\w++`` / ``[^&]++``
    # (minimum one), which PyPy let match zero. Pin the observable behaviour.
    from sentencesplit.cleaner import Cleaner
    from sentencesplit.languages import Language

    en = Language.get_language_code("en")
    # Real tags are still stripped...
    assert Cleaner("a &lt;b&gt;x&lt;/b&gt; c", en).clean() == "a x c"
    assert Cleaner('&lt;a href="x&amp;y"&gt;link&lt;/a&gt;', en).clean() == "link"
    # ...but escaped comparison operators in prose are preserved (the run must
    # actually consume a tag name, not zero chars).
    assert "5 and y" in Cleaner("The value x &lt; 5 and y &gt; 3 here.", en).clean()
