#!/usr/bin/env python3
"""Dump built-in language-profile data as the Rust port's shared source of truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sentencesplit.language_profile import LanguageProfile
from sentencesplit.languages import _LANGUAGE_MODULES


def _regex(value: Any) -> str | None:
    return None if value is None else value.pattern


def dump(code: str) -> dict[str, Any]:
    module_name, class_name = _LANGUAGE_MODULES[code]
    language = getattr(__import__(module_name, fromlist=[class_name]), class_name)
    profile = LanguageProfile.from_language(language)
    abbreviation = language.Abbreviation
    sub_symbols = getattr(language.SubSymbolsRules, "SUBS_TABLE", ())
    return {
        "code": code,
        "iso_code": language.iso_code,
        "punctuations": list(profile.punctuations),
        "latin_uppercase_resplit": profile.latin_uppercase_resplit,
        "abbreviations": sorted({entry.strip() for entry in abbreviation.ABBREVIATIONS if entry.strip()}),
        "prepositive_abbreviations": sorted(set(abbreviation.PREPOSITIVE_ABBREVIATIONS)),
        "number_abbreviations": sorted(set(abbreviation.NUMBER_ABBREVIATIONS)),
        "sentence_boundary_regex": _regex(profile.sentence_boundary_re),
        "quotation_end_regex": _regex(profile.quotation_end_re),
        "split_quotation_regex": _regex(profile.split_quotation_re),
        "parens_dq_regex": _regex(profile.parens_dq_re),
        "continuous_punct_regex": _regex(profile.continuous_punct_re),
        "numbered_ref_regex": _regex(profile.numbered_ref_re),
        "double_punct_regex": _regex(profile.double_punct_re),
        "cjk_reporting_clause_regex": _regex(profile.cjk_reporting_clause_re),
        "sub_symbols": [list(pair) for pair in sub_symbols],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=Path("data/lang"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for code in sorted(_LANGUAGE_MODULES):
        payload = dump(code)
        target = args.output / f"{code}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
