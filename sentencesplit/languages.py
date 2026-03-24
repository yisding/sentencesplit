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

# Reverse map: class name -> (module_path, class_name) for __getattr__ support
_CLASS_NAME_TO_MODULE: dict[str, tuple[str, str]] = {
    cls_name: (mod_path, cls_name) for mod_path, cls_name in _LANGUAGE_MODULES.values()
}

_loaded_cache: dict[str, type] = {}

__all__ = ["LANGUAGE_CODES", "Language"] + list(_CLASS_NAME_TO_MODULE.keys())


def _load_language(code: str) -> type:
    if code in _loaded_cache:
        return _loaded_cache[code]
    mod_path, cls_name = _LANGUAGE_MODULES[code]
    mod = importlib.import_module(mod_path)
    klass = getattr(mod, cls_name)
    _loaded_cache[code] = klass
    return klass


def __getattr__(name: str):
    """Allow ``from sentencesplit.languages import English`` etc. via lazy loading."""
    if name in _CLASS_NAME_TO_MODULE:
        mod_path, cls_name = _CLASS_NAME_TO_MODULE[name]
        mod = importlib.import_module(mod_path)
        klass = getattr(mod, cls_name)
        globals()[name] = klass
        return klass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Keep LANGUAGE_CODES as a lazy-loading dict for backwards compatibility
class _LazyLanguageCodes(dict):
    """dict subclass that lazily loads language modules on access."""

    def __init__(self):
        super().__init__()
        self._removed: set[str] = set()

    def _materialize(self, code: str) -> None:
        """Ensure a built-in key is in the backing dict."""
        if code in _LANGUAGE_MODULES and code not in self._removed and not dict.__contains__(self, code):
            dict.__setitem__(self, code, _load_language(code))

    def __missing__(self, code: str) -> type:
        if code in _LANGUAGE_MODULES and code not in self._removed:
            klass = _load_language(code)
            self[code] = klass
            return klass
        raise KeyError(code)

    def __contains__(self, code: object) -> bool:
        if isinstance(code, str) and code in self._removed:
            return dict.__contains__(self, code)
        return code in _LANGUAGE_MODULES or dict.__contains__(self, code)

    def __setitem__(self, key, value):
        self._removed.discard(key)
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self._materialize(key)
        dict.__delitem__(self, key)
        if key in _LANGUAGE_MODULES:
            self._removed.add(key)

    def __iter__(self):
        seen = set()
        for code in _LANGUAGE_MODULES:
            if code not in self._removed:
                seen.add(code)
                yield code
        for code in dict.keys(self):
            if code not in seen:
                yield code

    def __len__(self) -> int:
        builtin_active = set(_LANGUAGE_MODULES) - self._removed
        return len(builtin_active | set(dict.keys(self)))

    def keys(self):
        return dict(dict.fromkeys(list(self))).keys()

    def values(self):
        return [self[code] for code in self]

    def items(self):
        return [(code, self[code]) for code in self]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return default

    def pop(self, key, *args):
        try:
            self._materialize(key)
            value = dict.pop(self, key)
            if key in _LANGUAGE_MODULES:
                self._removed.add(key)
            return value
        except KeyError:
            if args:
                return args[0]
            raise

    def copy(self) -> dict:
        return dict(self.items())

    def __repr__(self) -> str:
        return repr(dict(self.items()))

    def __eq__(self, other) -> bool:
        if not isinstance(other, dict):
            return NotImplemented
        return dict(self.items()) == other

    def __or__(self, other):
        result = dict(self.items())
        result.update(other)
        return result

    def __ror__(self, other):
        result = dict(other)
        result.update(self.items())
        return result


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
