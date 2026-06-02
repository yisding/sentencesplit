"""Guard that ``import sentencesplit`` does not eagerly resolve package metadata.

The package defers ``__version__`` (and the other metadata attributes) behind a
PEP 562 module ``__getattr__`` so the ``importlib.metadata`` / ``email.utils``
cost is only paid when the attribute is actually read. These checks run in a
fresh subprocess so the assertions see a clean interpreter rather than whatever
the pytest process already imported.
"""

import subprocess
import sys
import textwrap


def _run(snippet: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(snippet)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_bare_import_does_not_pull_in_importlib_metadata():
    out = _run(
        """
        import sys

        import sentencesplit  # noqa: F401

        print("importlib.metadata" in sys.modules)
        """
    )
    assert out == "False"


def test_version_is_a_nonempty_string_when_read():
    out = _run(
        """
        import sentencesplit

        version = sentencesplit.__version__
        assert isinstance(version, str) and version, repr(version)
        print(version)
        """
    )
    assert out
