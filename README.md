# sentencesplit

> **Derived from [pySBD](https://github.com/nipunsadvilkar/pySBD)** (Python Sentence Boundary Disambiguation) by Nipun Sadvilkar.

sentencesplit is a rule-based sentence boundary detection library that works out-of-the-box across many languages.

This project is a direct port of ruby gem - [Pragmatic Segmenter](https://github.com/diasks2/pragmatic_segmenter) which provides rule-based sentence boundary detection.

## Install

**Python 3.11+ required.**

    pip install sentencesplit

## Usage

-   Currently sentencesplit supports 23 languages.

```python
import sentencesplit
text = "My name is Jonas E. Smith. Please turn to p. 55."
seg = sentencesplit.Segmenter(language="en", clean=False)
print(seg.segment(text))
# ['My name is Jonas E. Smith.', 'Please turn to p. 55.']
```

-   Use `sentencesplit` as a [spaCy](https://spacy.io/usage/processing-pipelines) pipeline component. (recommended)</br>Please refer to example [sentencesplit\_as\_spacy\_component.py](examples/sentencesplit_as_spacy_component.py)
- Use sentencesplit through [entry points](https://spacy.io/usage/saving-loading#entry-points-components)

```python
import spacy

nlp = spacy.blank('en')

# add sentencesplit component registered via package entry points
nlp.add_pipe("sentencesplit")

doc = nlp('My name is Jonas E. Smith. Please turn to p. 55.')
print(list(doc.sents))
# [My name is Jonas E. Smith., Please turn to p. 55.]

```

## Multi-language segmentation

Languages with similar writing systems (e.g. English, Spanish, French) can be combined into a single segmenter by merging their abbreviation lists. This avoids needing to detect the language of each sentence before segmenting.

```python
import sentencesplit
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.english import English
from sentencesplit.lang.spanish import Spanish
from sentencesplit.lang.french import French
from sentencesplit.languages import LANGUAGE_CODES

class MultiLang(Common, Standard):
    iso_code = 'multi'

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = sorted(set(
            Standard.Abbreviation.ABBREVIATIONS +
            Spanish.Abbreviation.ABBREVIATIONS +
            French.Abbreviation.ABBREVIATIONS
        ))
        PREPOSITIVE_ABBREVIATIONS = sorted(set(
            Standard.Abbreviation.PREPOSITIVE_ABBREVIATIONS +
            Spanish.Abbreviation.PREPOSITIVE_ABBREVIATIONS +
            French.Abbreviation.PREPOSITIVE_ABBREVIATIONS
        ))
        NUMBER_ABBREVIATIONS = sorted(set(
            Standard.Abbreviation.NUMBER_ABBREVIATIONS +
            Spanish.Abbreviation.NUMBER_ABBREVIATIONS +
            French.Abbreviation.NUMBER_ABBREVIATIONS
        ))

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = English.AbbreviationReplacer.SENTENCE_STARTERS

LANGUAGE_CODES['multi'] = MultiLang

seg = sentencesplit.Segmenter(language="multi", clean=False)
print(seg.segment("Hola Srta. Ledesma. How are you?"))
# ['Hola Srta. Ledesma.', 'How are you?']
```

This works well for languages that share the `Common` and `Standard` base classes and use the same sentence-ending punctuation (`.`, `!`, `?`). The same pattern can be extended to other similar languages like Italian, Dutch, or Danish. Languages with different writing systems or punctuation (e.g. Japanese, Arabic) would need a different approach.

## Contributing

If you want to contribute new feature/language support or found a text that is incorrectly segmented, then please head to [CONTRIBUTING.md](CONTRIBUTING.md) to know more and follow these steps.

1.  Fork it
2.  Create your feature branch (`git checkout -b my-new-feature`)
3.  Commit your changes (`git commit -am 'Add some feature'`)
4.  Push to the branch (`git push origin my-new-feature`)
5.  Create a new Pull Request

## Citation
This project is derived from pySBD. If you use it in your projects or research, please cite the original [PySBD: Pragmatic Sentence Boundary Disambiguation](https://www.aclweb.org/anthology/2020.nlposs-1.15) paper.
```
@inproceedings{sadvilkar-neumann-2020-pysbd,
    title = "{P}y{SBD}: Pragmatic Sentence Boundary Disambiguation",
    author = "Sadvilkar, Nipun  and
      Neumann, Mark",
    booktitle = "Proceedings of Second Workshop for NLP Open Source Software (NLP-OSS)",
    month = nov,
    year = "2020",
    address = "Online",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/2020.nlposs-1.15",
    pages = "110--114",
    abstract = "We present a rule-based sentence boundary disambiguation Python package that works out-of-the-box for 22 languages. We aim to provide a realistic segmenter which can provide logical sentences even when the format and domain of the input text is unknown. In our work, we adapt the Golden Rules Set (a language specific set of sentence boundary exemplars) originally implemented as a ruby gem pragmatic segmenter which we ported to Python with additional improvements and functionality. PySBD passes 97.92{\%} of the Golden Rule Set examplars for English, an improvement of 25{\%} over the next best open source Python tool.",
}
```

## Credit

This project is derived from [pySBD](https://github.com/nipunsadvilkar/pySBD) by Nipun Sadvilkar, which itself wouldn't be possible without the great work done by the [Pragmatic Segmenter](https://github.com/diasks2/pragmatic_segmenter) team.
