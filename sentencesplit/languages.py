# -*- coding: utf-8 -*-
from sentencesplit.lang.amharic import Amharic
from sentencesplit.lang.arabic import Arabic
from sentencesplit.lang.armenian import Armenian
from sentencesplit.lang.bulgarian import Bulgarian
from sentencesplit.lang.burmese import Burmese
from sentencesplit.lang.chinese import Chinese
from sentencesplit.lang.danish import Danish
from sentencesplit.lang.deutsch import Deutsch
from sentencesplit.lang.dutch import Dutch
from sentencesplit.lang.english import English
from sentencesplit.lang.french import French
from sentencesplit.lang.greek import Greek
from sentencesplit.lang.hindi import Hindi
from sentencesplit.lang.italian import Italian
from sentencesplit.lang.japanese import Japanese
from sentencesplit.lang.kazakh import Kazakh
from sentencesplit.lang.marathi import Marathi
from sentencesplit.lang.persian import Persian
from sentencesplit.lang.polish import Polish
from sentencesplit.lang.russian import Russian
from sentencesplit.lang.slovak import Slovak
from sentencesplit.lang.spanish import Spanish
from sentencesplit.lang.urdu import Urdu

LANGUAGE_CODES = {
    "en": English,
    "hi": Hindi,
    "mr": Marathi,
    "zh": Chinese,
    "es": Spanish,
    "am": Amharic,
    "ar": Arabic,
    "hy": Armenian,
    "bg": Bulgarian,
    "ur": Urdu,
    "ru": Russian,
    "pl": Polish,
    "fa": Persian,
    "nl": Dutch,
    "da": Danish,
    "fr": French,
    "my": Burmese,
    "el": Greek,
    "it": Italian,
    "ja": Japanese,
    "de": Deutsch,
    "kk": Kazakh,
    "sk": Slovak,
}


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
