from .exceptions import SentenceSplitError as SentenceSplitError
from .languages import list_languages as list_languages
from .segmenter import Segmenter as Segmenter
from .stream_segmenter import StreamSegmenter as StreamSegmenter
from .utils import SegmentLookahead as SegmentLookahead
from .utils import TextSpan as TextSpan

__all__ = [
    "Segmenter",
    "StreamSegmenter",
    "SentenceSplitError",
    "list_languages",
    "TextSpan",
    "SegmentLookahead",
    "__version__",
]

_LAZY_METADATA = {"__version__", "__author__", "__email__", "__uri__"}


def __getattr__(name):
    """Lazily resolve package metadata so importing the package stays cheap."""
    if name in _LAZY_METADATA:
        from . import about

        return getattr(about, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted([*globals().keys(), "__version__", "__author__", "__email__", "__uri__"])
