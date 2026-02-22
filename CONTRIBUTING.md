# Contributing to sentencesplit
Thanks for your interest in contributing to sentencesplit. This project is derived from [pySBD](https://github.com/nipunsadvilkar/pySBD) by [@nipunsadvilkar](https://github.com/nipunsadvilkar). This page will give you a quick overview of how things are organised and most importantly, how to get involved.

## Table of contents

1. [Issues and bug reports](#issues-and-bug-reports)</br>
    a. [Submitting issues](#submitting-issues)
2. [Contributing to the code base](#contributing-to-the-code-base)</br>
    a. [Getting started](#getting-started)</br>
    b. [Add a new rule to existing *Golden Rules Set* (GRS)](#add-a-new-rule-to-existing-golden-rules-set-grs)</br>
    c. [Add new language support](#add-new-language-support)</br>
    d. [Add tests](#add-tests)</br>
    e. [Fix bugs](#fix-bugs)

## Issues and bug reports
Please do a quick search to see if the issue has already been reported or is already open. If so, it's often better to just leave a comment on an existing issue, rather than creating a new one.

### Submitting issues

When opening an issue, use an **appropriate and descriptive title** and include your
**environment** (operating system, Python version, sentencesplit version).

-   **Describing your issue:** Try to provide as many details as possible. What
    exactly goes wrong? _How_ is it failing? Is there an error?
    "XY doesn't work" usually isn't that helpful for tracking down problems. Always
    remember to include the code you ran and if possible, extract only the relevant
    parts and don't just dump your entire script. Also, provide what was the expected output for given input. This will make it easier for contributors to
    reproduce the error.

-   **Getting info about your sentencesplit installation and environment:** You can use the command line interface to print details:
    `pip freeze|grep sentencesplit`.

-   **Sharing long blocks of code/logs/tracebacks:** If you need to include long code,
    logs or tracebacks, you can wrap them in `<details>` and `</details>`. This
    [collapses the content](https://developer.mozilla.org/en/docs/Web/HTML/Element/details)
    so it only becomes visible on click, making the issue easier to read and follow.

## Contributing to the code base

To understand the internals of this project, a good place to start is to refer to the implementation section of the [pySBD research paper](https://arxiv.org/abs/2010.09657).

### Getting started
To make changes to the code base, you need to fork then clone the GitHub repository. You'll need Python 3.11+, pip and git installed.

```python
python -m pip install -U pip
git clone https://github.com/yisding/pySBD
cd pySBD
pip install -e ".[dev]"
```
Since sentencesplit is lightweight, it requires only Python built-in modules, specifically the `re` module, to function. Development packages are provided through the `dev` extra in `pyproject.toml`. If you want benchmark dependencies (`spacy`, `stanza`, etc.), install `pip install -e ".[benchmark]"`.

### Add a new rule to existing *Golden Rules Set* (GRS)
The language specific *Golden Rules Set* are hand-constructed rules, designed to cover sentence boundaries across a variety of domains. The set is by no means complete and will evolve and expand over time. If you would like to report an issue in an existing rule or report a new rule, please [open an issue.](#submitting-issues) If you want to contribute yourself then please go ahead and send a pull request by referring to the [add tests](#add-tests) section.

### Add new language support
You would need the following steps to add new language support:

1. **New Language Specific *Golden Rules Set***</br>
You would need to create a *Golden Rule Set* representing basic to complex sentence boundary variations as a test set. Create a new file at `tests/lang/test_<language_name>.py` and enlist input text and expected output in the same way existing languages are supported. You may want to refer to [adding tests](#adding-tests) for more details. Next, run the tests using `pytest` and let them deliberately fail.

2. **Add your language module**</br>
Create a new file at `sentencesplit/lang/<language_name>.py` and define a new class `LanguageName` which should inherit from two base classes - `Common, Standard` - involving basic rules common across the majority of languages. Try running tests to see if your GRS passes. If it fails, you would need to override `SENTENCE_BOUNDARY_REGEX`, `Punctuations` class variables and `AbbreviationReplacer` class to support your language-specific punctuations and sentence boundaries.

3. **Add language code**<br>
Your language module & language GRS should be in place by now. Next, make it available in the [`languages`](sentencesplit/languages.py) module by importing your language module and adding a new key with the [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) language code to the `LANGUAGE_CODES` dictionary.

### Add tests
We emphasize Test-Driven Development [(TDD)](https://testdriven.io/test-driven-development/) to ensure robustness. Follow a "Red-Green-Refactor" cycle.

1. Make sure you have a proper development environment [setup](#getting-started)
2. Depending on your type of contribution, your test script would vary between [feature-specific](#add-new-language-support) / [bugfix-specific](#fix-bugs).
3. (Red) Once you add those tests, run `pytest` to make sure they fail deliberately.
4. (Green) Write just enough code to pass the specific test that failed earlier.
5. Once it passes, run all the tests to see if your added code doesn't break existing code.
6. (Refactor) Do necessary refactoring & cleaning to keep tests green.
7. Repeat

### Fix bug(s)

When fixing a bug, first create an issue if one does not already exist.

Next, depending on your type of issue, add your test in `TEST_ISSUE_DATA` / `TEST_ISSUE_DATA_CHAR_SPANS` with a tuple `("#ISSUE_NUMBER", "<input_text>", <expected_output>)` in the
[`tests/regression`](tests/regression) folder. Test for the bug
you're fixing, and make sure the test fails. Next, add and commit your test file
referencing the issue number in the commit message. Finally, fix the bug, make
sure your test passes and reference the issue in your commit message.

Thank you for contributing!
