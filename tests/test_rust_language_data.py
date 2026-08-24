from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sentencesplit.languages import _LANGUAGE_MODULES

ROOT = Path(__file__).parents[1]
DATA_DIR = ROOT / "data" / "lang"


def test_extractor_covers_every_built_in_language() -> None:
    files = {path.stem for path in DATA_DIR.glob("*.json")}
    assert files == set(_LANGUAGE_MODULES)


@pytest.mark.parametrize("code", sorted(_LANGUAGE_MODULES))
def test_extracted_data_has_required_shape(code: str) -> None:
    payload = json.loads((DATA_DIR / f"{code}.json").read_text())
    assert payload["code"] == code == payload["iso_code"]
    assert payload["punctuations"]
    assert isinstance(payload["latin_uppercase_resplit"], bool)
    assert payload["abbreviations"]
    for key in (
        "sentence_boundary_regex",
        "quotation_end_regex",
        "split_quotation_regex",
        "parens_dq_regex",
        "continuous_punct_regex",
        "numbered_ref_regex",
        "double_punct_regex",
        "sub_symbols",
    ):
        assert payload[key] is not None


def test_generated_data_is_stable() -> None:
    before = {(path.name, path.read_bytes()) for path in DATA_DIR.glob("*.json")}
    subprocess.run([sys.executable, str(ROOT / "tools" / "dump_language_data.py"), str(DATA_DIR)], check=True)
    after = {(path.name, path.read_bytes()) for path in DATA_DIR.glob("*.json")}
    assert before == after
