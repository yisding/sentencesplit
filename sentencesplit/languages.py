# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib

_LANGUAGE_MODULES: dict[str, tuple[str, str]] = {
    "en": ("sentencesplit.lang.english", "English"),
    "en_es_zh": ("sentencesplit.lang.en_es_zh", "EnglishSpanishChinese"),
    "en_legal": ("sentencesplit.lang.en_legal", "EnglishLegal"),
    "hi": ("sentencesplit.lang.hindi", "Hindi"),
    "mr": ("sentencesplit.lang.marathi", "Marathi"),
    "zh": ("sentencesplit.lang.chinese", "Chinese"),
    "es": ("sentencesplit.lang.spanish", "Spanish"),
    "am": ("sentencesplit.lang.amharic", "Amharic"),
    "ar": ("sentencesplit.lang.arabic", "Arabic"),
    "hy": ("sentencesplit.lang.armenian", "Armenian"),
    "bg": ("sentencesplit.lang.bulgarian", "Bulgarian"),
    "ur": ("sentencesplit.lang.urdu", "Urdu"),
    "ru": ("sentencesplit.lang.russian", "Russian"),
    "pl": ("sentencesplit.lang.polish", "Polish"),
    "fa": ("sentencesplit.lang.persian", "Persian"),
    "nl": ("sentencesplit.lang.dutch", "Dutch"),
    "da": ("sentencesplit.lang.danish", "Danish"),
    "fr": ("sentencesplit.lang.french", "French"),
    "my": ("sentencesplit.lang.burmese", "Burmese"),
    "el": ("sentencesplit.lang.greek", "Greek"),
    "it": ("sentencesplit.lang.italian", "Italian"),
    "ja": ("sentencesplit.lang.japanese", "Japanese"),
    "de": ("sentencesplit.lang.deutsch", "Deutsch"),
    "kk": ("sentencesplit.lang.kazakh", "Kazakh"),
    "sk": ("sentencesplit.lang.slovak", "Slovak"),
    "tl": ("sentencesplit.lang.tagalog", "Tagalog"),
}

_loaded_cache: dict[str, type] = {}


def _load_language(code: str) -> type:
    if code in _loaded_cache:
        return _loaded_cache[code]
    mod_path, cls_name = _LANGUAGE_MODULES[code]
    mod = importlib.import_module(mod_path)
    klass = getattr(mod, cls_name)
    _loaded_cache[code] = klass
    return klass


# Keep LANGUAGE_CODES as a lazy-loading dict for backwards compatibility
class _LazyLanguageCodes:
    """Dict-like object that lazily loads language modules on access."""

    def __getitem__(self, code: str) -> type:
        if code in _loaded_cache:
            return _loaded_cache[code]
        if code not in _LANGUAGE_MODULES:
            raise KeyError(code)
        return _load_language(code)

    def __setitem__(self, code: str, lang_class: type) -> None:
        _loaded_cache[code] = lang_class
        if code not in _LANGUAGE_MODULES:
            # Register a placeholder so __contains__/keys()/etc. see it
            _LANGUAGE_MODULES[code] = ("", "")

    def __delitem__(self, code: str) -> None:
        _loaded_cache.pop(code, None)
        if code not in _LANGUAGE_MODULES:
            raise KeyError(code)
        del _LANGUAGE_MODULES[code]

    def __contains__(self, code: object) -> bool:
        return code in _LANGUAGE_MODULES

    def __iter__(self):
        return iter(_LANGUAGE_MODULES)

    def __len__(self) -> int:
        return len(_LANGUAGE_MODULES)

    def keys(self):
        return _LANGUAGE_MODULES.keys()

    def values(self):
        return [self[code] for code in _LANGUAGE_MODULES]

    def items(self):
        return [(code, self[code]) for code in _LANGUAGE_MODULES]


LANGUAGE_CODES = _LazyLanguageCodes()


class Language:
    def __init__(self, code: str) -> None:
        self.code = code

    @classmethod
    def get_language_code(cls, code: str):
        try:
            return LANGUAGE_CODES[code]
        except KeyError:
            raise ValueError(
                "Provide valid language ID i.e. ISO code. Available codes are : {}".format(sorted(LANGUAGE_CODES.keys()))
            )
