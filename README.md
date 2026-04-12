# sentencesplit

Rule-based sentence boundary detection that works out-of-the-box for 24 languages. Pure Python, zero dependencies.

## Why sentencesplit

Most sentence splitters choke on abbreviations, numbered references, initials, and other ambiguous periods. sentencesplit uses a deep rule engine (derived from [pySBD](https://github.com/nipunsadvilkar/pySBD) / [Pragmatic Segmenter](https://github.com/diasks2/pragmatic_segmenter)) to handle these correctly:

```python
import sentencesplit

seg = sentencesplit.Segmenter(language="en")
seg.segment("My name is Jonas E. Smith. Please turn to p. 55.")
# ['My name is Jonas E. Smith. ', 'Please turn to p. 55.']
```

Naive `split(".")` or regex-based splitters would break on `E.`, `p.`, and `55.` above. sentencesplit gets these right across English, Chinese, Japanese, Spanish, and 20+ other languages.

**What it's good at:**

- Abbreviations, honorifics, and initials (`Dr.`, `U.S.`, `p. 55`)
- CJK sentence-ending punctuation (`。`, `！`, `？`) with quote/bracket awareness
- Mixed-language text via the built-in `en_es_zh` combined profile
- Streaming/incremental input: `should_wait_for_more()` tells you if the last boundary might change as more text arrives
- Character-offset spans for downstream annotation, NER, or LLM token alignment
- Lists, parentheticals, ellipses, and OCR/PDF artifacts
- No model downloads, no GPU, no network calls -- just `pip install` and go

## Install

```
pip install sentencesplit
```

Python 3.11+. No dependencies to install.

## Quick start

### Basic segmentation

```python
import sentencesplit

seg = sentencesplit.Segmenter(language="en")
seg.segment("Dr. Smith called at 3 p.m. He said to see p. 55. Then he left.")
# ['Dr. Smith called at 3 p.m. ', 'He said to see p. 55. ', 'Then he left.']
```

### Character-offset spans

```python
seg = sentencesplit.Segmenter(language="en")
seg.segment_spans("My name is Jonas E. Smith. Please turn to p. 55.")
# [TextSpan(sent='My name is Jonas E. Smith. ', start=0, end=27),
#  TextSpan(sent='Please turn to p. 55.', start=27, end=48)]
```

`segment_spans()` always returns `TextSpan` objects with `.sent`, `.start`, `.end` regardless of the `char_span` constructor flag.

### Streaming / lookahead

When processing streaming text (e.g. LLM output), you often can't tell if the last period is truly the end of a sentence. sentencesplit can probe for you:

```python
seg = sentencesplit.Segmenter(language="en")

result = seg.segment_with_lookahead("The model is GPT 3.")
result.segments          # ['The model is GPT 3.']
result.should_wait_for_more  # True  -- "3." might continue as "3.5"

result = seg.segment_with_lookahead("This is the finale.")
result.should_wait_for_more  # False -- clearly a complete sentence
```

`should_wait_for_more()` works by appending tiny probe suffixes and re-running segmentation. If the final boundary changes, it returns `True`. This handles abbreviations, numeric decimals, and language-specific ambiguities without any special configuration.

### CJK languages

```python
seg = sentencesplit.Segmenter(language="zh")
seg.segment("这是第一句。这是第二句！这是第三句？")
# ['这是第一句。', '这是第二句！', '这是第三句？']
```

Chinese (`zh`) and Japanese (`ja`) use `CJKBoundaryProfile`, which recognizes CJK sentence-ending punctuation and closing quotes/brackets.

### Mixed-language text

Use the built-in `en_es_zh` profile for text that mixes English, Spanish, and Chinese:

```python
seg = sentencesplit.Segmenter(language="en_es_zh")
seg.segment("Hola Sr. Lopez. This is Dr. Wang. 今天天气很好。")
# ['Hola Sr. Lopez. ', 'This is Dr. Wang. ', '今天天气很好。']
```

You can build your own combined profile by merging abbreviation lists from any languages that share the same writing system. See [Multi-language segmentation](#multi-language-segmentation) below.

### Split mode

Controls how aggressively abbreviation-period ambiguity is resolved:

```python
# Default: conservative -- fewer splits, preserves abbreviation boundaries
seg = sentencesplit.Segmenter(language="en", split_mode="conservative")

# Aggressive: more splits at ambiguous abbreviation periods (e.g. "St.")
seg = sentencesplit.Segmenter(language="en", split_mode="aggressive")
```

### spaCy integration

sentencesplit registers as a [spaCy pipeline component](https://spacy.io/usage/processing-pipelines) via entry points:

```python
import spacy

nlp = spacy.blank("en")
nlp.add_pipe("sentencesplit")

doc = nlp("My name is Jonas E. Smith. Please turn to p. 55.")
print(list(doc.sents))
# [My name is Jonas E. Smith., Please turn to p. 55.]
```

See [examples/sentencesplit_as_spacy_component.py](examples/sentencesplit_as_spacy_component.py) for more.

### PDF / OCR text

```python
seg = sentencesplit.Segmenter(language="en", clean=True, doc_type="pdf")
seg.segment(ocr_text)
```

`clean=True` normalizes HTML entities, escaped newlines, and PDF line-break artifacts before segmenting.

## Supported languages

24 languages with ISO 639-1 codes, plus 2 specialized profiles:

| Code | Language | Code | Language | Code | Language |
|------|----------|------|----------|------|----------|
| `am` | Amharic | `fa` | Persian | `mr` | Marathi |
| `ar` | Arabic | `fr` | French | `my` | Burmese |
| `bg` | Bulgarian | `el` | Greek | `nl` | Dutch |
| `da` | Danish | `hi` | Hindi | `pl` | Polish |
| `de` | German | `hy` | Armenian | `ru` | Russian |
| `en` | English | `it` | Italian | `sk` | Slovak |
| `es` | Spanish | `ja` | Japanese | `tl` | Tagalog |
| `kk` | Kazakh | `zh` | Chinese | `ur` | Urdu |

**Specialized profiles:** `en_es_zh` (combined English/Spanish/Chinese), `en_legal` (English legal text).

## Multi-language segmentation

Languages with similar writing systems can be combined into a single segmenter by merging their abbreviation lists. This avoids needing to detect the language of each sentence before segmenting.

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
# ['Hola Srta. Ledesma. ', 'How are you?']
```

This works well for languages that share the `Common` and `Standard` base classes and use the same sentence-ending punctuation (`.`, `!`, `?`). The same pattern can be extended to other similar languages like Italian, Dutch, or Danish. Languages with different writing systems or punctuation (e.g. Japanese, Arabic) would need a different approach.

## Custom processor hooks

If you need to customize segmentation beyond regex tables and abbreviation lists, override `Processor` hooks on your language class.

The processor treats most hooks as pure transformations:

- `replace_abbreviations(text: str) -> str`
- `replace_numbers(text: str) -> str`
- `replace_continuous_punctuation(text: str) -> str`
- `replace_periods_before_numeric_references(text: str) -> str`
- `between_punctuation(text: str) -> str`
- `split_into_segments(text: str | None = None) -> list[str]`
- `_resplit_segments(sentences: list[str]) -> list[str]`
- `_merge_orphan_fragments(sentences: list[str]) -> list[str]`

For most languages, overriding one or two of these hooks is enough. Prefer calling `super()` and transforming the returned text instead of mutating `self.text` directly.

```python
from sentencesplit.lang.common import Common, Standard
from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.processor import Processor


class Demo(Common, Standard):
    iso_code = "demo"

    class Processor(Processor):
        def replace_numbers(self, text: str) -> str:
            text = super().replace_numbers(text)
            # Example: protect section markers like "§. 5"
            return text.replace("§.", "§∯")

        def _resplit_segments(self, sentences: list[str]) -> list[str]:
            # Reuse the default resplit logic, then add project-specific tweaks.
            return super()._resplit_segments(sentences)


LANGUAGE_CODES["demo"] = Demo
```

`sentencesplit.language_profile.LanguageProfile` is the internal adapter that resolves these hooks and compiled regexes for the processor. It is useful for contributors working on the engine, but it is not intended as a stable public extension API.

## Releasing

Releases are published manually from GitHub Actions.

One-time setup:

1. In GitHub, create an environment named `pypi`.
2. In PyPI, add a Trusted Publisher for repo `yisding/sentencesplit`, workflow `.github/workflows/publish.yml`, and environment `pypi`.

Release steps:

1. Merge the code you want to publish into `main`.
2. Open GitHub Actions and run the `Release` workflow on `main`.
3. Choose the version bump: `patch`, `minor`, `major`, or `prerelease`.
4. Set `dry_run=true` to preview the release, then run it again with `dry_run=false` for the real release.
5. The workflow creates the version commit, tag, changelog update, and GitHub Release.
6. After the release step succeeds, the `Release` workflow calls the separate `Publish to PyPI` workflow, which checks out the new tag and uploads the built distributions using Trusted Publishing.
7. If you need to publish an already-created release tag, run `Publish to PyPI` manually and enter the existing tag, for example `v0.0.1`.

`python-semantic-release` uses Conventional Commits to generate changelog entries, so commit messages like `fix: ...`, `feat: ...`, and `feat!: ...` are recommended.

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
