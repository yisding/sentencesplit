import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

# inspired from:
# https://python-packaging-user-guide.readthedocs.org/en/latest/single_source_version/


def _load_source_project_metadata() -> dict[str, object]:
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as pyproject_file:
            return tomllib.load(pyproject_file).get("project", {})
    except (OSError, tomllib.TOMLDecodeError):
        return {}


_PROJECT_METADATA = _load_source_project_metadata()
_PROJECT_AUTHORS = _PROJECT_METADATA.get("authors", [])
_PROJECT_URLS = _PROJECT_METADATA.get("urls", {})

__title__ = "sentencesplit"
try:
    __version__ = version("sentencesplit")
except PackageNotFoundError:
    __version__ = str(_PROJECT_METADATA.get("version", "0.0.0"))
__summary__ = "sentencesplit is a rule-based sentence boundary detection library, derived from pySBD (Python Sentence Boundary Disambiguation), that works out-of-the-box across many languages."
__uri__ = str(_PROJECT_URLS.get("Repository", "https://github.com/yisding/sentencesplit"))
__author__ = ", ".join(author["name"] for author in _PROJECT_AUTHORS if "name" in author) or "Nipun Sadvilkar, Yi Ding"
__email__ = ", ".join(author["email"] for author in _PROJECT_AUTHORS if "email" in author) or (
    "nipunsadvilkar@gmail.com, yi.s.ding@gmail.com"
)
__license__ = "MIT"
