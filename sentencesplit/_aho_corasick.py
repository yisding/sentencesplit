# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import deque


class AhoCorasickAutomaton:
    """Pure-Python Aho-Corasick automaton for multi-pattern substring search.

    Thread-safety: an instance is mutated only by ``add_pattern``/``build`` and is
    read-only thereafter. It carries no lock of its own — safe concurrent use
    relies on the owner publishing it only after ``build()`` completes. In this
    package the only instances live inside ``_AbbreviationData``, which is built
    and then stored into ``AbbreviationReplacer._data_cache`` under
    ``_cache_lock``, so every reader's ``search()`` happens-after ``build()``.
    """

    __slots__ = ("goto", "fail", "output", "delta")

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
