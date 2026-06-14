# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from collections import deque
from threading import RLock

from sentencesplit.utils import (
    _next_nonspace_char_is_non_ascii_upper,
    _next_nonspace_char_is_upper,
    apply_rules,
    ensure_compiled,
    split_mode_rank,
)


class AhoCorasickAutomaton:
    """Pure-Python Aho-Corasick automaton for multi-pattern substring search."""

    __slots__ = ("goto", "fail", "output", "delta", "_built")

    def __init__(self):
        # State 0 is the root. Each state maps char -> next_state.
        self.goto: list[dict[str, int]] = [{}]
        self.output: list[list[int]] = [[]]  # pattern IDs at each state
        self.fail: list[int] = [0]
        # Fail-link-collapsed transition table, built once in build(). Each
        # delta[state] maps an observed-alphabet char -> next state with the fail
        # walk already resolved, so search() is one dict.get per char (no inner
        # loop). Chars outside the alphabet are absent and .get(ch, 0) sends them
        # to the root, exactly as the fail walk would.
        self.delta: list[dict[str, int]] = []
        self._built = False

    def add_pattern(self, pattern: str, pattern_id: int) -> None:
        state = 0
        for ch in pattern:
            nxt = self.goto[state].get(ch)
            if nxt is None:
                nxt = len(self.goto)
                self.goto.append({})
                self.output.append([])
                self.fail.append(0)
                self.goto[state][ch] = nxt
            state = nxt
        self.output[state].append(pattern_id)

    def build(self) -> None:
        queue: deque[int] = deque()
        # Initialize depth-1 states
        for ch, s in self.goto[0].items():
            self.fail[s] = 0
            queue.append(s)
        # BFS to build failure links
        while queue:
            r = queue.popleft()
            for ch, s in self.goto[r].items():
                queue.append(s)
                state = self.fail[r]
                while state != 0 and ch not in self.goto[state]:
                    state = self.fail[state]
                self.fail[s] = self.goto[state].get(ch, 0)
                if self.fail[s] == s:
                    self.fail[s] = 0
                if self.output[self.fail[s]]:
                    self.output[s] = self.output[s] + self.output[self.fail[s]]

        # Collapse the fail links into a DFA transition table. For each state and
        # each observed-alphabet char: take the goto if present, else inherit the
        # fail state's already-resolved transition. fail[r] is strictly shallower
        # than r, so a goto-tree BFS visits it first and delta[fail[r]] is ready.
        alphabet: set[str] = set()
        for trans in self.goto:
            alphabet.update(trans)
        delta: list[dict[str, int]] = [{} for _ in self.goto]
        root_goto = self.goto[0]
        delta[0] = {ch: root_goto.get(ch, 0) for ch in alphabet}
        queue = deque(self.goto[0].values())
        while queue:
            r = queue.popleft()
            gr = self.goto[r]
            dfail = delta[self.fail[r]]
            delta[r] = {ch: (gr[ch] if ch in gr else dfail[ch]) for ch in alphabet}
            queue.extend(gr.values())
        self.delta = delta
        self._built = True

    def search(self, text: str) -> set[int]:
        """Scan text in one pass, return set of matched pattern IDs."""
        state = 0
        found: set[int] = set()
        delta = self.delta
        output = self.output
        for ch in text:
            state = delta[state].get(ch, 0)
            out = output[state]
            if out:
                found.update(out)
        return found


def _replace_with_escape(txt: str, escaped: str, suffix_pattern: str, replacement: str, boundary_class: str = r"\s") -> str:
    """Replace period after abbreviation match using pre-escaped abbreviation."""
    txt = " " + txt
    txt = re.sub(rf"(?<=[{boundary_class}]{escaped}){suffix_pattern}", replacement, txt)
    return txt[1:]


# Constant patterns run on every ``replace()`` call. Compiling them once at import
# (rather than via a raw ``re.sub`` literal each call) skips the per-call pattern
# cache lookup in the abbreviation hot path.
# Compact time token with no leading space (e.g. "3P.M.").
_COMPACT_AMPM_RE = re.compile(r"(?<=\d)([AaPp])\.([Mm])\.")
# Sentence-boundary period after an all-uppercase 3+ part initialism ("S∯A∯T∯ ").
_UPPERCASE_INITIALISM_BOUNDARY_RE = re.compile(r"(?<=[A-Z]∯[A-Z]∯[A-Z])∯(?=\s)")
# Standalone pronoun "I" abbreviation sentinel before whitespace.
_STANDALONE_I_BOUNDARY_RE = re.compile(r"(?<![A-Za-z0-9_∯])I∯(?=\s)")
# Non-ASCII a.m./p.m. boundary restores (with and without an inner space).
_NON_ASCII_AMPM_RE = re.compile(r"(\d\s*[AaPp]∯[Mm])∯(?=\s)")
_NON_ASCII_AMPM_SPACED_RE = re.compile(r"(\d\s*[AaPp]∯\s+[Mm])∯(?=\s)")


class _AbbreviationData:
    """Pre-computed abbreviation data for a language, cached per Abbreviation class."""

    __slots__ = (
        "abbreviations",
        "abbr_set",
        "prepositive_set",
        "number_abbr_set",
        "automaton",
        "elision_chars",
        "boundary_class",
    )

    def __init__(self, lang_abbreviation_class):
        raw = lang_abbreviation_class.ABBREVIATIONS
        elision = getattr(lang_abbreviation_class, "ELISION_CHARACTERS", "")
        self.elision_chars = elision
        if elision:
            escaped_elision = re.escape(elision)
            self.boundary_class = rf"\s{escaped_elision}"
        else:
            self.boundary_class = r"\s"
        sorted_abbrs = sorted(raw, key=len, reverse=True)
        self.abbreviations = []
        self.automaton = AhoCorasickAutomaton()
        for idx, abbr in enumerate(sorted_abbrs):
            stripped = abbr.strip()
            stripped_lower = stripped.lower()
            escaped = re.escape(stripped)
            # Pre-compile the two findall patterns for this abbreviation
            if elision:
                match_re = re.compile(r"(?:^|\s|\r|\n|[{ec}]){esc}".format(ec=escaped_elision, esc=escaped), re.IGNORECASE)
            else:
                match_re = re.compile(r"(?:^|\s|\r|\n){}".format(escaped), re.IGNORECASE)
            next_word_re = re.compile(r"(?<={escaped}\. ).{{1}}".format(escaped=escaped), re.IGNORECASE)
            self.abbreviations.append(
                (
                    stripped,
                    stripped_lower,
                    escaped,
                    match_re,
                    next_word_re,
                )
            )
            # Add the trailing period to the automaton key. search_for_abbreviations
            # only ever acts on an abbreviation when it occurs at a word boundary
            # *followed by a period*; any such occurrence contains the substring
            # "<abbr>.", so keying on "<abbr>." is a byte-identical pre-filter that
            # skips the per-abbreviation full-text finditer for abbreviations whose
            # bare form merely appears inside other words (e.g. "al" in "called",
            # "no" in "no one") with no following period — the dominant cost on
            # real prose, where common short abbreviations match everywhere.
            #
            # Exception: the automaton is searched on ``text.lower()`` and U+0130
            # 'İ' is the only Unicode char whose .lower() changes length ('İ' ->
            # 'i' + U+0307 combining dot). An occurrence ending in 'İ' followed by
            # a period lowers to '...i̇.', so the "<abbr>." key (e.g. "vi.") would
            # not match. Abbreviations ending in 'i' therefore keep the bare key
            # (the original, always-correct behavior).
            key = stripped_lower if stripped_lower.endswith("i") else stripped_lower + "."
            self.automaton.add_pattern(key, idx)
        self.automaton.build()
        self.abbr_set = frozenset(a.strip().lower() for a in raw)
        self.prepositive_set = frozenset(a.lower() for a in lang_abbreviation_class.PREPOSITIVE_ABBREVIATIONS)
        self.number_abbr_set = frozenset(a.lower() for a in lang_abbreviation_class.NUMBER_ABBREVIATIONS)


class AbbreviationReplacer:
    _data_cache: dict[type, _AbbreviationData] = {}
    _cache_lock = RLock()
    CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE = False
    PROTECT_ALLCAPS_IMPRINT_SUFFIXES = False
    RESTORE_STANDALONE_I_BOUNDARIES = False

    # Opt-in for scripts (e.g. Greek, Cyrillic) that do not capitalize common
    # nouns mid-sentence: there, a capital letter following a multi-period
    # abbreviation's final period reliably marks a new sentence. The default
    # Latin sentence-start heuristic deliberately ignores these scripts; Latin
    # capital followers already flow through the split-mode ambiguity dial.
    NON_LATIN_CAPITAL_STARTS_SENTENCE = False

    AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST = frozenset(
        {
            # "st." is highly ambiguous (street vs Saint) and is often
            # sentence-final in address-like text.
            "st",
        }
    )

    # Prepositive abbreviations listed here are ambiguous: they often introduce
    # a following title/name ("Bankr. Court") but can also end a sentence
    # ("The 9th Cir. The panel reversed."). split_mode resolves that ambiguity.
    STARTER_AWARE_PREPOSITIVE: frozenset[str] = frozenset()
    TWO_LETTER_INITIALISM_SPLIT_MIN_RANK = 1
    UPPERCASE_INITIALISM_SPLIT_MIN_RANK = 1
    ALWAYS_JOIN_TWO_LETTER_INITIALISM_PHRASES = frozenset(
        {
            ("d.c", "circuit"),
            ("e.u", "commission"),
            ("l.a", "times"),
            ("u.n", "general", "assembly"),
            ("u.n", "secretary", "general"),
            ("u.n", "secretary-general"),
            ("u.n", "security", "council"),
            ("u.s", "court", "of"),
            ("u.s", "courts"),
            ("u.s", "department"),
            ("u.s", "district", "court"),
            ("u.s", "embassy"),
            ("u.s", "government"),
            ("u.s", "supreme", "court"),
        }
    )
    _UNKNOWN_PLACEHOLDER = "&ᓷ&&ᓷ&"
    _SENTENCE_START_OPENERS = frozenset("\"'“‘«([")

    def __init__(self, text: str, lang, split_mode: str = "balanced") -> None:
        self.text = text
        self.lang = lang
        abbr_class = lang.Abbreviation
        self.split_mode = split_mode
        with AbbreviationReplacer._cache_lock:
            if abbr_class not in AbbreviationReplacer._data_cache:
                AbbreviationReplacer._data_cache[abbr_class] = _AbbreviationData(lang.Abbreviation)
            self._data = AbbreviationReplacer._data_cache[abbr_class]

    @property
    def _leans_split(self) -> bool:
        """True in 'aggressive' mode: resolve ambiguous abbreviations toward a split."""
        return split_mode_rank(self.split_mode) >= 2

    @property
    def _leans_join(self) -> bool:
        """True in 'conservative' mode: resolve ambiguous abbreviations toward joining."""
        return split_mode_rank(self.split_mode) <= 0

    @staticmethod
    def _initials_chain_start(text: str, sep_index: int) -> int | None:
        """Return the start offset for initials ending before *sep_index*.

        The caller already matched the final protected separator after at least
        three uppercase initials.  Walk left over the compact ``X∯X∯X`` suffix
        instead of searching a growing prefix for every candidate.

        Only ASCII letters count as initials, mirroring the original
        ``[A-Za-z]`` regex: language profiles with a Unicode multi-period
        abbreviation regex (e.g. Greek) may absorb a leading non-ASCII initial
        into the protected chain, but walking back across it would reach the
        preceding determiner and wrongly allow a split before the surname.
        """
        chain_start = sep_index - 1
        if chain_start < 0 or not (text[chain_start].isascii() and text[chain_start].isalpha()):
            return None
        while (
            chain_start >= 2
            and text[chain_start - 1] == "∯"
            and text[chain_start - 2].isascii()
            and text[chain_start - 2].isalpha()
        ):
            chain_start -= 2
        return chain_start

    @staticmethod
    def _previous_whitespace_token(text: str, end_index: int) -> str:
        """Return the whitespace-delimited token before *end_index*."""
        word_end = end_index
        while word_end > 0 and text[word_end - 1].isspace():
            word_end -= 1
        word_start = word_end
        while word_start > 0 and not text[word_start - 1].isspace():
            word_start -= 1
        return text[word_start:word_end]

    def _i_looks_like_name_or_heading_continuation(self, match: re.Match[str]) -> bool:
        prev_word = self._previous_whitespace_token(self.text, match.start()).strip(",;:(")
        return bool(prev_word) and prev_word[0].isupper()

    @staticmethod
    def _next_whitespace_token(text: str, start_index: int) -> str:
        """Return the whitespace-delimited token at or after *start_index*."""
        word_start = start_index
        text_len = len(text)
        while word_start < text_len and text[word_start].isspace():
            word_start += 1
        word_end = word_start
        while word_end < text_len and not text[word_end].isspace():
            word_end += 1
        return text[word_start:word_end]

    def _is_initials_name(self, text: str, sep_index: int) -> bool:
        """Return True if the initialism ending at *sep_index* is a personal name.

        A run of single-letter initials (e.g. "F∯J∯G") followed by a single
        capitalized surname can be an "Initials + Surname" personal name, so
        conservative mode uses this structural check to keep the trailing period
        non-terminal.
        """
        return self._initials_chain_start(text, sep_index) is not None

    def _sentence_start_content_offset(self, text: str, start: int) -> int:
        index = start
        while index < len(text) and (text[index].isspace() or text[index] in self._SENTENCE_START_OPENERS):
            index += 1
        return index

    def _follower_is_likely_sentence_start(self, text: str, start: int) -> bool:
        return self._is_likely_sentence_start_at(text, self._sentence_start_content_offset(text, start))

    def _is_likely_sentence_start(self, text: str, start: int = 0) -> bool:
        """Check if the next non-space character in *text* looks like a sentence start.

        Subclasses (e.g. en_es_zh) can override to recognise additional scripts
        such as CJK ideographs. The supported override signature is
        ``(self, text, start=0)``.
        """
        return _next_nonspace_char_is_upper(text, start)

    def _is_likely_sentence_start_at(self, text: str, start: int) -> bool:
        return self._is_likely_sentence_start(text, start)

    def _is_capital_sentence_start_at(self, text: str, start: int) -> bool:
        if start >= len(text):
            return False
        if self._is_likely_sentence_start_at(text, start):
            return True
        return self.NON_LATIN_CAPITAL_STARTS_SENTENCE and text[start].isupper()

    def replace(self) -> str:
        self.text = apply_rules(
            self.text,
            self.lang.PossessiveAbbreviationRule,
            self.lang.KommanditgesellschaftRule,
            *self.lang.SingleLetterAbbreviationRules.All,
        )
        lines: list[str] = []
        for line in self.text.splitlines(True):
            lines.append(self.search_for_abbreviations_in_string(line))
        self.text = "".join(lines)
        self.replace_multi_period_abbreviations()
        # Protect compact time tokens with no space before them (e.g. "3P.M.")
        # so a.m./p.m. rules can decide boundary vs non-boundary using context.
        self.text = _COMPACT_AMPM_RE.sub(r"\1∯\2∯", self.text)
        # Restore a sentence-boundary period when an all-uppercase multi-period
        # abbreviation with 3+ parts (e.g. "S∯A∯T∯", "E∯S∯T∯") is followed
        # by a space and uppercase letter.
        # Only uppercase lookbehind so lowercase abbreviations like "a.k.a."
        # keep their non-boundary separator.
        restore_source = self.text

        def restore_uppercase_initialism_boundary(match):
            content_offset = self._sentence_start_content_offset(restore_source, match.end())
            if not self._is_capital_sentence_start_at(restore_source, content_offset):
                return match.group()
            # The surname reading and a genuine sentence boundary
            # ("…H.B.S. Applications are due.") are structurally identical, so
            # split-mode resolves the ambiguity: balanced/aggressive split by
            # default, while language profiles may raise the threshold for
            # name-heavy corpora.
            if split_mode_rank(self.split_mode) >= self.UPPERCASE_INITIALISM_SPLIT_MIN_RANK:
                return "."
            if self._is_initials_name(restore_source, match.start()):
                return match.group()
            return "."

        self.text = _UPPERCASE_INITIALISM_BOUNDARY_RE.sub(restore_uppercase_initialism_boundary, self.text)
        self.text = self.protect_allcaps_imprint_abbreviations()
        self.apply_ampm_boundary_rules()
        if self.RESTORE_STANDALONE_I_BOUNDARIES:
            self.text = self.restore_standalone_i_boundaries()
        return self.text

    def apply_ampm_boundary_rules(self, restore_non_ascii: bool = True) -> None:
        """Apply a.m./p.m. handling to ``self.text``, honoring the split-bias.

        In 'conservative' mode the a.m./p.m. periods stay protected before a
        capital ("3 p.m. Please …" stays joined) — only the structural spacing
        normalizer runs. Otherwise the boundary-restore rules fire. Subclasses
        that override ``replace`` should call this instead of applying
        ``AmPmRules.All`` directly, so the dial works for every language.
        *restore_non_ascii* is opt-out for profiles that never restored
        non-ASCII a.m./p.m. boundaries (e.g. German).
        """
        if self._leans_join:
            self.text = apply_rules(self.text, self.lang.AmPmRules.SpacedAmPmRule)
            return
        self.text = apply_rules(self.text, *self.lang.AmPmRules.All)
        if restore_non_ascii:
            self.text = self.restore_non_ascii_ampm_boundaries()

    # An all-caps word (2+ letters) immediately followed, across whitespace, by
    # another all-caps word (2+ letters). Used to detect imprint/colophon runs
    # like "CHARLES WHITTINGHAM AND CO. TOOKS COURT".
    _ALLCAPS_IMPRINT_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,})\.(?=\s+[A-Z]{2,}\b)")
    _ALLCAPS_IMPRINT_COMPANY_ABBREVIATIONS = frozenset({"bros", "co", "corp", "inc", "ltd"})

    def protect_allcaps_imprint_abbreviations(self) -> str:
        """Keep a known abbreviation's period non-terminal inside an all-caps run.

        In an all-caps imprint/colophon (e.g. "...AND CO. TOOKS COURT, LONDON.")
        a company-style abbreviation such as "CO." is a name continuation, not a
        sentence end, even though the following all-caps token would normally be
        read as a sentence start. Only the narrow set of company suffixes that
        motivated this heuristic is protected, so ordinary all-caps sentence
        boundaries after other abbreviations ("IT HAPPENED IN DEC. THE END.")
        still split.
        """
        if not self.PROTECT_ALLCAPS_IMPRINT_SUFFIXES:
            return self.text

        def _protect(match):
            if match.group(1).lower() not in self._ALLCAPS_IMPRINT_COMPANY_ABBREVIATIONS:
                return match.group()
            return match.group(1) + "∯"

        return self._ALLCAPS_IMPRINT_RE.sub(_protect, self.text)

    def restore_standalone_i_boundaries(self) -> str:
        def _restore(match):
            content_offset = self._sentence_start_content_offset(self.text, match.end())
            if not self._is_capital_sentence_start_at(self.text, content_offset):
                return match.group()
            if self._i_looks_like_name_or_heading_continuation(match):
                return "I." if self._leans_split else match.group()
            return "I."

        return _STANDALONE_I_BOUNDARY_RE.sub(_restore, self.text)

    @staticmethod
    def _two_letter_initialism_key(parts: list[str]) -> str:
        return ".".join(parts).lower()

    @staticmethod
    def _normalize_follower_token(token: str) -> str:
        normalized = token.strip(",.;:([{)]}\"'“”‘’").lower()
        for possessive_suffix in ("'s", "’s"):
            if normalized.endswith(possessive_suffix):
                return normalized[: -len(possessive_suffix)]
        return normalized

    def _next_normalized_words(self, start_index: int, limit: int) -> tuple[str, ...]:
        words = []
        word_start = start_index
        text_len = len(self.text)
        while len(words) < limit:
            while word_start < text_len and self.text[word_start].isspace():
                word_start += 1
            if word_start >= text_len:
                break
            word_end = word_start
            while word_end < text_len and not self.text[word_end].isspace():
                word_end += 1
            word = self._normalize_follower_token(self.text[word_start:word_end])
            if word:
                words.append(word)
            word_start = word_end
        return tuple(words)

    def _two_letter_initialism_has_always_joined_follower(self, parts: list[str], content_offset: int) -> bool:
        initialism_key = self._two_letter_initialism_key(parts)
        max_words = max((len(phrase) - 1 for phrase in self.ALWAYS_JOIN_TWO_LETTER_INITIALISM_PHRASES), default=0)
        followers = self._next_normalized_words(content_offset, max_words)
        for word_count in range(1, len(followers) + 1):
            if (initialism_key, *followers[:word_count]) in self.ALWAYS_JOIN_TWO_LETTER_INITIALISM_PHRASES:
                return True
        return False

    def replace_multi_period_abbreviations(self) -> None:
        def mpa_replace(match):
            matched = match.group()
            parts = matched[:-1].split(".")
            next_start = match.end()
            protect_final_period = True

            # Keep sentence-final boundaries for multi-period abbreviations when
            # a likely new sentence starts next. Conservative mode keeps the
            # joined reading for acronym/capital ambiguity; balanced/aggressive
            # split it consistently.
            #
            # Split-bias: 'conservative' never treats the final period as a
            # boundary (so "Ph.D. Smith" stays joined); balanced/aggressive
            # split mixed abbreviations, uppercase two-letter initialisms, and
            # 3+ uppercase initialisms before likely sentence starts.
            content_offset = self._sentence_start_content_offset(self.text, next_start)
            likely_start = self._is_likely_sentence_start_at(self.text, content_offset)
            two_letter_uppercase_initialism = len(parts) == 2 and all(len(part) == 1 and part.isupper() for part in parts)
            two_letter_initialism = (
                two_letter_uppercase_initialism
                and split_mode_rank(self.split_mode) >= self.TWO_LETTER_INITIALISM_SPLIT_MIN_RANK
            )
            uppercase_initialism = (
                len(parts) >= 3
                and all(part.isupper() for part in parts)
                and split_mode_rank(self.split_mode) >= self.UPPERCASE_INITIALISM_SPLIT_MIN_RANK
            )
            split_candidate = any(len(part) > 1 for part in parts) or two_letter_initialism or uppercase_initialism
            # Greek/Cyrillic etc. (opt-in): a capital follower reliably starts a
            # new sentence, so a pure single-letter initialism ("π.Χ.", "Ε.Ε.")
            # ends the sentence before it even though _is_latin_upper ignored it.
            capital_boundary = (
                self.NON_LATIN_CAPITAL_STARTS_SENTENCE
                and not likely_start
                and content_offset < len(self.text)
                and self.text[content_offset].isupper()
            )
            # a.m./p.m. own their boundary decision later (with timezone and
            # numeric-time awareness), so the generic multi-period split skips
            # them to avoid breaking a "p.m. EST" time+zone unit.
            is_ampm = matched[:-1].lower().replace(".", "") in {"am", "pm"}
            has_always_joined_follower = (
                two_letter_uppercase_initialism
                and self._two_letter_initialism_has_always_joined_follower(parts, content_offset)
            )
            if self._leans_join:
                protect_final_period = True
            elif has_always_joined_follower:
                protect_final_period = True
            elif not is_ampm and ((split_candidate and likely_start) or capital_boundary):
                protect_final_period = False

            body = matched[:-1].replace(".", "∯")
            tail = "∯" if protect_final_period else "."
            return body + tail

        self.text = ensure_compiled(self.lang.MULTI_PERIOD_ABBREVIATION_REGEX, re.IGNORECASE).sub(mpa_replace, self.text)

    def restore_non_ascii_ampm_boundaries(self) -> str:
        """Restore sentence boundaries after a.m./p.m. before non-ASCII capitals."""

        def _restore(match):
            if _next_nonspace_char_is_non_ascii_upper(self.text, match.end()):
                return f"{match.group(1)}."
            return match.group()

        self.text = _NON_ASCII_AMPM_RE.sub(_restore, self.text)
        self.text = _NON_ASCII_AMPM_SPACED_RE.sub(_restore, self.text)
        return self.text

    def replace_period_of_abbr(self, txt: str, abbr: str, escaped: str | None = None) -> str:
        txt = " " + txt
        if escaped is None:
            escaped = re.escape(abbr.strip())
        boundary = self._data.boundary_class
        txt = re.sub(
            r"(?<=[{boundary}]{abbr})\.(?=((\.|\:|-|\?|,)|(\s([a-z]|I\s|I'm|I'll|\d|\())))".format(
                boundary=boundary, abbr=escaped
            ),
            "∯",
            txt,
        )
        return txt[1:]

    def search_for_abbreviations_in_string(self, text: str) -> str:
        lowered = text.lower()
        data = self._data
        found_indices = data.automaton.search(lowered)
        abbreviations = data.abbreviations
        for idx in sorted(found_indices):
            stripped, stripped_lower, escaped, match_re, next_word_re = abbreviations[idx]
            # Capture each occurrence that is actually followed by a period
            # together with its OWN following character (the char after
            # "abbr. ", else ""). Computing both from the same match keeps them
            # aligned — the previous code zipped two independent findall() lists
            # of different lengths, so the case heuristic was read from the wrong
            # occurrence. A period-less occurrence (e.g. a decoy "Cir held"
            # before the real "Cir.") has no period to protect; processing it
            # would run a broad global re.sub that wrongly mutates the period of
            # a *different* occurrence, so it is skipped entirely.
            occurrences = []
            for m in match_re.finditer(text):
                end = m.end()
                if text[end : end + 1] != ".":
                    continue
                char = text[end + 2 : end + 3] if text[end : end + 2] == ". " else ""
                occurrences.append((m.group(), char))
            # scan_for_replacements performs a *global* re.sub keyed only on (am,
            # char), so identical occurrences yield identical, idempotent edits.
            # Deduplicate them to keep work linear instead of O(occurrences × N)
            # on long, repetitive, newline-free input.
            for am, char in dict.fromkeys(occurrences):
                text = self.scan_for_replacements(text, am, 0, (char,), stripped, escaped)
        return text

    def _replace_number_abbr(self, txt: str, am_escaped: str, boundary: str, upper: bool) -> str:
        """Protect period after number abbreviations before digits and Roman numerals."""
        if upper:
            if self._leans_join:
                # conservative: a capitalized follower ("Fig. Several") is read
                # as a continuation, not a new sentence — protect (join).
                return _replace_with_escape(txt, am_escaped, r"\.(?=\s[^\W\d_])", "∯", boundary)
            # balanced/aggressive: protect only before Roman numerals (Vol. IV).
            # Exclude lone "I" to avoid false joins with the pronoun "I".
            return _replace_with_escape(txt, am_escaped, r"\.(?=\s(?:[IVXLCDM]{2,}|[VXLCDM])\b)", "∯", boundary)
        txt = _replace_with_escape(txt, am_escaped, r"\.(?=(\s\d|\s+\(|\s\?\?(?!\?)|\s[IVXLCDM]+\b))", "∯", boundary)
        return self._protect_number_abbr_unknown_placeholder(txt, am_escaped, boundary)

    def _protect_number_abbr_unknown_placeholder(self, txt: str, am_escaped: str, boundary: str) -> str:
        txt = " " + txt
        txt = re.sub(rf"(?<=[{boundary}]{am_escaped}∯)\s\?\?(?!\?)", f" {self._UNKNOWN_PLACEHOLDER}", txt)
        return txt[1:]

    def _replace_starter_aware_prepositive(self, txt: str, am_escaped: str, boundary: str) -> str:
        txt = " " + txt
        pattern = re.compile(rf"(?<=[{boundary}]{am_escaped})\.(?=(\s|:\d+))")

        def _protect_or_restore(match):
            if txt[match.end() : match.end() + 1] == ":":
                return "∯"
            if self._follower_is_likely_sentence_start(txt, match.end()):
                return "."
            return "∯"

        return pattern.sub(_protect_or_restore, txt)[1:]

    def scan_for_replacements(
        self, txt: str, am: str, ind: int, char_array, stripped: str = "", escaped: str | None = None
    ) -> str:
        try:
            char = char_array[ind]
        except IndexError:
            char = ""
        use_case_heuristic = self.CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE
        upper = char.isupper() if (char and use_case_heuristic) else False
        am_stripped = am.strip()
        # Strip leading elision characters (e.g. apostrophe in "l'Avv") so the
        # bare abbreviation is used for set lookups and replacement patterns.
        elision = self._data.elision_chars
        if elision and am_stripped and am_stripped[0] in elision:
            am_stripped = am_stripped[1:]
        am_lower = am_stripped.lower()
        boundary = self._data.boundary_class
        if not upper or am_lower in self._data.prepositive_set or am_lower in self._data.number_abbr_set:
            am_escaped = re.escape(am_stripped)
            if am_lower in self._data.prepositive_set:
                should_protect = not (self._leans_split and am_lower in self.AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST)
                if should_protect:
                    if am_lower in self.STARTER_AWARE_PREPOSITIVE and self._leans_split:
                        txt = self._replace_starter_aware_prepositive(txt, am_escaped, boundary)
                    else:
                        txt = _replace_with_escape(txt, am_escaped, r"\.(?=(\s|:\d+))", "∯", boundary)
            elif am_lower in self._data.number_abbr_set:
                txt = self._replace_number_abbr(txt, am_escaped, boundary, upper)
                # Multi-char number abbreviations (eq, pt, fig, vol, …) also
                # need regular abbreviation protection before lowercase text.
                # Single-char entries like "p" are excluded — they are too
                # ambiguous (e.g. "p" is also part of "p.m.").
                if not upper and len(am_stripped) > 1:
                    txt = self.replace_period_of_abbr(txt, am_stripped, am_escaped)
            else:
                txt = self.replace_period_of_abbr(txt, am_stripped, am_escaped)
        return txt
