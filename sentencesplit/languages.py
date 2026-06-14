# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
from threading import RLock

from sentencesplit.exceptions import UnknownLanguageError

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
_LANGUAGE_LOCK = RLock()

__all__ = [
    "LANGUAGE_CODES",
    "Language",
    "list_languages",
    "register_language",
    "unregister_language",
] + list(_CLASS_NAME_TO_MODULE.keys())


def _load_language(code: str) -> type:
    with _LANGUAGE_LOCK:
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
        with _LANGUAGE_LOCK:
            cached = globals().get(name)
            if cached is not None:
                return cached
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
        with _LANGUAGE_LOCK:
            if code in _LANGUAGE_MODULES and code not in self._removed and not dict.__contains__(self, code):
                dict.__setitem__(self, code, _load_language(code))

    def __missing__(self, code: str) -> type:
        with _LANGUAGE_LOCK:
            if code in _LANGUAGE_MODULES and code not in self._removed:
                klass = _load_language(code)
                self[code] = klass
                return klass
            raise KeyError(code)

    def __contains__(self, code: object) -> bool:
        with _LANGUAGE_LOCK:
            if isinstance(code, str) and code in self._removed:
                return dict.__contains__(self, code)
            return code in _LANGUAGE_MODULES or dict.__contains__(self, code)

    def __setitem__(self, key, value):
        with _LANGUAGE_LOCK:
            self._removed.discard(key)
            dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        with _LANGUAGE_LOCK:
            self._materialize(key)
            dict.__delitem__(self, key)
            if key in _LANGUAGE_MODULES:
                self._removed.add(key)

    def __iter__(self):
        with _LANGUAGE_LOCK:
            seen = set()
            codes = []
            for code in _LANGUAGE_MODULES:
                if code not in self._removed:
                    seen.add(code)
                    codes.append(code)
            for code in dict.keys(self):
                if code not in seen:
                    codes.append(code)
        yield from codes

    def __len__(self) -> int:
        with _LANGUAGE_LOCK:
            builtin_active = set(_LANGUAGE_MODULES) - self._removed
            return len(builtin_active | set(dict.keys(self)))

    def keys(self):
        with _LANGUAGE_LOCK:
            return dict(dict.fromkeys(list(self))).keys()

    def values(self):
        with _LANGUAGE_LOCK:
            return [self[code] for code in self]

    def items(self):
        with _LANGUAGE_LOCK:
            return [(code, self[code]) for code in self]

    def get(self, key, default=None):
        with _LANGUAGE_LOCK:
            try:
                return self[key]
            except KeyError:
                return default

    def setdefault(self, key, default=None):
        with _LANGUAGE_LOCK:
            if key in self:
                return self[key]
            self[key] = default
            return default

    def pop(self, key, *args):
        with _LANGUAGE_LOCK:
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
        with _LANGUAGE_LOCK:
            return dict(self.items())

    def __repr__(self) -> str:
        with _LANGUAGE_LOCK:
            return repr(dict(self.items()))

    def __eq__(self, other) -> bool:
        if not isinstance(other, dict):
            return NotImplemented
        with _LANGUAGE_LOCK:
            return dict(self.items()) == other

    def __or__(self, other):
        with _LANGUAGE_LOCK:
            result = dict(self.items())
            result.update(other)
            return result

    def __ror__(self, other):
        with _LANGUAGE_LOCK:
            result = dict(other)
            result.update(self.items())
            return result


LANGUAGE_CODES = _LazyLanguageCodes()


def _evict_profile(code: str) -> None:
    """Drop the cached state for the class currently bound to ``code`` so a
    re-registration (or override) is rebuilt fresh.

    This drops both the cached :class:`LanguageProfile` (keyed on the language
    class) and the per-``Abbreviation``-class Aho-Corasick data (keyed on
    ``language_cls.Abbreviation``); otherwise a re-registered class whose
    abbreviation list changed would keep a stale automaton.

    Lock ordering (load-bearing): the two cache locks are acquired *sequentially*
    (never co-held) while the caller holds ``_LANGUAGE_LOCK``. No reader path ever
    acquires ``_LANGUAGE_LOCK`` while holding ``_PROFILE_CACHE_LOCK`` or
    ``_cache_lock``, so there is no lock-ordering cycle. Preserve that invariant.
    """
    from sentencesplit.abbreviation_replacer import AbbreviationReplacer
    from sentencesplit.language_profile import _PROFILE_CACHE, _PROFILE_CACHE_LOCK

    with _LANGUAGE_LOCK:
        existing = LANGUAGE_CODES.get(code)
    if existing is not None:
        with _PROFILE_CACHE_LOCK:
            _PROFILE_CACHE.pop(existing, None)
        abbr_class = getattr(existing, "Abbreviation", None)
        if abbr_class is not None:
            with AbbreviationReplacer._cache_lock:
                AbbreviationReplacer._data_cache.pop(abbr_class, None)


def register_language(code: str, language_cls: type) -> None:
    """Register (or override) a language class for an ISO 639-1 ``code``.

    ``LANGUAGE_CODES`` is a process-global registry shared by every
    ``Segmenter``. Registry mutations are locked, but callers should still
    register custom languages during startup so concurrent workers see a stable
    language set.
    """
    with _LANGUAGE_LOCK:
        _evict_profile(code)
        LANGUAGE_CODES[code] = language_cls


def unregister_language(code: str) -> None:
    """Remove a registered (or built-in) language ``code`` if present."""
    with _LANGUAGE_LOCK:
        _evict_profile(code)
        try:
            del LANGUAGE_CODES[code]
        except KeyError:
            pass


def list_languages() -> list[str]:
    """Return the supported ISO 639-1 language codes, sorted.

    Includes the built-in natural languages plus the special profiles
    ``en_es_zh`` and ``en_legal``, and reflects any languages added via
    :func:`register_language` (or removed via :func:`unregister_language`).

    Reading the list does **not** import any concrete language module, so it is
    cheap to call for discovery or for validating a ``language`` argument before
    constructing a :class:`~sentencesplit.segmenter.Segmenter`.
    """
    return sorted(LANGUAGE_CODES.keys())


class Language:
    def __init__(self, code: str) -> None:
        self.code = code

    @classmethod
    def get_language_code(cls, code: str):
        try:
            return LANGUAGE_CODES[code]
        except KeyError as err:
            raise UnknownLanguageError(
                "Provide valid language ID i.e. ISO code. Available codes are : {}".format(sorted(LANGUAGE_CODES.keys()))
            ) from err
