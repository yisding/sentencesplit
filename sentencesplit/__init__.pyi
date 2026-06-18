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

__all__: list[str]

__version__: str
__author__: str
__email__: str
__uri__: str

def __dir__() -> list[str]: ...
