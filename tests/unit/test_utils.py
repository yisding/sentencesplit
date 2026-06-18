# -*- coding: utf-8 -*-

from sentencesplit.utils import _next_nonspace_char, _next_nonspace_char_is_non_ascii_upper, _next_nonspace_char_is_upper


class NoSliceStr(str):
    def __getitem__(self, key):
        if isinstance(key, slice):
            raise AssertionError("_next_nonspace_char should scan by index instead of slicing")
        return super().__getitem__(key)


def test_next_nonspace_char_uses_start_offset_without_slicing():
    text = NoSliceStr("prefix.   Éclair")

    assert _next_nonspace_char(text, 7) == "É"
    assert _next_nonspace_char_is_upper(text, 7)
    assert _next_nonspace_char_is_non_ascii_upper(text, 7)
