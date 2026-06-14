"""Guard that ``import sentencesplit`` does not eagerly resolve package metadata.

The package defers ``__version__`` (and the other metadata attributes) behind a
PEP 562 module ``__getattr__`` so the ``importlib.metadata`` / ``email.utils``
cost is only paid when the attribute is actually read. These checks run in a
fresh subprocess so the assertions see a clean interpreter rather than whatever
the pytest process already imported.
"""

import platform
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


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


@pytest.mark.skipif(
    platform.python_implementation() == "PyPy",
    reason="mypy refuses to run under PyPy ('Running mypy on PyPy is not supported yet')",
)
def test_lazy_metadata_preserves_typed_public_surface(tmp_path: Path):
    config = tmp_path / "mypy.ini"
    config.write_text("[mypy]\npython_version = 3.11\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(config),
            "-c",
            textwrap.dedent(
                """
                import sentencesplit

                reveal_type(sentencesplit.__version__)
                from sentencesplit import no_such_attr
                """
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert 'Revealed type is "str"' in output
    assert 'Module "sentencesplit" has no attribute "no_such_attr"' in output
