# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from itertools import product

# Internal placeholder ("sentinel") characters the pipeline uses to protect
# punctuation from splitting. They are ordinary printable codepoints, so if a
# user's input already contains one, processing must escape and restore it
# instead of treating it as internal state.
RESERVED_SENTINELS = "∯♬♭☉☇☈☄☊☋☌☍ȸȹƪ♟♝☏∮♨☝"
RESERVED_SENTINEL_SET = frozenset(RESERVED_SENTINELS)

# Private-use codepoints (BMP + both supplementary planes) used as escape
# targets. Targets are chosen per call from this pool to be absent from the
# input. If adversarial input occupies every single private-use character, the
# escape target grows into a delimited private-use string token.
PRIVATE_USE_RANGES = ((0xE000, 0xF8FF), (0xF0000, 0xFFFFD), (0x100000, 0x10FFFD))
NONCHARACTER_DELIMITER_RANGES = ((0xFDD0, 0xFDEF),) + tuple(
    (plane + 0xFFFE, plane + 0xFFFF) for plane in range(0, 0x110000, 0x10000)
)
MAX_NONCHARACTER_DELIMITER_INDEX_BYTES = 32 * 1024 * 1024


def iter_private_use_chars(private_use_ranges=PRIVATE_USE_RANGES):
    for lo, hi in private_use_ranges:
        for cp in range(lo, hi + 1):
            yield chr(cp)


def iter_delimited_private_use_tokens(body_len: int, delimiter: str, private_use_ranges=PRIVATE_USE_RANGES):
    alphabet = tuple(iter_private_use_chars(private_use_ranges))
    if not alphabet:
        return
    for chars in product(alphabet, repeat=body_len):
        yield delimiter + "".join(chars) + delimiter


def iter_noncharacter_delimiters(noncharacter_delimiter_ranges=NONCHARACTER_DELIMITER_RANGES):
    for lo, hi in noncharacter_delimiter_ranges:
        for cp in range(lo, hi + 1):
            yield chr(cp)


def decode_noncharacter_delimiter(code: int, width: int, alphabet: tuple[str, ...]) -> str:
    base = len(alphabet)
    chars = [""] * width
    for pos in range(width - 1, -1, -1):
        code, idx = divmod(code, base)
        chars[pos] = alphabet[idx]
    return "".join(chars)


def absent_noncharacter_delimiter_with_missing_follower(
    text: str,
    context_code: int,
    context_width: int,
    alphabet: tuple[str, ...],
    alphabet_index: dict[str, int],
) -> str | None:
    base = len(alphabet)
    high_order = base ** (context_width - 1)
    code = 0
    run_len = 0
    followers = 0

    for index, ch in enumerate(text):
        char_index = alphabet_index.get(ch)
        if char_index is None:
            code = 0
            run_len = 0
            continue
        if run_len < context_width:
            code = (code * base) + char_index
            run_len += 1
            if run_len < context_width:
                continue
        else:
            code = ((code % high_order) * base) + char_index

        if code != context_code or index + 1 == len(text):
            continue
        follower_index = alphabet_index.get(text[index + 1])
        if follower_index is not None:
            followers |= 1 << follower_index

    for follower_index, follower in enumerate(alphabet):
        if not followers & (1 << follower_index):
            return decode_noncharacter_delimiter(context_code, context_width, alphabet) + follower
    return None


def scan_noncharacter_delimiter_counts(
    text: str,
    width: int,
    base: int,
    total_candidates: int,
    alphabet_index: dict[str, int],
) -> tuple[bytearray, int]:
    counts = bytearray(total_candidates)
    seen = 0
    code = 0
    run_len = 0
    high_order = base ** (width - 1)

    for ch in text:
        idx = alphabet_index.get(ch)
        if idx is None:
            code = 0
            run_len = 0
            continue
        if run_len < width:
            code = (code * base) + idx
            run_len += 1
            if run_len < width:
                continue
        else:
            code = ((code % high_order) * base) + idx

        if counts[code] == 0:
            seen += 1
        if counts[code] < base:
            counts[code] += 1

    return counts, seen


def absent_noncharacter_delimiter(
    text: str,
    noncharacter_delimiter_ranges=NONCHARACTER_DELIMITER_RANGES,
    max_index_bytes: int = MAX_NONCHARACTER_DELIMITER_INDEX_BYTES,
) -> str:
    """Return a noncharacter delimiter token absent from *text* in linear time."""
    alphabet = tuple(iter_noncharacter_delimiters(noncharacter_delimiter_ranges))
    if not alphabet:
        raise ValueError("At least one noncharacter delimiter token is required")

    alphabet_index = {char: idx for idx, char in enumerate(alphabet)}
    base = len(alphabet)
    width = 1

    while True:
        total_candidates = base**width
        if total_candidates > max_index_bytes:
            raise ValueError("Unable to choose a bounded noncharacter delimiter token")

        counts, seen = scan_noncharacter_delimiter_counts(text, width, base, total_candidates, alphabet_index)

        if seen < total_candidates:
            for missing_code, count in enumerate(counts):
                if count == 0:
                    return decode_noncharacter_delimiter(missing_code, width, alphabet)

        for context_code, count in enumerate(counts):
            if count >= base:
                continue
            delimiter = absent_noncharacter_delimiter_with_missing_follower(
                text, context_code, width, alphabet, alphabet_index
            )
            if delimiter is not None:
                return delimiter

        width += 1


def build_sentinel_escape_tables(
    text: str,
    *,
    reserved_sentinels: str = RESERVED_SENTINELS,
    private_use_ranges=PRIVATE_USE_RANGES,
    noncharacter_delimiter_ranges=NONCHARACTER_DELIMITER_RANGES,
    max_index_bytes: int = MAX_NONCHARACTER_DELIMITER_INDEX_BYTES,
) -> tuple[dict[int, str], dict[str, str], re.Pattern[str]]:
    """Return escape/restore tables for reserved sentinels in *text*.

    The escape values are private-use tokens that do not occur in the input.
    Single private-use characters are used for normal inputs; if an adversarial
    input exhausts the single-character pool, longer private-use token bodies
    are wrapped in an absent delimiter. The delimiter prevents restore matches
    from starting inside neighboring original private-use text.

    Returns ``(escape, restore, restore_re)`` where ``escape`` maps codepoints to
    tokens for ``str.translate``, ``restore`` maps each token back to its
    sentinel, and ``restore_re`` is a compiled alternation that restores every
    token in a single left-to-right pass. The atomic restore is required for
    correctness: multi-character tokens are not prefix-free, so a sequential
    per-token ``str.replace`` could match a window straddling two adjacent
    escaped sentinels and corrupt the round-trip.
    """
    tokens = []
    occupied = set(text)
    for token in iter_private_use_chars(private_use_ranges):
        if token not in occupied:
            tokens.append(token)
            if len(tokens) == len(reserved_sentinels):
                break
    if len(tokens) < len(reserved_sentinels):
        delimiter = absent_noncharacter_delimiter(
            text,
            noncharacter_delimiter_ranges=noncharacter_delimiter_ranges,
            max_index_bytes=max_index_bytes,
        )
        body_len = 1
        while len(tokens) < len(reserved_sentinels):
            saw_candidate = False
            for token in iter_delimited_private_use_tokens(body_len, delimiter, private_use_ranges):
                saw_candidate = True
                tokens.append(token)
                if len(tokens) == len(reserved_sentinels):
                    break
            if not saw_candidate:
                raise ValueError("At least one private-use escape codepoint is required")
            body_len += 1
    escape = {ord(ch): token for ch, token in zip(reserved_sentinels, tokens, strict=True)}
    restore = {token: ch for ch, token in zip(reserved_sentinels, tokens, strict=True)}
    restore_re = re.compile("|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True)))
    return escape, restore, restore_re
