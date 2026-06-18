from .exceptions import InvalidConfigurationError as InvalidConfigurationError
from .exceptions import SentenceSplitError as SentenceSplitError
from .exceptions import UnknownLanguageError as UnknownLanguageError
from .languages import list_languages as list_languages
from .languages import register_language as register_language
from .languages import unregister_language as unregister_language
from .segmenter import Segmenter as Segmenter
from .stream_segmenter import StreamSegmenter as StreamSegmenter
from .utils import SegmentLookahead as SegmentLookahead
from .utils import TextSpan as TextSpan

__all__ = [
    "Segmenter",
    "StreamSegmenter",
    "SentenceSplitError",
    "InvalidConfigurationError",
    "UnknownLanguageError",
    "list_languages",
    "register_language",
    "unregister_language",
    "TextSpan",
    "SegmentLookahead",
    "__version__",
]

_LAZY_METADATA = {"__version__", "__author__", "__email__", "__uri__"}


def __getattr__(name: str) -> str:
    """Lazily resolve package metadata so importing the package stays cheap."""
    if name in _LAZY_METADATA:
        from . import about

        return getattr(about, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted([*globals().keys(), "__version__", "__author__", "__email__", "__uri__"])
