from importlib.metadata import PackageNotFoundError, version

# inspired from:
# https://python-packaging-user-guide.readthedocs.org/en/latest/single_source_version/

__title__ = "sentencesplit"
__summary__ = "sentencesplit is a rule-based sentence boundary detection library, derived from pySBD (Python Sentence Boundary Disambiguation), that works out-of-the-box across many languages."
__license__ = "MIT"


def _load_source_project_metadata() -> dict[str, object]:
    import tomllib
    from pathlib import Path

    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as pyproject_file:
            data = tomllib.load(pyproject_file)
        project = data.get("project", {})
        if project.get("name") != "sentencesplit":
            return {}
        return project
    except (OSError, tomllib.TOMLDecodeError):
        return {}


try:
    __version__ = version("sentencesplit")
    __uri__ = "https://github.com/yisding/sentencesplit"
    __author__ = "Nipun Sadvilkar, Yi Ding"
    __email__ = "nipunsadvilkar@gmail.com, yi.s.ding@gmail.com"
except PackageNotFoundError:
    _project = _load_source_project_metadata()
    _authors = _project.get("authors", [])
    _urls = _project.get("urls", {})
    __version__ = str(_project.get("version", "0.0.0"))
    __uri__ = str(_urls.get("Repository", "https://github.com/yisding/sentencesplit"))
    __author__ = ", ".join(author["name"] for author in _authors if "name" in author) or "Nipun Sadvilkar, Yi Ding"
    __email__ = ", ".join(author["email"] for author in _authors if "email" in author) or (
        "nipunsadvilkar@gmail.com, yi.s.ding@gmail.com"
    )
