# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from collections import deque

from sentencesplit.utils import (
    _next_nonspace_char,
    _next_nonspace_char_is_non_ascii_upper,
    _next_nonspace_char_is_upper,
    apply_rules,
    ensure_compiled,
    split_mode_rank,
)


class AhoCorasickAutomaton:
    """Pure-Python Aho-Corasick automaton for multi-pattern substring search."""

    __slots__ = ("goto", "fail", "output", "_built")

    def __init__(self):
        # State 0 is the root. Each state maps char -> next_state.
        self.goto: list[dict[str, int]] = [{}]
        self.output: list[list[int]] = [[]]  # pattern IDs at each state
        self.fail: list[int] = [0]
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
        self._built = True

    def search(self, text: str) -> set[int]:
        """Scan text in one pass, return set of matched pattern IDs."""
        state = 0
        found: set[int] = set()
        goto = self.goto
        fail = self.fail
        output = self.output
        for ch in text:
            while state != 0 and ch not in goto[state]:
                state = fail[state]
            state = goto[state].get(ch, 0)
            if output[state]:
                found.update(output[state])
        return found


def _replace_with_escape(txt: str, escaped: str, suffix_pattern: str, replacement: str, boundary_class: str = r"\s") -> str:
    """Replace period after abbreviation match using pre-escaped abbreviation."""
    txt = " " + txt
    txt = re.sub(rf"(?<=[{boundary_class}]{escaped}){suffix_pattern}", replacement, txt)
    return txt[1:]


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
            self.automaton.add_pattern(stripped_lower, idx)
        self.automaton.build()
        self.abbr_set = frozenset(a.strip().lower() for a in raw)
        self.prepositive_set = frozenset(a.lower() for a in lang_abbreviation_class.PREPOSITIVE_ABBREVIATIONS)
        self.number_abbr_set = frozenset(a.lower() for a in lang_abbreviation_class.NUMBER_ABBREVIATIONS)


class AbbreviationReplacer:
    _data_cache: dict[type, _AbbreviationData] = {}
    _boundary_regex_cache: dict[type, re.Pattern[str] | None] = {}
    SENTENCE_STARTERS = []
    SENTENCE_BOUNDARY_ABBREVIATIONS = ["U∯S", "U.S", "U∯K", "E∯U", "E.U", "U∯S∯A", "U.S.A", "I", "i.v", "I.V"]

    # Opt-in for scripts (e.g. Greek, Cyrillic) that do not capitalize common
    # nouns mid-sentence: there, a capital letter following a multi-period
    # abbreviation's final period reliably marks a new sentence, so even a pure
    # single-letter initialism ("π.Χ.", "Ε.Ε.") ends the sentence before it. The
    # Latin sentence-start heuristic (_is_latin_upper) deliberately ignores these
    # scripts, so without this flag their abbreviation boundaries never restore.
    # Off by default — for Latin scripts a capital follower is ambiguous with a
    # proper-noun continuation ("A.I. Systems").
    NON_LATIN_CAPITAL_STARTS_SENTENCE = False

    AGGRESSIVE_PREPOSITIVE_BOUNDARY_BLOCKLIST = frozenset(
        {
            # "st." is highly ambiguous (street vs Saint) and is often
            # sentence-final in address-like text.
            "st",
        }
    )

    # Prepositive abbreviations listed here will allow sentence splits
    # before known sentence starters.  E.g. "Cir. The panel reversed."
    # splits, while "Bankr. Court approved the plan." stays joined.
    # Only effective when SENTENCE_STARTERS is non-empty.
    STARTER_AWARE_PREPOSITIVE: frozenset[str] = frozenset()

    def __init__(self, text: str, lang, split_mode: str = "balanced") -> None:
        self.text = text
        self.lang = lang
        abbr_class = lang.Abbreviation
        self.split_mode = split_mode
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

    # Articles/determiners that mark a following initialism as a noun
    # (e.g. "the S.A.T.", "un M.B.A."), not the initials of a personal name.
    # Covers the common articles of the Latin-script languages so the chained
    # initials name heuristic does not over-join acronym nouns before a new
    # sentence.  Languages may extend this set.
    _INITIALS_NAME_DETERMINERS = frozenset(
        {
            "the",
            "a",
            "an",  # en
            "el",
            "la",
            "los",
            "las",
            "un",
            "una",
            "unos",
            "unas",  # es
            "de",
            "het",
            "een",  # nl
            "le",
            "les",
            "une",
            "des",  # fr
            "der",
            "die",
            "das",
            "ein",
            "eine",  # de
            "il",
            "lo",
            "gli",
            "uno",  # it ("una" already covered above)
            "o",
            "os",
            "um",
            "uma",
            "uns",
            "umas",  # pt
        }
    )

    # Matches a run of single-letter initials protected as "X∯X∯…X∯", ending at
    # the position of the final separator that the restore is examining.
    _INITIALS_CHAIN_RE = re.compile(r"(?:[A-Za-z]∯)+[A-Za-z]\Z")

    # First whitespace-delimited token after the initialism separator.
    _FOLLOWER_WORD_RE = re.compile(r"\s+(\S+)")

    def _is_initials_name(self, text: str, sep_index: int) -> bool:
        """Return True if the initialism ending at *sep_index* is a personal name.

        A run of single-letter initials (e.g. "F∯J∯G") followed by a single
        capitalized surname is an "Initials + Surname" personal name, so its
        trailing period must not be restored as a boundary.  Two cues mark the
        initialism as a sentence-ending noun instead (and keep the boundary):
        an article/determiner before it ("the S.A.T.") or a known sentence
        starter after it ("from H.B.S. She ...").
        """
        chain = self._INITIALS_CHAIN_RE.search(text[:sep_index])
        if chain is None:
            return False
        before = text[: chain.start()].rstrip()
        prev_word = before.rsplit(None, 1)[-1] if before else ""
        if prev_word.lower() in self._INITIALS_NAME_DETERMINERS:
            return False
        if self.SENTENCE_STARTERS:
            follower = self._FOLLOWER_WORD_RE.match(text[sep_index + 1 :])
            if follower and follower.group(1).rstrip(",.;:") in self.SENTENCE_STARTERS:
                return False
        return True

    def _is_likely_sentence_start(self, text: str) -> bool:
        """Check if the next non-space character in *text* looks like a sentence start.

        Subclasses (e.g. en_es_zh) can override to recognise additional scripts
        such as CJK ideographs.
        """
        return _next_nonspace_char_is_upper(text)

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
        self.text = re.sub(r"(?<=\d)([AaPp])\.([Mm])\.", r"\1∯\2∯", self.text)
        # Restore sentence-boundary period when an all-uppercase multi-period
        # abbreviation with 3+ parts (e.g. "S∯A∯T∯", "E∯S∯T∯") is followed
        # by a space and uppercase letter.  Two-part abbreviations like U∯S∯
        # are handled separately by replace_abbreviation_as_sentence_boundary.
        # Only uppercase lookbehind so lowercase abbreviations like "a.k.a."
        # keep their non-boundary separator.
        restore_source = self.text

        def restore_uppercase_initialism_boundary(match):
            next_text = restore_source[match.end() :]
            char = _next_nonspace_char(next_text)
            if not (char and char.isupper() and char.isascii()):
                return match.group()
            # A run of single-letter initials (e.g. "F.J.G.", protected as
            # "F∯J∯G∯") immediately followed by a single capitalized token is an
            # "Initials + Surname" personal name, not a sentence end — keep the
            # final separator non-terminal.  An initialism used as a noun
            # ("the S.A.T."), where an article/determiner precedes it, is still
            # treated as a possible boundary so a following capital can split.
            #
            # The surname reading and a genuine sentence boundary
            # ("…H.B.S. Applications are due.") are structurally identical, so
            # 'aggressive' mode resolves the ambiguity toward splitting (at the
            # cost of splitting real "Initials + Surname" names too).
            if self._leans_split:
                return "."
            if self._is_initials_name(restore_source, match.start()):
                return match.group()
            return "."

        self.text = re.sub(r"(?<=[A-Z]∯[A-Z]∯[A-Z])∯(?=\s)", restore_uppercase_initialism_boundary, self.text)
        self.text = self.protect_allcaps_imprint_abbreviations()
        self.apply_ampm_boundary_rules()
        self.text = self.replace_abbreviation_as_sentence_boundary()
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

    def protect_allcaps_imprint_abbreviations(self) -> str:
        """Keep a known abbreviation's period non-terminal inside an all-caps run.

        In an all-caps imprint/colophon (e.g. "...AND CO. TOOKS COURT, LONDON.")
        a company-style abbreviation such as "CO." is a name continuation, not a
        sentence end, even though the following all-caps token would normally be
        read as a sentence start. Only known multi-letter abbreviations flanked
        by all-caps tokens are protected, so ordinary all-caps words that end a
        sentence ("THE END. THE BEGINNING.") still split.
        """
        if not self.SENTENCE_STARTERS:
            return self.text
        abbr_set = self._data.abbr_set

        def _protect(match):
            if match.group(1).lower() not in abbr_set:
                return match.group()
            return match.group(1) + "∯"

        return self._ALLCAPS_IMPRINT_RE.sub(_protect, self.text)

    @classmethod
    def _get_boundary_regex(cls) -> re.Pattern[str] | None:
        if cls not in cls._boundary_regex_cache:
            boundary_abbr = "|".join(re.escape(abbr).replace(r"\.", r"[.∯]") for abbr in cls.SENTENCE_BOUNDARY_ABBREVIATIONS)
            if not boundary_abbr:
                cls._boundary_regex_cache[cls] = None
            elif cls.SENTENCE_STARTERS:
                sent_starters = "|".join(r"(?=\s{}\s)".format(re.escape(word)) for word in cls.SENTENCE_STARTERS)
                cls._boundary_regex_cache[cls] = re.compile(
                    r"(?<![A-Za-z0-9_∯])({})∯({})".format(boundary_abbr, sent_starters)
                )
            else:
                cls._boundary_regex_cache[cls] = re.compile(r"(?<![A-Za-z0-9_∯])({})∯".format(boundary_abbr))
        return cls._boundary_regex_cache[cls]

    def replace_abbreviation_as_sentence_boundary(self) -> str:
        regex = type(self)._get_boundary_regex()
        if regex is None:
            return self.text
        self.text = regex.sub("\\1.", self.text)
        return self.text

    def replace_multi_period_abbreviations(self) -> None:
        def mpa_replace(match):
            matched = match.group()
            parts = matched[:-1].split(".")
            next_text = self.text[match.end() :]
            protect_final_period = True

            # Keep sentence-final boundaries for mixed abbreviations like Ph.D.
            # when a likely new sentence starts next, but continue protecting
            # pure initialisms like A.I. before uppercase nouns.
            #
            # Split-bias: 'conservative' never treats the final period as a
            # boundary (so "Ph.D. Smith" stays joined); 'aggressive' splits
            # before any likely sentence start, including pure initialisms
            # ("A.I. Systems …").
            likely_start = self._is_likely_sentence_start(next_text)
            # Greek/Cyrillic etc. (opt-in): a capital follower reliably starts a
            # new sentence, so a pure single-letter initialism ("π.Χ.", "Ε.Ε.")
            # ends the sentence before it even though _is_latin_upper ignored it.
            capital_boundary = (
                self.NON_LATIN_CAPITAL_STARTS_SENTENCE and not likely_start and _next_nonspace_char(next_text).isupper()
            )
            # a.m./p.m. own their boundary decision later (with timezone
            # awareness), so the aggressive pure-initialism split skips them to
            # avoid breaking a "p.m. EST" time+zone unit.
            is_ampm = matched[:-1].lower().replace(".", "") in {"am", "pm"}
            if self._leans_join:
                protect_final_period = True
            elif self._leans_split and not is_ampm:
                protect_final_period = not (likely_start or capital_boundary)
            elif (likely_start and any(len(part) > 1 for part in parts)) or capital_boundary:
                protect_final_period = False

            body = matched[:-1].replace(".", "∯")
            tail = "∯" if protect_final_period else "."
            return body + tail

        self.text = ensure_compiled(self.lang.MULTI_PERIOD_ABBREVIATION_REGEX, re.IGNORECASE).sub(mpa_replace, self.text)

    def restore_non_ascii_ampm_boundaries(self) -> str:
        """Restore sentence boundaries after a.m./p.m. before non-ASCII capitals."""

        def _restore(match):
            next_text = self.text[match.end() :]
            if _next_nonspace_char_is_non_ascii_upper(next_text):
                return f"{match.group(1)}."
            return match.group()

        self.text = re.sub(r"(?<![a-zA-Z])([AaPp]∯[Mm])∯(?=\s)", _restore, self.text)
        self.text = re.sub(r"(?<![a-zA-Z])([AaPp]∯\s+[Mm])∯(?=\s)", _restore, self.text)
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
        return _replace_with_escape(txt, am_escaped, r"\.(?=(\s\d|\s+\(|\s\?\?|\s[IVXLCDM]+\b))", "∯", boundary)

    def _prepositive_suffix(self, am_lower: str, upper: bool, char: str) -> str:
        """Return the regex suffix pattern for protecting a prepositive abbreviation."""
        # Court/tribunal-style prepositives (en_legal's STARTER_AWARE set) can
        # also legitimately end a sentence. Split-bias governs how eagerly:
        #   conservative — protect like any prepositive (always join);
        #   balanced     — split only before a *known* sentence starter;
        #   aggressive   — split before any capitalized follower (e.g.
        #                  "Bankr. Court" becomes a boundary).
        if self.SENTENCE_STARTERS and am_lower in self.STARTER_AWARE_PREPOSITIVE and not self._leans_join:
            if self._leans_split:
                return r"\.(?=(\s(?![A-Z])|:\d+))"
            # Exclude single-char starters like "A" and "I" — they
            # often appear as identifiers after prepositive
            # abbreviations (e.g. "Sched. A", "Amend. I").
            starters = "|".join(re.escape(s) for s in self.SENTENCE_STARTERS if len(s) > 1)
            if upper:
                return rf"\.(?=(\s(?!(?:{starters})\s)|:\d+))"
            if char and not char.isalpha():
                # First char is non-alpha (e.g. opening quote/bracket).
                # Allow splits before quoted sentence starters like:
                # Cir. "The panel reversed," he wrote.
                open_q = r"""[\"'\u201c\u00ab(\[]*"""
                return rf"\.(?=(\s(?!{open_q}(?:{starters})\s)|:\d+))"
        return r"\.(?=(\s|:\d+))"

    def scan_for_replacements(
        self, txt: str, am: str, ind: int, char_array, stripped: str = "", escaped: str | None = None
    ) -> str:
        try:
            char = char_array[ind]
        except IndexError:
            char = ""
        use_case_heuristic = bool(self.SENTENCE_STARTERS)
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
                    suffix = self._prepositive_suffix(am_lower, upper, char)
                    txt = _replace_with_escape(txt, am_escaped, suffix, "∯", boundary)
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
