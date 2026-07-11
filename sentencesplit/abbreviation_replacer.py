# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from threading import RLock

from sentencesplit._abbreviation_data import _AbbreviationData
from sentencesplit.utils import (
    _next_nonspace_char_is_non_ascii_upper,
    _next_nonspace_char_is_upper,
    apply_rules,
    ensure_compiled,
    split_mode_rank,
)

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


# --------------------------------------------------------------------------- #
# Downstream per-period post-stages (S1 — completing the single-pass model).
#
# These were a fixed sequence hard-coded in ``AbbreviationReplacer.replace()``;
# they are now ``(replacer) -> None`` primitives that an ``AbbrPolicy`` lists in
# ``post_stages``, so a language declares its post-classifier pipeline as data.
# Each mutates ``replacer.text`` and self-gates on the same class flags as before,
# so the assembled tuples reproduce the historical behavior byte-for-byte. They
# still run AFTER the per-line classifier and continue to read the ``∯`` IR the
# classifier (and earlier stages) produce — i.e. they are *owned by the policy*
# now, but not yet out-of-band (S4 deletes the sentinel only once they are).
# --------------------------------------------------------------------------- #
def _stage_multi_period(r: "AbbreviationReplacer") -> None:
    r.replace_multi_period_abbreviations()


def _stage_compact_ampm(r: "AbbreviationReplacer") -> None:
    # Protect compact time tokens with no space before them (e.g. "3P.M.") so the
    # a.m./p.m. rules can decide boundary vs non-boundary using context.
    r.text = _COMPACT_AMPM_RE.sub(r"\1∯\2∯", r.text)


def _stage_uppercase_initialism(r: "AbbreviationReplacer") -> None:
    r.text = r._restore_uppercase_initialism_boundaries()


def _stage_allcaps_imprint(r: "AbbreviationReplacer") -> None:
    r.text = r.protect_allcaps_imprint_abbreviations()


def _stage_ampm_rules(r: "AbbreviationReplacer") -> None:
    r.apply_ampm_boundary_rules()


def _stage_ampm_rules_ascii_only(r: "AbbreviationReplacer") -> None:
    # German never restored non-ASCII a.m./p.m. boundaries.
    r.apply_ampm_boundary_rules(restore_non_ascii=False)


def _stage_standalone_i(r: "AbbreviationReplacer") -> None:
    if r.RESTORE_STANDALONE_I_BOUNDARIES:
        r.text = r.restore_standalone_i_boundaries()


# The historical full post-classifier sequence (english/en_legal/greek/zh/ja/...
# all inherit this when their policy leaves ``post_stages`` as None).
DEFAULT_POST_STAGES = (
    _stage_multi_period,
    _stage_compact_ampm,
    _stage_uppercase_initialism,
    _stage_allcaps_imprint,
    _stage_ampm_rules,
    _stage_standalone_i,
)

# German's reduced pipeline (no Kommanditgesellschaft / compact-ampm /
# uppercase-initialism / allcaps-imprint / standalone-I passes; a.m./p.m. without
# the non-ASCII boundary restore). Previously the body of ``Deutsch...replace()``.
GERMAN_POST_STAGES = (
    _stage_multi_period,
    _stage_ampm_rules_ascii_only,
)


class AbbreviationReplacer:
    _data_cache: dict[type, _AbbreviationData] = {}
    _cache_lock = RLock()
    CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE = False
    PROTECT_ALLCAPS_IMPRINT_SUFFIXES = False
    RESTORE_STANDALONE_I_BOUNDARIES = False

    # Single-pass period classifier. The per-line abbreviation-protection step
    # always routes through PeriodClassifier. ABBR_POLICY selects the per-language
    # policy by data; None resolves to period_classifier.BASE_POLICY lazily.
    ABBR_POLICY = None

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
    SENTENCE_BOUNDARY_ABBREVIATIONS: frozenset[str] = frozenset()
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

    # English-honorific DEFAULT for the shared title-prefix heuristic, and an
    # explicit per-language-overridable policy.
    #
    # Personal-title / honorific abbreviations that can introduce a name and chain
    # in front of a degree abbreviation ("Dr. Ph.D. Smith"). Used by
    # ``_preceding_token_is_title_prefix`` (reached from ``_is_titled_name_prefix``)
    # to tell a genuine title chain from an unrelated protected prepositive that
    # merely precedes a capitalized degree token (a geographic "Mt." or a legal
    # "v." is NOT a personal title, so "We climbed Mt. Ph.D. Smith advised her."
    # still splits).
    #
    # Altitude / override contract:
    #   * This is the ENGLISH-HONORIFIC DEFAULT. Because it is a class attribute on
    #     the shared base ``AbbreviationReplacer``, every Latin-script language
    #     (es, fr, it, de, ... as well as en and en_legal) inherits this exact set
    #     unchanged via class inheritance — no language overrides it today.
    #   * A language customizes the policy by setting
    #     ``NAME_TITLE_PREFIX_ABBREVIATIONS`` in its OWN ``AbbreviationReplacer``
    #     subclass. ``_is_titled_name_prefix`` reads it as
    #     ``self.NAME_TITLE_PREFIX_ABBREVIATIONS`` (see below), so a subclass
    #     attribute transparently wins. To extend rather than replace the default,
    #     do as ``en_legal`` does for ``STARTER_AWARE_PREPOSITIVE``, e.g.
    #     ``NAME_TITLE_PREFIX_ABBREVIATIONS = (
    #         AbbreviationReplacer.NAME_TITLE_PREFIX_ABBREVIATIONS | frozenset({"qc"})
    #     )``.
    #
    # Format contract: each entry is the BARE LOWERCASE form with periods stripped
    # (so "Dr." -> "dr", "Ph.D." -> "phd"). Include any degree forms used in chains
    # (e.g. "phd", "md") so a longer chain ("Ph.D. M.D. Smith") also links.
    NAME_TITLE_PREFIX_ABBREVIATIONS: frozenset[str] = frozenset(
        {
            "dr",
            "mr",
            "mrs",
            "ms",
            "miss",
            "mx",
            "prof",
            "rev",
            "hon",
            "sr",
            "fr",
            "sir",
            "dame",
            "gen",
            "col",
            "capt",
            "lt",
            "sgt",
            "maj",
            "sen",
            "rep",
            "gov",
            "pres",
            "phd",
            "md",
            "dds",
            "esq",
        }
    )

    def __init__(self, text: str, lang, split_mode: str = "balanced") -> None:
        self.text = text
        self.lang = lang
        abbr_class = lang.Abbreviation
        self.split_mode = split_mode
        with AbbreviationReplacer._cache_lock:
            if abbr_class not in AbbreviationReplacer._data_cache:
                AbbreviationReplacer._data_cache[abbr_class] = _AbbreviationData(lang.Abbreviation)
            self._data = AbbreviationReplacer._data_cache[abbr_class]

    def _period_classifier(self):
        """Return a PeriodClassifier, reusing the one cached per
        ``(policy, split_mode, replacer_cls)`` on the shared ``_AbbreviationData``.

        The classifier's compiled ``RE_*`` suffix patterns and ``_full_cache`` are
        line-independent and depend only on ``(policy, split_mode, data)`` — all
        immutable for a given ``_AbbreviationData`` — so one classifier serves every
        per-call ``AbbreviationReplacer`` instance, avoiding ~9 regex compiles and a
        cold full-pattern cache on each ``segment()`` call. It reuses the SAME
        ``_AbbreviationData`` (automaton + sets), never rebuilding the keys or the
        automaton, preserving the U+0130 İ exception and the publish-after-build
        thread-safety invariant.

        The classifier's back-reference (``self.r``) is bound ONCE, at construction,
        to a document-free *reference* replacer of this class — never rebound to the
        live, document-holding instance. Everything the classifier reads through the
        back-ref (``CAPITALIZED_FOLLOWER_IS_BOUNDARY_CUE``, ``STARTER_AWARE_PREPOSITIVE``,
        ``_follower_is_likely_sentence_start``, ``_UNKNOWN_PLACEHOLDER`` …) is
        class-level, so a same-class reference is interchangeable with the live one.
        Binding to the class (not the instance) keeps the process-global cache free
        of any caller's input text (no retention) and immune to a per-call back-ref
        rebind race when concurrent ``segment()`` calls share one classifier.
        """
        pc = getattr(self, "_pc", None)
        if pc is not None:
            return pc
        # Local import keeps imports lazy and avoids a cycle.
        from sentencesplit.period_classifier import BASE_POLICY, PeriodClassifier

        policy = self.ABBR_POLICY if self.ABBR_POLICY is not None else BASE_POLICY
        cls = type(self)
        key = (id(policy), self.split_mode, cls)
        cache = self._data._classifier_cache
        pc = cache.get(key)
        if pc is None:
            # Build against a document-free reference replacer of THIS class so the
            # cached classifier never pins a caller's input text or language class
            # and reads only class-level config through its back-ref.
            reference = cls("", self.lang, split_mode=self.split_mode)
            reference.lang = None
            pc = PeriodClassifier(reference, self._data, policy)
            with AbbreviationReplacer._cache_lock:
                # Publish after full construction; first writer wins (the value is
                # behavior-identical for a given key, so a benign race is harmless).
                pc = cache.setdefault(key, pc)
        self._pc = pc
        return pc

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
        return self._is_likely_sentence_start(text, self._sentence_start_content_offset(text, start))

    def _is_likely_sentence_start(self, text: str, start: int = 0) -> bool:
        """Check if the next non-space character in *text* looks like a sentence start.

        Subclasses (e.g. en_es_zh) can override to recognise additional scripts
        such as CJK ideographs. The supported override signature is
        ``(self, text, start=0)``.
        """
        return _next_nonspace_char_is_upper(text, start)

    def _is_capital_sentence_start_at(self, text: str, start: int) -> bool:
        if start >= len(text):
            return False
        if self._is_likely_sentence_start(text, start):
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
        self._run_post_stages()
        return self.text

    def _run_post_stages(self) -> None:
        """Run the policy's ordered downstream per-period post-stages over ``self.text``.

        Each stage is a ``(replacer) -> None`` callable that mutates ``self.text``;
        the ordered tuple is OWNED by the active ``AbbrPolicy`` (S1 — completing the
        single-pass model: the downstream period decisions that used to be a fixed
        sequence hard-coded in ``replace()`` now flow through the policy, so a
        language reorders/drops/augments them as data, e.g. German's reduced
        pipeline or Kazakh's extra paren pass). A policy that leaves ``post_stages``
        as None inherits ``DEFAULT_POST_STAGES`` (the historical full sequence), so the
        base languages are unchanged. Stages self-gate on the same class flags as
        before (``PROTECT_ALLCAPS_IMPRINT_SUFFIXES``, ``RESTORE_STANDALONE_I_BOUNDARIES``,
        the ``split_mode`` dial), so this is behavior-preserving.
        """
        for stage in self._post_stages():
            stage(self)

    def _post_stages(self) -> tuple:
        """Resolve the active policy's ``post_stages`` (or the default full sequence).

        ``None`` inherits ``DEFAULT_POST_STAGES``; an explicit empty tuple is honored
        as a deliberate "run no post-stages" pipeline.
        """
        from sentencesplit.period_classifier import BASE_POLICY

        policy = self.ABBR_POLICY if self.ABBR_POLICY is not None else BASE_POLICY
        return DEFAULT_POST_STAGES if policy.post_stages is None else policy.post_stages

    def _restore_uppercase_initialism_boundaries(self) -> str:
        """Restore a sentence-boundary period after an all-uppercase 3+ part initialism.

        An all-uppercase multi-period abbreviation ("S∯A∯T∯", "E∯S∯T∯") followed by a
        space and an uppercase letter is ambiguous between a surname/initialism
        reading and a real boundary; split-mode resolves it. Only an uppercase
        lookbehind is matched so lowercase abbreviations like "a.k.a." keep their
        non-boundary separator. Reads the pre-substitution text (``restore_source``)
        for the follower/left-context checks so the decision is not perturbed by its
        own rewrites.
        """
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

        return _UPPERCASE_INITIALISM_BOUNDARY_RE.sub(restore_uppercase_initialism_boundary, self.text)

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
        initialism_key = ".".join(parts).lower()
        max_words = max((len(phrase) - 1 for phrase in self.ALWAYS_JOIN_TWO_LETTER_INITIALISM_PHRASES), default=0)
        followers = self._next_normalized_words(content_offset, max_words)
        for word_count in range(1, len(followers) + 1):
            if (initialism_key, *followers[:word_count]) in self.ALWAYS_JOIN_TWO_LETTER_INITIALISM_PHRASES:
                return True
        return False

    @staticmethod
    def _preceding_token_is_title_prefix(text: str, start: int, title_abbreviations: frozenset[str]) -> bool:
        """Whether the multi-period abbr ending its name-title prefix at *start*.

        A multi-period title/degree abbreviation acts as a *prefix* of a personal
        name ("Ph.D. Smith", "Dr. Ph.D. Smith") when it opens the sentence/line or
        is itself preceded only by another protected *personal-title* abbreviation.
        Walk left over whitespace: a string/line start (or only whitespace back to a
        newline) qualifies. Landing on a protected abbreviation separator ('∯')
        qualifies ONLY when that preceding token is itself a personal title in
        *title_abbreviations* ("Dr∯ ") — an unrelated protected prepositive ("Mt∯ ",
        "v∯ ") does not, since it is not a title and the degree token begins a new
        sentence. Landing on an ordinary word ("earned a Ph.D.", "his Ph.D.") does
        not qualify either.
        """
        i = start
        while i > 0 and text[i - 1].isspace():
            if text[i - 1] in "\r\n":
                return True
            i -= 1
        if i == 0:
            return True
        if text[i - 1] != "∯":
            return False
        # The preceding token is a protected abbreviation: it only chains as a
        # title prefix when it is itself a personal title/honorific, not an
        # unrelated geographic/legal prepositive. Extract that token (letters plus
        # its own protected separators) and normalize to the bare lowercase form.
        k = i
        while k > 0 and (text[k - 1].isalnum() or text[k - 1] in ".∯"):
            k -= 1
        token = text[k:i].replace("∯", "").replace(".", "").lower()
        return token in title_abbreviations

    def _is_titled_name_prefix(self, parts: list[str], start: int) -> bool:
        """True if a degree/title abbr precedes a surname ("Ph.D. Smith").

        Restricted to *mixed* abbreviations carrying a multi-letter part with a
        lowercase letter (the "Ph" in "Ph.D."): pure all-caps initialisms
        ("A.S.E. Ackermann", "M.B.A.") deliberately follow the uppercase-initialism
        split dial instead. The caller has already confirmed a capitalized
        follower; this adds the structural left-context check so only a
        name-title prefix keeps its final period non-terminal.
        """
        if not any(len(part) > 1 and not part.isupper() for part in parts):
            return False
        # Read the policy via ``self.`` so a per-language ``AbbreviationReplacer``
        # subclass that sets its own ``NAME_TITLE_PREFIX_ABBREVIATIONS`` overrides
        # the inherited English-honorific default (see the attribute's docstring).
        return self._preceding_token_is_title_prefix(self.text, start, self.NAME_TITLE_PREFIX_ABBREVIATIONS)

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
            likely_start = self._is_likely_sentence_start(self.text, content_offset)
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
            abbreviation_key = matched[:-1].lower()
            listed_sentence_boundary = abbreviation_key in self.SENTENCE_BOUNDARY_ABBREVIATIONS
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
            # A degree/title abbreviation that opens the name ("Ph.D. Smith",
            # "Dr. Ph.D. Smith") prefixes a surname, so its final period is a
            # name-internal separator, not a boundary — even before a capital.
            # Restricted to the title-prefix position so a trailing degree
            # ("She earned a Ph.D. Smith advised her.") still splits.
            titled_name_prefix = not self._leans_split and likely_start and self._is_titled_name_prefix(parts, match.start())
            if self._leans_join:
                protect_final_period = True
            elif has_always_joined_follower:
                protect_final_period = True
            elif titled_name_prefix:
                protect_final_period = True
            elif not is_ampm and (((split_candidate or listed_sentence_boundary) and likely_start) or capital_boundary):
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

    def search_for_abbreviations_in_string(self, text: str) -> str:
        return self._period_classifier().rewrite(text)
