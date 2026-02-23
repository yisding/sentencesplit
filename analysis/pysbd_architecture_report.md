# pySBD Regex Architecture: Comprehensive Analysis

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Overview](#2-architectural-overview)
3. [The Core Idea: Protect-Split-Restore](#3-the-core-idea-protect-split-restore)
4. [File-by-File Analysis](#4-file-by-file-analysis)
   - 4.1 [utils.py — Rule Primitive](#41-utilspy--rule-primitive)
   - 4.2 [segmenter.py — Entry Point](#42-segmenterpy--entry-point)
   - 4.3 [processor.py — Pipeline Orchestrator](#43-processorpy--pipeline-orchestrator)
   - 4.4 [abbreviation_replacer.py — Aho-Corasick + Regex Hybrid](#44-abbreviation_replacerpy--aho-corasick--regex-hybrid)
   - 4.5 [between_punctuation.py — Quoted Region Protection](#45-between_punctuationpy--quoted-region-protection)
   - 4.6 [punctuation_replacer.py — Symbol Substitution Engine](#46-punctuation_replacerpy--symbol-substitution-engine)
   - 4.7 [exclamation_words.py — Lexical Exceptions](#47-exclamation_wordspy--lexical-exceptions)
   - 4.8 [lists_item_replacer.py — Structural Pattern Detection](#48-lists_item_replacerpy--structural-pattern-detection)
   - 4.9 [cleaner.py + clean/rules.py — Pre-processing](#49-cleanerpy--cleanrulespy--pre-processing)
   - 4.10 [lang/common/common.py — Shared Regex Patterns](#410-langcommoncommonpy--shared-regex-patterns)
   - 4.11 [lang/common/standard.py — Standard Rules & Abbreviations](#411-langcommonstandardpy--standard-rules--abbreviations)
   - 4.12 [Language Modules](#412-language-modules)
   - 4.13 [spacy_component.py — Integration Bridge](#413-spacy_componentpy--integration-bridge)
5. [Complete Regex Catalog](#5-complete-regex-catalog)
6. [Sentinel Character Map](#6-sentinel-character-map)
7. [Pipeline Execution Order](#7-pipeline-execution-order)
8. [Regex Design Patterns Used](#8-regex-design-patterns-used)
9. [Potential Issues and Edge Cases](#9-potential-issues-and-edge-cases)
10. [Conclusion](#10-conclusion)

---

## 1. Executive Summary

pySBD is a rule-based sentence boundary detection system that uses **~80 distinct regex patterns** organized in a multi-pass pipeline. Rather than attempting a single monolithic regex to classify sentence boundaries, it employs a **protect-split-restore** strategy: ambiguous punctuation is temporarily replaced with Unicode sentinel characters, the text is split on the now-unambiguous remaining punctuation, and the sentinels are restored to their original characters.

The system supports 23 languages through a class inheritance hierarchy where language-specific modules override abbreviation lists, boundary regexes, and processing steps. Performance-critical abbreviation matching uses an Aho-Corasick automaton for O(n) multi-pattern scanning, while simpler rules use pre-compiled `re.compile()` patterns wrapped in `Rule` objects.

---

## 2. Architectural Overview

```
                          Segmenter (segmenter.py)
                         /          |              \
                   Cleaner    Processor        _match_spans
                  (optional)   (always)        (if char_span)
                      |            |
                 clean/rules   Delegates to:
                               ├── ListItemReplacer
                               ├── AbbreviationReplacer (with AhoCorasickAutomaton)
                               ├── ExclamationWords
                               ├── BetweenPunctuation
                               ├── PunctuationReplacer
                               └── SENTENCE_BOUNDARY_REGEX (final split)
```

**Class inheritance for languages:**
```
Common (base regex patterns)
  └── Standard (rules, abbreviations, punctuation lists)
        ├── English (inherits everything, adds SENTENCE_STARTERS)
        ├── Spanish (custom abbreviation list)
        ├── German (custom Numbers, Processor, BetweenPunctuation)
        ├── Japanese (custom Cleaner, BetweenPunctuation)
        ├── Hindi (entirely different SENTENCE_BOUNDARY_REGEX)
        ├── Arabic (different regex + colon/comma rules)
        └── ... 16 more languages
```

---

## 3. The Core Idea: Protect-Split-Restore

The fundamental design insight is converting a **classification problem** into an **elimination problem**.

Instead of asking "is this `.` a sentence boundary?" (hard — requires context), pySBD asks "is this `.` **definitely not** a sentence boundary?" (easier — can be answered by pattern matching). Each pipeline stage identifies one category of non-boundary punctuation and replaces it with a sentinel. After all stages, any remaining `.`, `!`, `?` is a genuine boundary by process of elimination.

**Example walkthrough:**
```
Input:  "Dr. Smith went to Washington. He arrived at 5 p.m. EST."

Stage 1 (abbreviations):    "Dr∯ Smith went to Washington. He arrived at 5 p∯m∯ EST."
         ^^                                                         ^^^  ^^
         "Dr." is prepositive → protect    "p.m." matches AmPmRules → protect

Stage 2 (sentence boundary): Split on remaining "." characters
         → ["Dr∯ Smith went to Washington.", "He arrived at 5 p∯m∯ EST."]

Stage 3 (restore):           → ["Dr. Smith went to Washington.", "He arrived at 5 p.m. EST."]
```

---

## 4. File-by-File Analysis

### 4.1 `utils.py` — Rule Primitive

**Lines:** 55 | **Regexes defined:** 0 (provides the framework)

The `Rule` class is the atomic unit of regex processing throughout the codebase:

```python
class Rule:
    def __init__(self, pattern: str, replacement: str, flags: int = 0):
        self.pattern = pattern
        self.replacement = replacement
        self.regex: Pattern[str] = re.compile(pattern, flags)
```

Every `Rule` pre-compiles its regex at class definition time (module load), not at call time. The `apply_rules()` function chains multiple rules sequentially:

```python
def apply_rules(text: str, *rules: Rule) -> str:
    for rule in rules:
        text = rule.regex.sub(rule.replacement, text)
    return text
```

This is the workhorse that 90% of the codebase feeds into. Each rule is a `(regex, replacement)` pair applied via `re.sub()`. Rules are stateless and composable.

`TextSpan` is a simple data class holding `(sent, start, end)` tuples for character offset tracking.

**Design note:** Rules compile eagerly at import time. This means the first `import pysbd` pays a one-time cost to compile all ~80 patterns. Subsequent calls are fast.

---

### 4.2 `segmenter.py` — Entry Point

**Lines:** 123 | **Regexes defined:** 1 inline

The `Segmenter` class is the public API. Key design decisions:

1. **Mutual exclusion of `clean` and `char_span`**: Cleaning modifies text, so character offsets become invalid. This is enforced with a `ValueError`.

2. **Language module dispatch**: `hasattr()` checks determine whether to use a language-specific override:
   ```python
   if hasattr(self.language_module, "Cleaner"):
       return self.language_module.Cleaner(text, ...)
   else:
       return Cleaner(text, ...)
   ```

3. **Span matching** (`_match_spans`): After segmentation produces sentence strings, this method maps them back to positions in the original text using `str.find()` with a `prior_end` cursor. If `find()` fails (rare edge cases), it falls back to `re.finditer()`:
   ```python
   re.finditer(rf'{re.escape(sent)}\s*', original_text)
   ```
   This fallback handles cases where whitespace normalization during processing causes an exact substring match to fail. The `\s*` suffix captures trailing whitespace to ensure non-destructive segmentation (no characters lost between sentences).

4. **Non-destructive default**: Even without `char_span=True`, the `segment()` method returns original text slices (via `_match_spans`) rather than processed text, preserving the user's original whitespace and formatting.

---

### 4.3 `processor.py` — Pipeline Orchestrator

**Lines:** 181 | **Regexes defined:** 4 pre-compiled + 3 inline

This is the heart of the system. The `process()` method defines the pipeline execution order.

**Pre-compiled module-level patterns** (hot path optimization):

| Pattern | Purpose |
|---------|---------|
| `_ALPHA_ONLY_RE = r'\A[a-zA-Z]*\Z'` | Fast skip: segments that are pure letters need no post-processing |
| `_TRAILING_EXCL_RE = r'&ᓴ&$'` | Restore `!` if it's the final character (was protected but is actually a boundary) |
| `_PAREN_SPACE_BEFORE_RE = r'\s(?=\()'` | Space before paren → sentence break in quotes-between-parens |
| `_PAREN_SPACE_AFTER_RE = r'(?<=\))\s'` | Space after paren → sentence break in quotes-between-parens |

**`_sub_symbols_fast()`**: Uses `str.replace()` instead of regex for sentinel restoration — all sentinels are literal strings, so regex overhead is unnecessary. This is a deliberate performance optimization.

**`process()` pipeline:**

```
1. text.replace('\n', '\r')          — Normalize newlines to internal boundary marker
2. ListItemReplacer.add_line_break() — Detect lists, insert \r boundaries
3. replace_abbreviations()           — Abbreviation periods → ∯
4. replace_numbers()                 — Number periods → ∯
5. replace_continuous_punctuation()  — !!!/?? → sentinel sequences
6. replace_periods_before_numeric_references() — [1] footnotes
7. apply_rules(WithMultiplePeriodsAndEmailRule, GeoLocationRule, FileFormatRule)
8. split_into_segments()             — The actual split
```

**`split_into_segments()`** sub-pipeline:

```
1. Split on \r markers
2. Apply SingleNewLineRule + EllipsisRules to each segment
3. check_for_punctuation() on each → process_text() if punctuation present
4. Restore sentinels via _sub_symbols_fast()
5. post_process_segments() — handle quotation splits, strip whitespace
6. Apply SubSingleQuoteRule
```

**`process_text()`** sub-pipeline (called per segment that contains punctuation):

```
1. If text doesn't end with punctuation → append ȸ (synthetic end marker)
2. ExclamationWords.apply_rules()
3. between_punctuation() — protect !/? inside quotes/brackets
4. DoublePunctuationRules — ?! → ☉, !? → ☈, ?? → ☇, !! → ☄
5. QuestionMarkInQuotationRule + ExclamationPointRules
6. ListItemReplacer.replace_parens() — Roman numerals in parens
7. sentence_boundary_punctuation() — THE FINAL SPLIT via SENTENCE_BOUNDARY_REGEX
```

**Key inline regex — `replace_continuous_punctuation()`:**
```python
CONTINUOUS_PUNCTUATION_REGEX = r'(?<=\S)(!|\?){3,}(?=(\s|\Z|$))'
```
Matches 3+ consecutive `!` or `?` preceded by a non-space and followed by whitespace/end. The callback replaces `!` → `&ᓴ&` and `?` → `&ᓷ&` within the match, preventing the splitter from treating `!!!` as three separate sentence boundaries.

**Key inline regex — `replace_periods_before_numeric_references()`:**
```python
NUMBERED_REFERENCE_REGEX = r'(?<=[^\d\s])(\.|∯)((\[(\d{1,3},?\s?-?\s?)?\b\d{1,3}\])+|((\d{1,3}\s?){0,3}\d{1,3}))(\s)(?=[A-Z])'
```
This handles academic-style references like `sentence.[1] Next` or `sentence.2 Next`. The lookbehind `(?<=[^\d\s])` ensures it's not a decimal number. The replacement `r"∯\2\r\7"` protects the period and inserts a sentence break.

---

### 4.4 `abbreviation_replacer.py` — Aho-Corasick + Regex Hybrid

**Lines:** 210 | **Regexes defined:** 2 per abbreviation (dynamically compiled) + 4 inline

This is the most algorithmically sophisticated file.

**`AhoCorasickAutomaton`**: A pure-Python implementation of the Aho-Corasick multi-pattern string matching algorithm. It builds a finite automaton from all abbreviation patterns, then scans the input text in a single O(n) pass to find all matches simultaneously. This replaces what would otherwise be 185+ individual regex scans for English.

**`_AbbreviationData`**: Pre-computed per-language data, cached by class identity (`id(lang.Abbreviation)`):

```python
class _AbbreviationData:
    __slots__ = ('abbreviations', 'prepositive_set', 'number_abbr_set', 'automaton')
```

For each abbreviation, it pre-computes:
- `match_re`: `re.compile(r"(?:^|\s|\r|\n){}".format(escaped))` — Finds the abbreviation preceded by a word boundary
- `next_word_re`: `re.compile(r"(?<={escaped} ).{1}")` — Captures the first character after the abbreviation's period and space

**`replace()` pipeline:**

```
1. Apply global rules: PossessiveAbbreviationRule, KommanditgesellschaftRule, SingleLetterAbbreviationRules
2. For each line: search_for_abbreviations_in_string()
   a. Lowercase the text → Aho-Corasick scan → get matched abbreviation indices
   b. For each match: check if abbreviation actually appears (case-sensitive regex)
   c. Look at next character after period:
      - lowercase → always protect (not a boundary)
      - uppercase + prepositive abbreviation → protect ("Dr. Smith")
      - uppercase + NOT prepositive → keep as boundary ("etc. He")
      - digit + number abbreviation → protect ("p. 55")
3. replace_multi_period_abbreviations() — "U.S.A." → "U∯S∯A∯"
4. Apply AmPmRules (with timezone awareness)
5. replace_abbreviation_as_sentence_boundary() — Undo protection when followed by a sentence starter
```

**`replace_period_of_abbr()`** — The general-case abbreviation handler:
```python
r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())))".format(abbr=escaped)
```
This lookbehind finds the abbreviation, then looks ahead to determine if the period should be protected. The lookahead accepts:
- Another `.`, `:`, `-`, `?`, `,` — clearly not a sentence boundary
- A lowercase letter — next sentence wouldn't start lowercase
- `I `, `I'm`, `I'll` — special cases where "I" is not a sentence-starting capital
- A digit or `(` — continuation of the same sentence

**`replace_abbreviation_as_sentence_boundary()`:**
```python
regex = r"(U∯S|U\.S|U∯K|E∯U|E\.U|U∯S∯A|U\.S\.A|I|i.v|I.V)∯({})".format(sent_starters)
```
This is a correction pass. After abbreviation protection, patterns like `U.S. He went...` will have been over-protected. If the word following the abbreviation is a known sentence starter (A, Being, Did, For, He, How, However, I, In, It, Millions, More, She, That, The, There, They, We, What, When, Where, Who, Why), the period is restored as a genuine boundary.

**`_replace_with_escape()`** helper:
```python
def _replace_with_escape(txt, escaped, suffix_pattern, replacement):
    txt = " " + txt  # Ensure lookbehind can match at start
    txt = re.sub(rf"(?<=\s{escaped}){suffix_pattern}", replacement, txt)
    return txt[1:]    # Remove prepended space
```
The space prepend is a clever workaround for Python's fixed-width lookbehind limitation. By ensuring the abbreviation is always preceded by a space, the lookbehind pattern works consistently.

---

### 4.5 `between_punctuation.py` — Quoted Region Protection

**Lines:** 84 | **Regexes defined:** 9 pre-compiled

This module protects sentence-ending punctuation that appears inside quoted or bracketed regions. Its approach: match the entire quoted region, then replace all `!`, `?`, `.` within it with sentinels.

**The `_REGEX_2` patterns** use a workaround for Python's lack of atomic groups:

```python
BETWEEN_DOUBLE_QUOTES_REGEX_2 = re.compile(r'"(?=(?P<tmp>[^\"\\]+|\\{2}|\\.)*)(?P=tmp)"')
```

This is a self-referencing pattern: the lookahead `(?=(?P<tmp>...))` captures content into group `tmp`, then `(?P=tmp)` backreferences it. This simulates atomic grouping by preventing the regex engine from backtracking into the quoted content — if the initial match of the content succeeds, the backreference commits to it.

**Pattern breakdown for each quote type:**

| Pattern | Matches | Example |
|---------|---------|---------|
| `BETWEEN_SINGLE_QUOTES_REGEX` | `'...'` after whitespace, with apostrophe exceptions | `'Hello! World'` |
| `BETWEEN_SINGLE_QUOTE_SLANTED_REGEX` | `\u2018...\u2019` (curly single quotes) | `\u2018Hello!\u2019` |
| `BETWEEN_DOUBLE_QUOTES_REGEX_2` | `"..."` with escape handling | `"Really? Yes."` |
| `BETWEEN_QUOTE_ARROW_REGEX_2` | `\u00ab...\u00bb` (guillemets «...») | `«Vraiment?»` |
| `BETWEEN_QUOTE_SLANTED_REGEX_2` | `\u201c...\u201d` (curly double quotes) | `\u201cReally?\u201d` |
| `BETWEEN_SQUARE_BRACKETS_REGEX_2` | `[...]` | `[see note 1?]` |
| `BETWEEN_PARENS_REGEX_2` | `(...)` | `(is this true?)` |
| `BETWEEN_EM_DASHES_REGEX_2` | `--...--` | `--really?--` |

**Apostrophe disambiguation:**
```python
def sub_punctuation_between_single_quotes(self, txt):
    if self.WORD_WITH_LEADING_APOSTROPHE.search(txt) and \
            (not self._QUOTE_SPACE_RE.search(txt)):
        return txt  # It's an apostrophe, not a quote
```
`WORD_WITH_LEADING_APOSTROPHE = r"(?<=\s)'(?:[^']|'[a-zA-Z])*'\S"` detects cases like `don't` where `'` is an apostrophe. If a leading apostrophe is found AND there's no `' ` (quote-space) pattern, the text is left unmodified — the `'` marks are apostrophes, not quotes.

---

### 4.6 `punctuation_replacer.py` — Symbol Substitution Engine

**Lines:** 74 | **Regexes defined:** 10 (via Rule classes, for backward compatibility)

The core function is `replace_punctuation()`, called as a `re.sub()` callback from `between_punctuation.py` and `exclamation_words.py`:

```python
_PUNCT_SUBS = [
    ('.', '∯'), ('。', '&ᓰ&'), ('．', '&ᓱ&'),
    ('！', '&ᓳ&'), ('!', '&ᓴ&'), ('?', '&ᓷ&'), ('？', '&ᓸ&'),
]
```

This replaces ALL sentence-ending punctuation within a matched region (e.g., inside quotes). Since the replacements are literal characters, `str.replace()` is used instead of regex.

**Escape handling for regex-reserved characters:**
```python
_ESCAPE_PAIRS = [('(', '\\('), (')', '\\)'), ('[', '\\['), (']', '\\]'), ('-', '\\-')]
```
If the matched region contains `()[]` or `-`, these are temporarily escaped before punctuation replacement, then unescaped afterward. This prevents the substituted text from being misinterpreted if it's later used in a regex context.

**Single quote handling:** When `match_type != 'single'`, single quotes are also replaced:
```python
text = text.replace("'", '&⎋&')
```
This prevents single quotes inside double-quoted regions from interfering with later single-quote detection.

---

### 4.7 `exclamation_words.py` — Lexical Exceptions

**Lines:** 20 | **Regexes defined:** 1 (dynamically built alternation)

Handles words that contain exclamation points as part of their spelling:

```python
EXCLAMATION_WORDS = "!Xũ !Kung ǃʼOǃKung !Xuun !Kung-Ekoka ǃHu ǃKhung ǃKu ǃung ǃXo ǃXû ǃXung ǃXũ !Xun Yahoo! Y!J Yum!".split()
EXCLAMATION_REGEX = r"|".join(re.escape(w) for w in EXCLAMATION_WORDS)
```

The regex is a simple alternation of escaped literal strings. When a match is found, `replace_punctuation()` replaces the `!` within the word with `&ᓴ&`, preventing it from being treated as a sentence boundary.

This list includes Khoisan language click consonants (written with `!` and `ǃ`) and brand names (Yahoo!, Yum!).

---

### 4.8 `lists_item_replacer.py` — Structural Pattern Detection

**Lines:** 249 | **Regexes defined:** 12

This module detects numbered and alphabetical lists, replacing their periods/parentheses with sentinels and inserting `\r` sentence boundaries between list items.

**Key regexes:**

| Name | Pattern | Purpose |
|------|---------|---------|
| `ALPHABETICAL_LIST_WITH_PERIODS` | `(?<=^)[a-z](?=\.)\|(?<=\A)[a-z](?=\.)\|(?<=\s)[a-z](?=\.)` | Matches `a.`, `b.` etc. at start of line or after whitespace |
| `ALPHABETICAL_LIST_WITH_PARENS` | `(?<=\()[a-z]+(?=\))\|(?<=^)[a-z]+(?=\))\|...` | Matches `(a)`, `b)` etc. |
| `NUMBERED_LIST_REGEX_1` | (long alternation) | Matches the number in `1.`, `2.` etc. — extracts the digit for sequence validation |
| `NUMBERED_LIST_REGEX_2` | (long alternation — includes the period) | Matches `1.`, `2.` with the period — used for actual replacement |
| `NUMBERED_LIST_PARENS_REGEX` | `\d{1,2}(?=\)\s)` | Matches numbers before `)` like `1)`, `2)` |
| `ROMAN_NUMERALS_IN_PARENTHESES` | `\(((?=[mdclxvi])m*(c[md]\|d?c*)(x[cl]\|l?x*)(i[xv]\|v?i*))\)(?=\s[A-Z])` | Matches `(iv)`, `(xii)` etc. followed by a capital letter |
| `SpaceBetweenListItemsFirstRule` | `(?<=\S\S)\s(?=\S\s*\d+♨)` | Inserts `\r` between items after period replacement |
| `SpaceBetweenListItemsSecondRule` | `(?<=\S\S)\s(?=\d{1,2}♨)` | Same, different context |
| `SpaceBetweenListItemsThirdRule` | `(?<=\S\S)\s(?=\d{1,2}☝)` | For paren-style lists |

**Sequence validation logic:** The module doesn't blindly treat every `1.` as a list item. It extracts all number matches, then checks if they form a consecutive sequence (1, 2, 3...) or adjacent pair. Only confirmed list items get their periods replaced. This prevents false positives like "I scored 1. The game ended."

**Alphabetical list validation:** Similarly, alphabetical items (a, b, c) are validated against a sequence. Roman numerals (i, ii, iii...) use a separate alphabet. Items are only treated as list items if they appear in consecutive order.

**Sentinel characters:**
- `♨` replaces periods in numbered lists (`1.` → `1♨`)
- `☝` replaces numbers before parentheses in numbered lists

---

### 4.9 `cleaner.py` + `clean/rules.py` — Pre-processing

**Lines:** 139 + 81 = 220 | **Regexes defined:** 18

The Cleaner is an optional pre-processing stage activated by `clean=True`. It normalizes formatting artifacts (HTML, PDF OCR, inconsistent newlines) before segmentation.

**CleanRules patterns:**

| Rule | Pattern | Replacement | Purpose |
|------|---------|-------------|---------|
| `NewLineInMiddleOfWordRule` | `\n(?=[a-zA-Z]{1,2}\n)` | `''` | Remove newlines that split words (PDF artifact) |
| `DoubleNewLineWithSpaceRule` | `\n \n` | `\r` | Paragraph break → sentence boundary |
| `DoubleNewLineRule` | `\n\n` | `\r` | Paragraph break → sentence boundary |
| `NewLineFollowedByPeriodRule` | `\n(?=\.(\s\|\n))` | `''` | Remove newline before period (OCR artifact) |
| `ReplaceNewlineWithCarriageReturnRule` | `\n` | `\r` | Remaining newlines → sentence boundaries |
| `EscapedNewLineRule` | `\\n` | `\n` | Literal `\n` string → actual newline |
| `EscapedCarriageReturnRule` | `\\r` | `\r` | Literal `\r` string → actual CR |
| `TypoEscapedNewLineRule` | `\\\ n` | `\n` | Common typo variant |
| `TypoEscapedCarriageReturnRule` | `\\\ r` | `\r` | Common typo variant |
| `InlineFormattingRule` | `{b\^&gt;\d*&lt;b\^}\|{b\^>\d*<b\^}` | `''` | Remove inline markup artifacts |
| `TableOfContentsRule` | `\.{4,}\s*\d+-*\d*` | `\r` | TOC entries like `Chapter 1 ........ 15` |
| `ConsecutivePeriodsRule` | `\.{5,}` | `' '` | Excessive dots → space |
| `ConsecutiveForwardSlashRule` | `\/{3}` | `''` | Triple slashes → removed |
| `NoSpaceBetweenSentencesRule` | `(?<=[a-z])\.(?=[A-Z])` | `'. '` | Fix `word.Word` → `word. Word` |
| `NoSpaceBetweenSentencesDigitRule` | `(?<=\d)\.(?=[A-Z])` | `'. '` | Fix `123.Word` → `123. Word` |
| `NEWLINE_IN_MIDDLE_OF_SENTENCE_REGEX` | `(?<=\s)\n(?=([a-z]\|\())` | (used for sub) | Newline before lowercase/paren = mid-sentence |

**HTML rules:**
| Rule | Pattern | Purpose |
|------|---------|---------|
| `HTMLTagRule` | `<\/?\w+((\s+\w+(\s*=\s*(?:".*?"\|'.*?'\|[\^'">\s]+))?)+\s*\|\s*)\/?>` | Strip HTML tags |
| `EscapedHTMLTagRule` | `&lt;\/?[^gt;]*gt;` | Strip escaped HTML tags |

**PDF rules:**
| Rule | Pattern | Purpose |
|------|---------|---------|
| `NewLineInMiddleOfSentenceRule` | `(?<=[^\n]\s)\n(?=\S)` | Remove OCR line breaks |
| `NewLineInMiddleOfSentenceNoSpacesRule` | `\n(?=[a-z])` | Newline before lowercase → space |

**`replace_punctuation_in_brackets()`** — Inline regex in cleaner.py:
```python
r'\[(?:[^\]])*\]'
```
Matches `[...]` and replaces any `?` inside with `&ᓷ&`. This prevents `[?]` or `[citation?]` from triggering sentence splits.

**`remove_newline_in_middle_of_sentence()`** uses a two-level approach:
```python
re.sub(r'(?:[^\.])*', replace_w_blank, self.text)
```
The outer regex matches everything between periods, then the callback applies `NEWLINE_IN_MIDDLE_OF_SENTENCE_REGEX` within each match. This scopes the newline removal to mid-sentence contexts only.

---

### 4.10 `lang/common/common.py` — Shared Regex Patterns

**Lines:** 119 | **Regexes defined:** 15+

This file defines the patterns shared across all Latin-script languages.

#### `SENTENCE_BOUNDARY_REGEX` — The Core Split Pattern

```python
_SENTENCE_END_PUNCT = r"[。．.！!?？ȸȹ☉☈☇☄]"

_SENTENCE_BOUNDARY_PARTS = [
    r"（(?:[^）])*）(?=\s?[A-Z])",                               # [1] Full-width parens
    r"「(?:[^」])*」(?=\s[A-Z])",                                 # [2] Japanese brackets
    r"\((?:[^\)]){2,}\)(?=\s[A-Z])",                            # [3] English parens
    r"\'(?:[^\'])*[^,]\'(?=\s[A-Z])",                           # [4] Single-quoted
    r"\"(?:[^\"])*[^,]\"(?=\s[A-Z])",                           # [5] Double-quoted
    r"\"(?:[^\"])*[^,]\"(?=\s[A-Z])",                          # [6] Curly-quoted (\u201c...\u201d)
    r"[。．.！!?？ ]{2,}",                                       # [7] Multiple end marks
    r"\S[^\n。．.！!?？ȸȹ☉☈☇☄]*" + _SENTENCE_END_PUNCT,        # [8] THE MAIN PATTERN
    r"[。．.！!?？]",                                             # [9] Lone end mark
]
```

This is used with `re.finditer()` — it extracts sentence-like chunks from text. The alternation order matters — earlier branches are tried first.

**Branch analysis:**

1. **Branches [1]-[6]**: Handle parenthesized/quoted text as complete units. The lookahead `(?=\s[A-Z])` requires a capital letter to follow, indicating a new sentence. The `[^,]` before closing quotes ensures the quote doesn't end with a comma (which would indicate a dialogue tag, not a sentence end).

2. **Branch [7]**: `[。．.！!?？ ]{2,}` — Two or more sentence-ending marks (including spaces). Captures patterns like `?! ` or `. . .` as a single unit.

3. **Branch [8]**: `\S[^\n。．.！!?？ȸȹ☉☈☇☄]*[。．.！!?？ȸȹ☉☈☇☄]` — **This is the main workhorse.** It matches: a non-whitespace character, followed by anything that isn't a sentence-ending character or newline, followed by one sentence-ending character. This greedily consumes an entire sentence up to its terminal punctuation. The sentinel characters `ȸȹ☉☈☇☄` are included in both the character class and the terminator set.

4. **Branch [9]**: A lone sentence-ending mark. Catches orphaned punctuation.

**The critical observation**: By the time this regex runs, all non-boundary `.`, `!`, `?` have been replaced with sentinels. So Branch [8] will correctly stop at the first remaining sentence-ending punctuation mark, which is guaranteed to be a genuine boundary.

#### Other Common patterns:

```python
QUOTATION_AT_END_OF_SENTENCE_REGEX = r'[!?\.-][\"\'""]\s{1}[A-Z]'
```
Detects patterns like `!"  He` or `.'  She` — a sentence-ending punctuation mark, followed by a closing quote, followed by a space and capital letter. Used in `post_process_segments()` to split sentences that the main regex joined together.

```python
SPLIT_SPACE_QUOTATION_AT_END_OF_SENTENCE_REGEX = r'(?<=[!?\.-][\"\'""])\s{1}(?=[A-Z])'
```
The actual split pattern for the above — splits on the space between the closing quote and the capital letter.

```python
PARENS_BETWEEN_DOUBLE_QUOTES_REGEX = r'["\"]\s\(.*\)\s["\"]'
```
Matches parenthesized text between double quotes, used to insert `\r` boundaries.

```python
MULTI_PERIOD_ABBREVIATION_REGEX = r"\b[a-z](?:\.[a-z])+[.]"
```
Matches abbreviations like `u.s.a.`, `e.g.`, `i.e.` — a word boundary, then alternating single lowercase letters and periods. Applied case-insensitively. The callback replaces all `.` with `∯`.

#### Abbreviation rules:

```python
PossessiveAbbreviationRule     r"\.(?='s\s)|\.(?='s$)|\.(?='s\Z)"  → '∯'
```
Protects the period in possessive forms like `Mr.'s`.

```python
KommanditgesellschaftRule      r'(?<=Co)\.(?=\sKG)'  → '∯'
```
Protects the period in "Co. KG" (German business form).

```python
SingleUpperCaseLetterAtStartOfLineRule   r"(?<=^[A-Z])\.(?=\s)"  → '∯'
SingleUpperCaseLetterRule                r"(?<=\s[A-Z])\.(?=,?\s)"  → '∯'
```
Protects periods after single uppercase letters (initials) like "J. K. Rowling".

#### AM/PM rules with timezone awareness:

```python
_TZ = (
    r'(?:[ECMP][SD]T'      # US: EST, EDT, CST, CDT, MST, MDT, PST, PDT
    r'|GMT|UTC'             # Universal
    r'|CET|CEST|WET|WEST|EET|EEST'  # Europe
    r'|BST|MSK|IST'        # UK, Moscow, India
    r'|JST|KST|HKT|SGT'   # East Asia
    r'|(?:AE|NZ)[SD]T'     # Australia/NZ
    r'|AST|AKST|HST|NST'   # US/Canada outlying
    r')[\s.]'
)

UpperCasePmRule = Rule(r'(?<= P∯M)∯(?=\s(?!' + _TZ + r')[A-Z])', '.')
```
After abbreviation processing, "5 P.M." becomes "5 P∯M∯". This rule restores the final period as a boundary ONLY if the next word is uppercase AND is NOT a timezone abbreviation. So "5 P.M. EST" keeps the period protected, but "5 P.M. He left" restores it as a boundary.

#### Number rules:

```python
PeriodBeforeNumberRule              r'\.(?=\d)'          → '∯'   # ".5", ".123"
NumberAfterPeriodBeforeLetterRule   r'(?<=\d)\.(?=\S)'   → '∯'   # "3.x", "1.5"
NewLineNumberPeriodSpaceLetterRule  r'(?<=\r\d)\.(?=(\s\S)|\))'  → '∯'   # "\r1. text"
StartLineNumberPeriodRule           r'(?<=^\d)\.(?=(\s\S)|\))'   → '∯'   # "^1. text"
StartLineTwoDigitNumberPeriodRule   r'(?<=^\d\d)\.(?=(\s\S)|\))' → '∯'   # "^12. text"
InchesAbbreviationRule              r'(?<=\d )in\.(?=\s[a-z])'   → 'in∯' # "5 in. wide"
```

---

### 4.11 `lang/common/standard.py` — Standard Rules & Abbreviations

**Lines:** 114 | **Regexes defined:** 20+

This defines the default rule sets that most languages inherit.

**Punctuation list:**
```python
Punctuations = ['。', '．', '.', '！', '!', '?', '？']
```
Used by `check_for_punctuation()` to decide whether a segment needs the full `process_text()` pipeline. If none of these characters are present, the segment is returned as-is.

**GeoLocationRule:**
```python
r'(?<=[a-zA-z]°)\.(?=\s*\d+)'  → '∯'
```
Protects periods in geographic coordinates like `40°N. 74°W.` → `40°N∯ 74°W∯`.

**FileFormatRule:**
```python
r'(?<=\s)\.(?=(jpe?g|png|gif|tiff?|pdf|ps|docx?|xlsx?|svg|bmp|tga|exif|odt|html?|txt|rtf|bat|sxw|xml|zip|exe|msi|blend|wmv|mp[34]|pptx?|flac|rb|cpp|cs|js)\s)'  → '∯'
```
Protects periods in file extensions like `.jpg`, `.pdf`, `.html`. The lookahead captures 40+ file extensions. The lookbehind `(?<=\s)` ensures it's preceded by whitespace (so it's a standalone filename reference, not part of a URL).

**QuestionMarkInQuotationRule:**
```python
r'\?(?=(\'|\"))'  → '&ᓷ&'
```
Protects `?` immediately before a closing quote. This prevents `?'` or `?"` from splitting sentences.

**DoublePunctuationRules:**
```python
r'\?!'  → '☉'
r'!\?'  → '☈'
r'\?\?' → '☇'
r'!!'   → '☄'
```
Replaces double punctuation with single sentinel characters so they're treated as one sentence-ending mark, not two.

**ExclamationPointRules:**
```python
InQuotationRule:          r'\!(?=(\'|\"))'       → '&ᓴ&'   # ! before quote
BeforeCommaMidSentenceRule: r'\!(?=\,\s[a-z])'   → '&ᓴ&'   # "wow!, he said"
MidSentenceRule:          r'\!(?=\s[a-z])'       → '&ᓴ&'   # "wow! he said"
```
Exclamation marks followed by lowercase continuations are protected — they're mid-sentence exclamations, not sentence boundaries.

**EllipsisRules:**
```python
ThreeConsecutiveRule:  r'\.\.\.(?=\s+[A-Z])'         → '☏☏.'     # "... Next"
FourConsecutiveRule:   r'(?<=\S)\.{3}(?=\.\s[A-Z])'  → 'ƪƪƪ'    # "word.... Next"
ThreeSpaceRule:        r'(\s\.){3}\s'                 → '♟♟♟♟♟♟♟' # " . . . "
FourSpaceRule:         r'(?<=[a-z])(\.\s){3}\.($|\\n)' → '♝♝♝♝♝♝♝' # "word. . . ."
OtherThreePeriodRule:  r'\.\.\.'                      → 'ƪƪƪ'    # "..."
```
Ellipsis patterns are replaced with sentinels of the same character width, preserving text length for offset tracking. The `ThreeConsecutiveRule` specifically handles `...` followed by a capital letter — the `...` is protected but the sentence break occurs there (replaced with `☏☏.` which still ends with a real `.`).

**ReinsertEllipsisRules:** The reverse mappings that restore the original ellipsis forms.

**Abbreviation list (English):** 185 entries including:
- Titles: `dr`, `mr`, `mrs`, `ms`, `prof`, `rev`, `gen`, `capt`, ...
- Geographic: `ala`, `calif`, `conn`, `fla`, `ida`, ...
- Months: `jan`, `feb`, `mar`, `apr`, ...
- Other: `etc`, `fig`, `vs`, `corp`, `inc`, `ltd`, ...

**SENTENCE_STARTERS:** Words that, when following an abbreviation, indicate a new sentence:
```
A Being Did For He How However I In It Millions More She That The There They We What When Where Who Why
```

---

### 4.12 Language Modules

#### Minimal override languages (inherit Common + Standard)

**English** (`en`): Only overrides `SENTENCE_STARTERS`.

**French** (`fr`): Custom abbreviation list (79 entries). Empty `PREPOSITIVE_ABBREVIATIONS` and `NUMBER_ABBREVIATIONS` — French doesn't use titles like "Dr." the same way.

**Italian** (`it`): Massive abbreviation list (~1500+ entries) including many technical, institutional, and professional abbreviations. Custom prepositive (110+ entries) and number abbreviations.

**Polish** (`pl`): 129 abbreviations including many with embedded periods like `sp. z o.o` (Polish limited company).

**Dutch** (`nl`): Extremely large abbreviation list (~1000+ entries) — Dutch legal and administrative terminology generates many period-containing abbreviations.

**Bulgarian** (`bg`): Cyrillic abbreviation list (61 entries). Custom `replace_period_of_abbr()` that's simpler — just `r'(?<=\s{abbr})\.|(?<=^{abbr})\.'`.

#### Medium override languages

**Spanish** (`es`): 159 abbreviations. Custom prepositive (`dr`, `ee`, `lic`, `mt`, `prof`, `sra`, `srta`) and number (`cra`, `ext`, `no`, `nos`, `p`, `pp`, `tel`) lists.

**Danish** (`da`): 274 abbreviations. Custom `Numbers` rules for Danish number formatting. Custom `SENTENCE_STARTERS` list in Danish. Overrides `replace_abbreviation_as_sentence_boundary()` to include Danish-specific patterns (`s.u`, `s.U`).

**German/Deutsch** (`de`):
- Custom `Numbers` with `NumberPeriodSpaceRule` and `NegativeNumberPeriodSpaceRule` for ordinal numbers.
- Custom `Processor` with `replace_period_in_deutsch_dates()` — protects periods before German month names (`Januar`, `Februar`, ...).
- Custom `AbbreviationReplacer.scan_for_replacements()` — simplified to `r'(?<={am})\.(?=\s)'`.
- Custom `BetweenPunctuation` for German quotation marks (`„..."` and `,,..."` — unconventional variant).
- German `SENTENCE_STARTERS`: `Am Auch Auf Bei Da Das Der Die Ein Eine Es Für Heute Ich Im In Ist Jetzt Mein Mit Nach So Und Warum Was Wenn Wer Wie Wir`.

**Russian** (`ru`): 62 Cyrillic abbreviations. Custom `replace_period_of_abbr()` with three separate regexes (after whitespace, after `\A`, after `^`) because Russian text processing may not have the same word boundary behavior.

**Slovak** (`sk`):
- Custom `ListItemReplacer` that **disables alphabetical list parsing** — the comment explains that abbreviations like `s. r. o.` (Slovak limited company) clash with alphabetical list detection.
- Custom `replace_period_of_abbr()` that uses `str.replace()` instead of regex — replaces ALL periods in the abbreviation, handling multi-period forms like `s. r. o.`.
- Custom `Processor` with `replace_period_in_ordinal_numerals()` (`r'(?<=\d)\.(?=\s*[a-z]+)'`), `replace_period_in_roman_numerals()`, and Slovak date handling.
- Custom `BetweenPunctuation` for Slovak double quotes (`„..."`).

**Kazakh** (`kk`):
- Custom `MULTI_PERIOD_ABBREVIATION_REGEX` using Unicode range `[\u0400-\u0500]` for Cyrillic characters.
- Custom `Processor` with `between_punctuation()` override that adds rules for `?` and `!` followed by dashes (`—`), which is common in Kazakh dialogue formatting.
- Custom `AbbreviationReplacer.replace()` that handles Cyrillic single-letter abbreviations.

#### Fully custom boundary regex languages

These languages replace `SENTENCE_BOUNDARY_REGEX` entirely — the Common regex assumes Latin-script punctuation.

| Language | `SENTENCE_BOUNDARY_REGEX` | `Punctuations` |
|----------|--------------------------|-----------------|
| **Hindi** | `r'.*?[।\|!\?]\|.*?$'` | `['।', '\|', '.', '!', '?']` |
| **Marathi** | `r'.*?[.!\?]\|.*?$'` | `['.', '!', '?']` |
| **Arabic** | `r'.*?[:\.!\?؟،]\|.*?\Z\|.*?$'` | `['?', '!', ':', '.', '؟', '،']` |
| **Persian** | `r'.*?[:\.!\?؟]\|.*?\Z\|.*?$'` | `['?', '!', ':', '.', '؟']` |
| **Burmese** | `r'.*?[။၏!\?]\|.*?$'` | `['။', '၏', '?', '!']` |
| **Amharic** | `r'.*?[፧።!\?]\|.*?$'` | `['።', '፧', '?', '!']` |
| **Armenian** | `r'.*?[։՜:]\|.*?$'` | `['։', '՜', ':']` |
| **Greek** | `r'.*?[\.;!\?]\|.*?$'` | `['.', '!', ';', '?']` |
| **Urdu** | `r'.*?[۔؟!\?]\|.*?$'` | `['?', '!', '۔', '؟']` |

These use the `.*?[PUNCT]|.*?$` pattern — a non-greedy match up to any sentence-ending punctuation, with `|.*?$` as a fallback for the final segment without punctuation.

**Arabic and Persian** add colon rules:
```python
ReplaceColonBetweenNumbersRule = Rule(r'(?<=\d):(?=\d)', '♭')
ReplaceNonSentenceBoundaryCommaRule = Rule(r'،(?=\s\S+،)', '♬')
```
Colons between numbers (times like `3:30`) are protected. Arabic commas (`،`) are protected when they appear in comma-separated lists (not sentence boundaries).

#### CJK languages with custom BetweenPunctuation

**Japanese** (`ja`):
- Custom `Cleaner` that only removes newlines after `の` particle: `r'(?<=の)\n(?=\S)'`.
- Custom `BetweenPunctuation` with Japanese-specific patterns:
  - `BETWEEN_PARENS_JA_REGEX = r'（(?=(?P<tmp>[^（）]+|\\{2}|\\.)*)(?P=tmp)）'` — full-width parens
  - `BETWEEN_QUOTE_JA_REGEX = r'「(?=(?P<tmp>[^「」]+|\\{2}|\\.)*)(?P=tmp)」'` — corner brackets

**Chinese** (`zh`):
- Custom `BetweenPunctuation` with Chinese-specific patterns:
  - `BETWEEN_DOUBLE_ANGLE_QUOTATION_MARK_REGEX = r"《(?=(?P<tmp>[^》\\]+|\\{2}|\\.)*)(?P=tmp)》"` — book title marks
  - `BETWEEN_L_BRACKET_REGEX = r"「(?=(?P<tmp>[^」\\]+|\\{2}|\\.)*)(?P=tmp)」"` — corner brackets

---

### 4.13 `spacy_component.py` — Integration Bridge

**Lines:** 23 | **Regexes defined:** 0

Registered as a spaCy factory via `pyproject.toml` entry point. Creates a `Segmenter(char_span=True)` and maps sentence boundaries to spaCy token `is_sent_start` flags by matching character offsets to token indices.

---

## 5. Complete Regex Catalog

### Abbreviation & Period Protection

| # | Pattern | File | Purpose |
|---|---------|------|---------|
| 1 | `\.(?='s\s)\|\.(?='s$)\|\.(?='s\Z)` | common.py | Possessive abbreviation |
| 2 | `(?<=Co)\.(?=\sKG)` | common.py | Kommanditgesellschaft |
| 3 | `\b[a-z](?:\.[a-z])+[.]` | common.py | Multi-period abbreviation (U.S.A.) |
| 4 | `(?<=^[A-Z])\.(?=\s)` | common.py | Single uppercase letter at line start |
| 5 | `(?<=\s[A-Z])\.(?=,?\s)` | common.py | Single uppercase letter after space |
| 6 | `(?<= P∯M)∯(?=\s(?!TZ)[A-Z])` | common.py | AM/PM with timezone awareness (x4 variants) |
| 7 | `\.(?=\d)` | common.py | Period before number |
| 8 | `(?<=\d)\.(?=\S)` | common.py | Number-period-letter |
| 9 | `(?<=\r\d)\.(?=(\s\S)\|\))` | common.py | Newline-number-period |
| 10 | `(?<=^\d)\.(?=(\s\S)\|\))` | common.py | Start-line number-period |
| 11 | `(?<=^\d\d)\.(?=(\s\S)\|\))` | common.py | Start-line two-digit number-period |
| 12 | `(?<=\d )in\.(?=\s[a-z])` | common.py | Inches abbreviation |
| 13 | `([a-zA-Z0-9_])(\.)([a-zA-Z0-9_])` | standard.py | Email/multi-period (a.b → a∮b) |
| 14 | `(?<=[a-zA-z]°)\.(?=\s*\d+)` | standard.py | Geo-location |
| 15 | `(?<=\s)\.(?=(jpe?g\|png\|...)` | standard.py | File format extensions |

### Sentence Boundary

| # | Pattern | File | Purpose |
|---|---------|------|---------|
| 16 | `SENTENCE_BOUNDARY_REGEX` (9 alternatives) | common.py | The core split pattern |
| 17 | `[!?\.-][\"\'""]\s{1}[A-Z]` | common.py | Quotation at end of sentence |
| 18 | `(?<=[!?\.-][\"\'""])\s{1}(?=[A-Z])` | common.py | Split at quotation end |
| 19 | `["\"]\s\(.*\)\s["\"]` | common.py | Parens between double quotes |

### Punctuation Protection

| # | Pattern | File | Purpose |
|---|---------|------|---------|
| 20 | `(?<=\S)(!|\?){3,}(?=(\s\|\Z\|$))` | common.py | Continuous punctuation |
| 21 | `(?<=[^\d\s])(\.\|∯)((\[...)\|...)(\s)(?=[A-Z])` | common.py | Numbered references |
| 22 | `\?(?=(\'|\"))` | standard.py | Question mark in quotation |
| 23 | `\?!` / `!\?` / `\?\?` / `!!` | standard.py | Double punctuation (x4) |
| 24 | `\!(?=(\'|\"))` | standard.py | Exclamation in quotation |
| 25 | `\!(?=\,\s[a-z])` | standard.py | Exclamation before comma |
| 26 | `\!(?=\s[a-z])` | standard.py | Exclamation mid-sentence |

### Ellipsis

| # | Pattern | File | Purpose |
|---|---------|------|---------|
| 27 | `\.\.\.(?=\s+[A-Z])` | standard.py | Three consecutive before capital |
| 28 | `(?<=\S)\.{3}(?=\.\s[A-Z])` | standard.py | Four consecutive |
| 29 | `(\s\.){3}\s` | standard.py | Spaced ellipsis |
| 30 | `(?<=[a-z])(\.\s){3}\.($\|\\n)` | standard.py | Four spaced periods |
| 31 | `\.\.\.` | standard.py | General three periods |
| 32-36 | Reverse rules (ƪƪƪ→..., etc.) | standard.py | Ellipsis restoration |

### Between Punctuation

| # | Pattern | File | Purpose |
|---|---------|------|---------|
| 37 | `(?<=\s)'(?:[^']\|'[a-zA-Z])*'` | between_punctuation.py | Single quotes |
| 38 | `(?<=\s)\u2018...\u2019` | between_punctuation.py | Slanted single quotes |
| 39 | `"(?=(?P<tmp>[^"\\]+\|\\{2}\|\\.)*)(?P=tmp)"` | between_punctuation.py | Double quotes |
| 40 | `\u00ab...\u00bb` | between_punctuation.py | Guillemets |
| 41 | `\u201c...\u201d` | between_punctuation.py | Curly double quotes |
| 42 | `\[...\]` | between_punctuation.py | Square brackets |
| 43 | `\(...\)` | between_punctuation.py | Parentheses |
| 44 | `--...--` | between_punctuation.py | Em dashes |
| 45 | `(?<=\s)'(?:[^']\|'[a-zA-Z])*'\S` | between_punctuation.py | Word with leading apostrophe |

### List Detection

| # | Pattern | File | Purpose |
|---|---------|------|---------|
| 46 | `(?<=^)[a-z](?=\.)...` | lists_item_replacer.py | Alphabetical list with periods |
| 47 | `(?<=\()[a-z]+(?=\))...` | lists_item_replacer.py | Alphabetical list with parens |
| 48 | `NUMBERED_LIST_REGEX_1` (12 alternatives) | lists_item_replacer.py | Extract numbers from lists |
| 49 | `NUMBERED_LIST_REGEX_2` (12 alternatives) | lists_item_replacer.py | Replace periods in numbered lists |
| 50 | `\d{1,2}(?=\)\s)` | lists_item_replacer.py | Numbers before parens |
| 51 | `\(((?=[mdclxvi])m*(c[md]\|d?c*)(x[cl]\|l?x*)(i[xv]\|v?i*))\)(?=\s[A-Z])` | lists_item_replacer.py | Roman numerals in parens |
| 52-54 | SpaceBetweenListItems (x3) | lists_item_replacer.py | Insert breaks between items |

### Cleaning

| # | Pattern | File | Purpose |
|---|---------|------|---------|
| 55 | `\n(?=[a-zA-Z]{1,2}\n)` | clean/rules.py | Newline in middle of word |
| 56 | `\n \n` | clean/rules.py | Double newline with space |
| 57 | `\n\n` | clean/rules.py | Double newline |
| 58 | `\n(?=\.(\s\|\n))` | clean/rules.py | Newline before period |
| 59 | `\n` | clean/rules.py | All remaining newlines |
| 60-63 | Escaped newline variants (x4) | clean/rules.py | `\\n`, `\\r`, `\\ n`, `\\ r` |
| 64 | `{b\^&gt;...}` | clean/rules.py | Inline formatting |
| 65 | `\.{4,}\s*\d+-*\d*` | clean/rules.py | Table of contents |
| 66 | `\.{5,}` | clean/rules.py | Consecutive periods |
| 67 | `\/{3}` | clean/rules.py | Consecutive slashes |
| 68 | `(?<=[a-z])\.(?=[A-Z])` | clean/rules.py | No space between sentences |
| 69 | `(?<=\d)\.(?=[A-Z])` | clean/rules.py | No space (digit variant) |
| 70 | `(?<=\s)\n(?=([a-z]\|\())` | clean/rules.py | Newline in middle of sentence |
| 71 | `\n(?=•')` | clean/rules.py | Newline before bullet |
| 72-73 | Quotation normalization (x2) | clean/rules.py | `''`→`"`, ` `` `→`"` |
| 74-75 | HTML tag rules (x2) | clean/rules.py | Strip HTML |
| 76-77 | PDF rules (x2) | clean/rules.py | PDF line break handling |

### Language-specific additions

| # | Pattern | Language | Purpose |
|---|---------|----------|---------|
| 78 | `(?<=\s\d)\.(?=\s)\|(?<=\s\d\d)\.(?=\s)` | German, Danish | Ordinal number periods |
| 79 | `(?<=-\d)\.(?=\s)\|...` | German, Danish | Negative number periods |
| 80 | `(?<=\d)\.(?=\s*{month})` | German, Danish, Slovak | Date periods before months |
| 81 | `„..."`/`,,..."` | German, Slovak | Language-specific quotes |
| 82 | `《...》` / `「...」` | Chinese | Chinese quotation marks |
| 83 | `（...）` / `「...」` | Japanese | Japanese brackets |
| 84 | `(?<=の)\n(?=\S)` | Japanese | Newline after の particle |
| 85 | `(?<=\d):(?=\d)` | Arabic, Persian | Colon between numbers |
| 86 | `،(?=\s\S+،)` | Arabic, Persian | Non-boundary Arabic comma |
| 87 | `(?<=\d)\.(?=\s*[a-z]+)` | Slovak | Ordinal numerals |
| 88 | `((\s+[VXI]+)\|(^[VXI]+))(\.)(?=\s+)` | Slovak | Roman numeral periods |
| 89 | `[\u0400-\u0500]+(?:\.\s?[\u0400-\u0500])+[.]` | Kazakh | Cyrillic multi-period abbreviation |
| 90 | `(?<=^[А-ЯЁ])\.(?=\s)` / `(?<=\s[А-ЯЁ])\.(?=\s)` | Kazakh | Cyrillic single-letter abbreviation |
| 91 | `\?(?=\s*[-—]\s*)` / `!(?=\s*[-—]\s*)` | Kazakh | Punctuation before dash (dialogue) |

---

## 6. Sentinel Character Map

| Sentinel | Original | Used in | Restored by |
|----------|----------|---------|-------------|
| `∯` | `.` | Abbreviation periods, number periods, list periods, etc. | `SubSymbolsRules.SUBS_TABLE` |
| `∮` | `.` | Periods in email-like patterns (`a.b`) | `ReinsertEllipsisRules.SubOnePeriod` |
| `&ᓰ&` | `。` | Full-width period (CJK) inside quotes | `SubSymbolsRules.SUBS_TABLE` |
| `&ᓱ&` | `．` | Ideographic full stop inside quotes | `SubSymbolsRules.SUBS_TABLE` |
| `&ᓳ&` | `！` | Full-width exclamation inside quotes | `SubSymbolsRules.SUBS_TABLE` |
| `&ᓴ&` | `!` | Exclamation inside quotes/mid-sentence | `SubSymbolsRules.SUBS_TABLE` |
| `&ᓷ&` | `?` | Question mark inside quotes/brackets | `SubSymbolsRules.SUBS_TABLE` |
| `&ᓸ&` | `？` | Full-width question mark inside quotes | `SubSymbolsRules.SUBS_TABLE` |
| `&⎋&` | `'` | Single quote inside double quotes | `SubSingleQuoteRule` |
| `☉` | `?!` | Double punctuation | `SubSymbolsRules.SUBS_TABLE` |
| `☈` | `!?` | Double punctuation | `SubSymbolsRules.SUBS_TABLE` |
| `☇` | `??` | Double punctuation | `SubSymbolsRules.SUBS_TABLE` |
| `☄` | `!!` | Double punctuation | `SubSymbolsRules.SUBS_TABLE` |
| `&✂&` | `(` | Parentheses in Roman numeral lists | `SubSymbolsRules.SUBS_TABLE` |
| `&⌬&` | `)` | Parentheses in Roman numeral lists | `SubSymbolsRules.SUBS_TABLE` |
| `ȸ` | (none) | Synthetic end-of-text marker | `SubSymbolsRules.SUBS_TABLE` → `''` |
| `ȹ` | `\n` | Newline preservation marker | `SubSymbolsRules.SUBS_TABLE` |
| `♨` | `.` (in list) | Period in numbered list item | `SubstituteListPeriodRule` → `∯` |
| `☝` | (number) | Number in parenthesized list item | `ListMarkerRule` → `''` |
| `☏☏` | `..` | Two periods (ellipsis component) | `SubTwoConsecutivePeriod` |
| `ƪƪƪ` | `...` | Three periods (ellipsis) | `SubThreeConsecutivePeriod` |
| `♟♟♟♟♟♟♟` | ` . . . ` | Spaced ellipsis | `SubThreeSpacePeriod` |
| `♝♝♝♝♝♝♝` | `. . . .` | Four spaced periods | `SubFourSpacePeriod` |
| `♭` | `:` | Colon between numbers (Arabic/Persian) | `SubSymbolsRules.SUBS_TABLE` |
| `♬` | `،` | Arabic comma (non-boundary) | `SubSymbolsRules.SUBS_TABLE` |
| `\r` | `\n` or space | Internal sentence boundary marker | Split point in `split_into_segments()` |

---

## 7. Pipeline Execution Order

```
INPUT TEXT
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 0: CLEANING (optional, if clean=True)         │
│                                                     │
│  1. Remove newlines in middle of words/sentences    │
│  2. Double newlines → \r (paragraph boundaries)     │
│  3. Remaining newlines → \r (or PDF-specific rules) │
│  4. Un-escape literal \n, \r strings                │
│  5. Strip HTML tags                                 │
│  6. Protect ? in brackets                           │
│  7. Remove inline formatting artifacts              │
│  8. Normalize quotation marks                       │
│  9. Handle table of contents patterns               │
│ 10. Fix missing spaces between sentences            │
│ 11. Remove excessive consecutive characters         │
└─────────────────┬───────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 1: STRUCTURAL NORMALIZATION                   │
│                                                     │
│  1. \n → \r                                         │
│  2. List detection (numbered, alphabetical, Roman)  │
│     - Periods in list items → ♨ → ∯                 │
│     - Numbers before parens → ☝                     │
│     - Insert \r between list items                  │
└─────────────────┬───────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 2: PERIOD DISAMBIGUATION                      │
│                                                     │
│  1. Global abbreviation rules (possessive, KG,      │
│     single letters)                                 │
│  2. Per-abbreviation matching (Aho-Corasick scan)   │
│     - Check next character: uppercase/lowercase/    │
│       digit → protect or keep                       │
│  3. Multi-period abbreviations (U.S.A. → U∯S∯A∯)   │
│  4. AM/PM rules (with timezone negative lookahead)  │
│  5. Sentence-starter correction (undo if followed   │
│     by known starter word)                          │
│  6. Number rules (6 patterns)                       │
│  7. Email/multi-period rule                         │
│  8. Geo-location rule                               │
│  9. File format rule                                │
└─────────────────┬───────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 3: PUNCTUATION DISAMBIGUATION                 │
│                                                     │
│  1. Continuous punctuation (!!!/??) → sentinels     │
│  2. Numeric references → protect period             │
└─────────────────┬───────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 4: SPLIT & PER-SEGMENT PROCESSING             │
│                                                     │
│  1. Handle parens between double quotes             │
│  2. Split on \r markers → segment list              │
│  3. For each segment:                               │
│     a. Apply ellipsis rules                         │
│     b. If segment contains punctuation:             │
│        i.   Add ȸ if no terminal punctuation        │
│        ii.  Exclamation word protection              │
│        iii. Between-punctuation protection           │
│             (8 quote/bracket types)                  │
│        iv.  Double punctuation → sentinels           │
│        v.   Question mark in quotation rule          │
│        vi.  Exclamation point rules (3 patterns)     │
│        vii. Roman numeral paren replacement          │
│        viii.Optional colon/comma rules               │
│        ix.  Restore trailing ! if it's terminal      │
│        x.   SENTENCE_BOUNDARY_REGEX (finditer)       │
│  4. Restore all sentinels → original punctuation     │
│  5. Post-process: quotation end splits, whitespace   │
│  6. Restore single quotes (SubSingleQuoteRule)       │
└─────────────────┬───────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 5: SPAN MATCHING (if non-destructive)         │
│                                                     │
│  Map processed sentences back to original text       │
│  positions using str.find() + fallback regex         │
└─────────────────┬───────────────────────────────────┘
                  ▼
OUTPUT: List[str] or List[TextSpan]
```

---

## 8. Regex Design Patterns Used

### 8.1 Lookbehind + Lookahead for Context-Sensitive Replacement

The most common pattern. Replace a character (usually `.`) only when specific context surrounds it:

```python
r'(?<=\s[A-Z])\.(?=,?\s)'   # Period after single capital letter
r'(?<=\d)\.(?=\S)'           # Period between digit and non-space
```

This preserves surrounding text while modifying only the target character.

### 8.2 Backreference-Based Atomic Grouping Simulation

Used in `between_punctuation.py` to prevent catastrophic backtracking:

```python
r'"(?=(?P<tmp>[^\"\\]+|\\{2}|\\.)*)(?P=tmp)"'
```

The lookahead `(?=(?P<tmp>...)*)` captures the content, then `(?P=tmp)` matches it again. Once the lookahead commits to a match, the backreference cannot backtrack into it. This simulates Ruby's `(?>...)` atomic groups.

### 8.3 Multi-Alternative Boundary Regex

`SENTENCE_BOUNDARY_REGEX` uses `|` alternation with `re.finditer()` to extract sentence-like chunks rather than finding split points. This is the opposite of most splitters — it matches the content, not the delimiter.

### 8.4 Dynamic Regex Construction

Abbreviation-specific regexes are built at cache-initialization time:
```python
match_re = re.compile(r"(?:^|\s|\r|\n){}".format(escaped), re.IGNORECASE)
next_word_re = re.compile(r"(?<={escaped} ).{1}".format(escaped=escaped))
```

Sentence-starter patterns are built dynamically:
```python
sent_starters = "|".join(r"(?=\s{}\s)".format(word) for word in self.SENTENCE_STARTERS)
```

### 8.5 Negative Lookahead for Exception Lists

The AM/PM rules use negative lookahead to exclude timezone abbreviations:
```python
r'(?<= P∯M)∯(?=\s(?!' + _TZ + r')[A-Z])'
```
"Restore the boundary UNLESS followed by a timezone."

### 8.6 Pre-compiled Patterns on Hot Paths

Module-level `re.compile()` for patterns used in tight loops:
```python
_ALPHA_ONLY_RE = re.compile(r'\A[a-zA-Z]*\Z')
_TRAILING_EXCL_RE = re.compile(r'&ᓴ&$')
```

### 8.7 `str.replace()` Over Regex for Known Literals

When replacements are fixed strings (sentinels → original characters), `str.replace()` is used instead of regex for performance:
```python
def _sub_symbols_fast(text, lang):
    for old, new in lang.SubSymbolsRules.SUBS_TABLE:
        text = text.replace(old, new)
```

---

## 9. Potential Issues and Edge Cases

### 9.1 Sentinel Collision

If input text contains sentinel characters (`∯`, `ȸ`, `ȹ`, `☉`, `☈`, `☇`, `☄`, `♨`, `☝`, `ƪ`, `♟`, `♝`, `☏`, `♭`, `♬`, `&ᓴ&`, `&ᓷ&`, `&⎋&`, `&✂&`, `&⌬&`, etc.), they will be incorrectly processed. There is no escaping mechanism. While these characters are rare in natural text, they could appear in:
- Mathematical or musical notation
- Unicode test data
- Deliberately adversarial input

### 9.2 Unclosed Quotes

The `between_punctuation.py` regex patterns assume matching open/close quote pairs. Unclosed quotes like `He said "hello` will fail to match, leaving punctuation unprotected within the quoted region. Worse, certain patterns of unclosed quotes could cause the regex engine to attempt many alternatives before failing.

### 9.3 Latin-Script Bias

The `[A-Z]` lookaheads in `SENTENCE_BOUNDARY_REGEX` and many rules only work for Latin-script languages. Languages using Cyrillic, Arabic, Devanagari, etc. must override the entire boundary regex. The abbreviation replacement logic (`scan_for_replacements`) also checks `char.isupper()`, which works for Cyrillic but not for scripts without case distinctions.

### 9.4 Pipeline Ordering Sensitivity

The pipeline is order-dependent. For example:
- Abbreviation replacement must happen before the sentence boundary split
- `between_punctuation` must happen before exclamation point rules
- Ellipsis rules must happen before the main split but after newline normalization

If a language override changes the ordering (e.g., via a custom `Processor.process()`), it must maintain all these invariants.

### 9.5 The `replace_period_of_abbr` Lookahead

```python
r"(?<=\s{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())))".format(abbr=escaped)
```

The special-casing of `I`, `I'm`, `I'll` is English-specific but lives in the base `AbbreviationReplacer` class. Languages that use the default `replace_period_of_abbr()` inherit this English bias. Some languages (Russian, Bulgarian, Slovak) override this method, but others (French, Italian, Polish, Dutch) don't.

### 9.6 Greedy `.*?` in Non-Latin Boundary Regexes

The pattern `r'.*?[PUNCT]|.*?$'` used by Hindi, Arabic, Burmese, etc. uses `.*?` (non-greedy match of anything). This is simple but doesn't handle the complexities that the Latin-script pipeline handles (abbreviations, between-punctuation, etc.). These languages still run through the abbreviation and between-punctuation stages, but the final split regex is less sophisticated.

### 9.7 NUMBERED_LIST_REGEX Complexity

`NUMBERED_LIST_REGEX_1` and `NUMBERED_LIST_REGEX_2` each contain 12 alternatives covering combinations of:
- Start of string vs. after whitespace
- With/without hyphen or bullet (⁃) prefix
- With period vs. with paren

The regex is long but each alternative is simple (no backtracking). It could be simplified with a more structured approach, but the flat alternation is efficient for the regex engine.

---

## 10. Conclusion

pySBD's regex architecture is a **pipeline of progressive disambiguation**, not a single classification step. Its key strengths are:

1. **Decomposition**: The hard problem of "is this period a sentence boundary?" is decomposed into ~20 easier sub-problems, each solved by a focused regex.

2. **Sentinel substitution**: By replacing non-boundary punctuation with unique characters, the final split becomes trivial — any remaining period/exclamation/question mark is a boundary by elimination.

3. **Performance consciousness**: Aho-Corasick for multi-pattern matching, pre-compiled regexes, `str.replace()` for literal substitutions, and per-language caching.

4. **Extensibility**: New languages can be added by subclassing `Common` + `Standard` and overriding only what differs (abbreviation list, boundary regex, quote patterns, etc.).

The system's weaknesses — sentinel collision risk, ordering fragility, Latin-script bias — are inherent trade-offs of the rule-based approach. They could be mitigated but not eliminated without fundamentally changing the architecture.
