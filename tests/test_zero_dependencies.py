"""Guards for the zero-dependency promise.

A bare ``import sentencesplit`` must not pull in any third-party (non-stdlib)
top-level module. This is the library's core selling point, so it gets a hard
test: a future change that quietly adds a runtime dependency fails CI here.

Both checks run in an isolated subprocess (``python -I``) so the assertions see
a clean interpreter rather than whatever the pytest process already imported.
"""

import subprocess
import sys
import textwrap


def _run(snippet: str) -> str:
    result = subprocess.run(
        [sys.executable, "-I", "-c", textwrap.dedent(snippet)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_bare_import_pulls_in_no_third_party_modules():
    out = _run(
        """
        import sys

        before = set(sys.modules)
        import sentencesplit  # noqa: F401
        added = set(sys.modules) - before

        stdlib = sys.stdlib_module_names
        offenders = sorted(
            name
            for name in added
            if "." not in name                       # top-level modules only
            and not name.startswith("_")             # skip C-accelerator internals
            and not name.startswith("sentencesplit")
            and name not in stdlib
        )
        print("|".join(offenders))
        """
    )
    offenders = [name for name in out.split("|") if name]
    assert offenders == [], (
        f"import sentencesplit pulled in non-stdlib modules: {offenders}. The library must stay zero-dependency."
    )


def test_public_surface_matches_all():
    # `from sentencesplit import *` and dir(sentencesplit) should expose exactly
    # the curated public names, not every submodule. `__all__` defines that
    # boundary, so it must match the names we intend to support.
    import sentencesplit

    expected = {
        "Segmenter",
        "StreamSegmenter",
        "list_languages",
        "TextSpan",
        "SegmentLookahead",
        "__version__",
    }
    assert set(sentencesplit.__all__) == expected
    assert len(sentencesplit.__all__) == len(set(sentencesplit.__all__)), "duplicate names in __all__"
    for name in sentencesplit.__all__:
        assert hasattr(sentencesplit, name), f"__all__ lists {name!r} but it is not importable"


def test_list_languages_imports_no_language_modules():
    # Enumerating supported languages must stay cheap: it must not import any
    # concrete `sentencesplit.lang.*` module just to list the codes.
    out = _run(
        """
        import sys
        import sentencesplit

        prefix = "sentencesplit.lang."
        before = {m for m in sys.modules if m.startswith(prefix)}
        codes = sentencesplit.list_languages()
        after = {m for m in sys.modules if m.startswith(prefix)}

        assert codes, "expected a non-empty language list"
        print("|".join(sorted(after - before)))
        """
    )
    imported = [name for name in out.split("|") if name]
    assert imported == [], f"list_languages() imported language modules: {imported}"
