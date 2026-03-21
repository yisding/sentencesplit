import importlib
import importlib.metadata as importlib_metadata
import tomllib
from pathlib import Path

import sentencesplit
import sentencesplit.about as about


def _project_metadata():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)["project"]


def test_public_metadata_matches_pyproject():
    project = _project_metadata()
    author_names = ", ".join(author["name"] for author in project["authors"])
    author_emails = ", ".join(author["email"] for author in project["authors"])

    assert sentencesplit.__version__ == project["version"]
    assert about.__version__ == project["version"]
    assert about.__uri__ == project["urls"]["Repository"]
    assert about.__author__ == author_names
    assert about.__email__ == author_emails


def test_about_falls_back_to_pyproject_version_when_distribution_metadata_is_missing(monkeypatch):
    project = _project_metadata()

    def raise_package_not_found(_distribution_name):
        raise importlib_metadata.PackageNotFoundError

    with monkeypatch.context() as context:
        context.setattr(importlib_metadata, "version", raise_package_not_found)
        importlib.reload(about)
        assert about.__version__ == project["version"]

    importlib.reload(about)
