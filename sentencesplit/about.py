# inspired from:
# https://python-packaging-user-guide.readthedocs.org/en/latest/single_source_version/

from importlib.metadata import PackageNotFoundError, version

__title__ = "sentencesplit"
try:
    __version__ = version("sentencesplit")
except PackageNotFoundError:
    __version__ = "0.0.0"
__summary__ = "sentencesplit is a rule-based sentence boundary detection library, derived from pySBD (Python Sentence Boundary Disambiguation), that works out-of-the-box across many languages."
__uri__ = "http://nipunsadvilkar.github.io/"
__author__ = "Nipun Sadvilkar"
__email__ = "nipunsadvilkar@gmail.com"
__license__ = "MIT"
