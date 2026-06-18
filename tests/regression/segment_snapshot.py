"""Deterministic 26-language ``segment()`` regression snapshot.

Builds a frozen baseline of the live engine's ``segment()`` output across every
registered language code, using each language's *own* Golden-Rule inputs
(extracted straight from ``tests/lang/test_<lang>.py``) plus a short, hand-fixed
script-appropriate sample per language. ``build_snapshot()`` re-runs the engine
and ``diff()`` compares it against the saved JSON
(``tests/regression/segment_snapshot.json``) to surface every changed
``(lang, input)`` pair so it can be adjudicated as an intended correctness change
or caught as a regression.

Determinism contract
--------------------
* Golden-Rule inputs are extracted by **AST-parsing** the test modules (no import,
  no fixtures, no collection ordering) so the set is stable and side-effect-free.
* Every code is segmented with ``Segmenter(language=code, clean=False)`` — the
  same construction the default per-language test fixtures use.
* Inputs are de-duplicated per language preserving first-seen order; languages are
  emitted in sorted code order. The JSON is written with ``sort_keys`` so the file
  bytes are reproducible.

The snapshot key is the string ``"<lang>\\x1f<input>"`` (a unit-separator joins the
language code and the raw input) so the JSON stays a flat ``{str: [str, ...]}``
object — JSON has no tuple keys.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from sentencesplit.languages import LANGUAGE_CODES
from sentencesplit.segmenter import Segmenter

# --------------------------------------------------------------------------- paths
_THIS_DIR = Path(__file__).resolve().parent
_LANG_TEST_DIR = _THIS_DIR.parent / "lang"
SNAPSHOT_PATH = _THIS_DIR / "segment_snapshot.json"

# Unit separator: cannot appear in any of our inputs, keeps the key reversible.
_KEY_SEP = "\x1f"

# Map each language test module (stem) to the language code(s) whose Golden-Rule
# inputs it carries. A few modules are explicit because their fixture/param names
# do not follow the ``<code>_default_fixture`` convention.
_TEST_MODULE_CODE = {
    "test_amharic": "am",
    "test_arabic": "ar",
    "test_armenian": "hy",
    "test_bulgarian": "bg",
    "test_burmese": "my",
    "test_chinese": "zh",
    "test_danish": "da",
    "test_deutsch": "de",
    "test_dutch": "nl",
    "test_en_es_zh": "en_es_zh",
    "test_en_legal": "en_legal",
    "test_english": "en",
    "test_english_challenging": "en",
    "test_english_clean": "en",
    "test_french": "fr",
    "test_greek": "el",
    "test_hindi": "hi",
    "test_italian": "it",
    "test_japanese": "ja",
    "test_kazakh": "kk",
    "test_marathi": "mr",
    "test_persian": "fa",
    "test_polish": "pl",
    "test_russian": "ru",
    "test_slovak": "sk",
    "test_spanish": "es",
    "test_tagalog": "tl",
    "test_urdu": "ur",
}

# One short, fixed, script-appropriate sample per code so even languages with a
# tiny Golden-Rule set get exercised on a representative multi-sentence input.
# These are intentionally simple and do not depend on the abbreviation tables.
_SCRIPT_SAMPLES = {
    "am": "ሰላም ለዓለም። ስሜ ዮናስ ነው።",
    "ar": "مرحبا بالعالم. اسمي يوناس.",
    "bg": "Здравей, свят. Казвам се Йонас.",
    "da": "Hej verden. Mit navn er Jonas.",
    "de": "Hallo Welt. Mein Name ist Jonas.",
    "el": "Γεια σου κόσμε. Το όνομά μου είναι Γιόνας.",
    "en": "Hello world. My name is Jonas.",
    "en_es_zh": "Hello world. Hola mundo. 你好世界。我叫约纳斯。",
    "en_legal": "See Roe v. Wade, 410 U.S. 113. The court so held.",
    "es": "Hola mundo. Me llamo Jonás.",
    "fa": "سلام دنیا. نام من یوناس است.",
    "fr": "Bonjour le monde. Je m'appelle Jonas.",
    "hi": "नमस्ते दुनिया। मेरा नाम योनास है।",
    "hy": "Բարեւ աշխարհ։ Իմ անունը Յոնաս է։",
    "it": "Ciao mondo. Mi chiamo Jonas.",
    "ja": "こんにちは世界。私の名前はヨナスです。",
    "kk": "Сәлем әлем. Менің атым Йонас. Ол обл. орталығында тұрады.",
    "mr": "नमस्कार जग। माझे नाव योनास आहे।",
    "my": "မင်္ဂလာပါကမ္ဘာ။ ကျွန်တော့်နာမည် ယိုနပ်စ်ဖြစ်သည်။",
    "nl": "Hallo wereld. Mijn naam is Jonas.",
    "pl": "Witaj świecie. Nazywam się Jonas. Mam np. psa, kota itd.",
    "ru": "Привет, мир. Меня зовут Йонас.",
    "sk": "Ahoj svet. Volám sa Jonas.",
    "tl": "Kumusta mundo. Ang pangalan ko ay Jonas.",
    "ur": "ہیلو دنیا۔ میرا نام یوناس ہے۔",
    "zh": "你好世界。我叫约纳斯。",
}


# --------------------------------------------------------------------- extraction
def _string_const(node: ast.AST) -> str | None:
    """Return the value of a string-constant AST node, else ``None``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _input_from_case(node: ast.AST) -> str | None:
    """Extract the input string (first positional element) from one parametrize case.

    Handles bare tuples ``("text", [...])`` and ``pytest.param("text", [...], ...)``.
    Returns ``None`` for cases whose first element is not a plain string literal
    (e.g. computed inputs), which are skipped — the snapshot only needs literal
    Golden-Rule inputs.
    """
    if isinstance(node, ast.Call):
        # pytest.param(text, expected, marks=..., id=...)
        if node.args:
            return _string_const(node.args[0])
        return None
    if isinstance(node, (ast.Tuple, ast.List)) and node.elts:
        return _string_const(node.elts[0])
    return None


def _is_text_parametrize(node: ast.AST) -> bool:
    """True iff *node* is a ``parametrize(...)`` call whose first arg names ``text``."""
    if not isinstance(node, ast.Call) or len(node.args) < 2:
        return False
    func = node.func
    attr = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else "")
    if attr != "parametrize":
        return False
    argnames = _string_const(node.args[0])
    return bool(argnames) and argnames.split(",")[0].strip() == "text"


def _module_list_assigns(tree: ast.Module) -> dict[str, ast.List]:
    """Map every module-level ``NAME = [...]`` to its list AST node."""
    assigns: dict[str, ast.List] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.List):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    assigns[target.id] = stmt.value
    return assigns


def _referenced_case_lists(tree: ast.Module, list_assigns: dict[str, ast.List]) -> list[ast.List]:
    """Return the case-list AST nodes used by ``parametrize("text,...", ...)``, in order."""
    referenced: list[ast.List] = []
    seen: set[int] = set()
    for node in ast.walk(tree):
        if not _is_text_parametrize(node):
            continue
        argvalues = node.args[1]
        if isinstance(argvalues, ast.Name):
            argvalues = list_assigns.get(argvalues.id)
        if isinstance(argvalues, ast.List) and id(argvalues) not in seen:
            seen.add(id(argvalues))
            referenced.append(argvalues)
    return referenced


def _golden_inputs_for_module(module_path: Path) -> list[str]:
    """AST-parse one ``test_*.py`` and return all Golden-Rule input strings.

    Finds every ``@pytest.mark.parametrize("text,...", NAME)`` decorator, resolves
    ``NAME`` to a module-level list assignment (or accepts an inline list literal),
    and pulls the first element from each case. Order: decorator appearance, then
    case order within each referenced list. Duplicates are removed by the caller.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    list_assigns = _module_list_assigns(tree)
    inputs: list[str] = []
    for list_node in _referenced_case_lists(tree, list_assigns):
        for case in list_node.elts:
            text = _input_from_case(case)
            if text is not None:
                inputs.append(text)
    return inputs


def golden_inputs_by_code() -> dict[str, list[str]]:
    """Collect Golden-Rule inputs per language code (deduped, first-seen order)."""
    by_code: dict[str, list[str]] = {code: [] for code in LANGUAGE_CODES}
    for stem, code in _TEST_MODULE_CODE.items():
        path = _LANG_TEST_DIR / f"{stem}.py"
        if not path.exists():
            continue
        by_code.setdefault(code, [])
        by_code[code].extend(_golden_inputs_for_module(path))
    return by_code


def corpus_by_code() -> dict[str, list[str]]:
    """Final per-code input corpus: script sample first, then Golden-Rule inputs.

    De-duplicated preserving first-seen order so the snapshot is stable.
    """
    golden = golden_inputs_by_code()
    corpus: dict[str, list[str]] = {}
    for code in sorted(LANGUAGE_CODES):
        ordered: list[str] = []
        sample = _SCRIPT_SAMPLES.get(code)
        if sample:
            ordered.append(sample)
        ordered.extend(golden.get(code, []))
        seen: set[str] = set()
        deduped: list[str] = []
        for text in ordered:
            if text not in seen:
                seen.add(text)
                deduped.append(text)
        corpus[code] = deduped
    return corpus


# ------------------------------------------------------------------ build / diff
def _segment(code: str, text: str) -> list[str]:
    return list(Segmenter(language=code, clean=False).segment(text))


def build_snapshot() -> dict[str, list[str]]:
    """Run the live engine over the full corpus; return ``{key: [sentences]}``."""
    snapshot: dict[str, list[str]] = {}
    for code, inputs in corpus_by_code().items():
        for text in inputs:
            snapshot[f"{code}{_KEY_SEP}{text}"] = _segment(code, text)
    return snapshot


def save_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, list[str]]:
    snapshot = build_snapshot()
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return snapshot


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def diff(path: Path = SNAPSHOT_PATH) -> list[dict[str, object]]:
    """Compare the live engine to the saved snapshot.

    Returns one record per changed/added/removed ``(lang, input)`` key::

        {"lang", "input", "kind": "changed|added|removed", "baseline", "live"}

    An empty list means the live engine reproduces the saved baseline exactly.
    """
    baseline = load_snapshot(path)
    live = build_snapshot()
    changes: list[dict[str, object]] = []
    for key in sorted(set(baseline) | set(live)):
        code, _, text = key.partition(_KEY_SEP)
        base_val = baseline.get(key)
        live_val = live.get(key)
        if key not in live:
            changes.append({"lang": code, "input": text, "kind": "removed", "baseline": base_val, "live": None})
        elif key not in baseline:
            changes.append({"lang": code, "input": text, "kind": "added", "baseline": None, "live": live_val})
        elif base_val != live_val:
            changes.append({"lang": code, "input": text, "kind": "changed", "baseline": base_val, "live": live_val})
    return changes


def _print_diff(records: list[dict[str, object]]) -> None:
    if not records:
        print("snapshot: no diffs (live == baseline)")
        return
    print(f"snapshot: {len(records)} changed (lang,input) keys")
    for rec in records:
        print(f"  [{rec['kind']}] {rec['lang']}: {rec['input']!r}")
        print(f"      baseline={rec['baseline']!r}")
        print(f"      live    ={rec['live']!r}")


def _main(argv: list[str]) -> int:
    """CLI entry point.

    * ``python -m tests.regression.segment_snapshot`` (bare) — diff the live engine
      against the committed baseline and exit non-zero if they differ. A bare
      run is *read-only*: it never rewrites the baseline.
    * ``--diff`` / ``diff`` — explicit alias for the read-only diff above.
    * ``--update`` — regenerate ``segment_snapshot.json`` from the live engine.
      This is the ONLY path that rewrites the baseline; use it deliberately when
      adjudicating an intended behavior change.
    """
    flag = argv[1] if len(argv) > 1 else ""
    if flag == "--update":
        snap = save_snapshot()
        print(f"snapshot: wrote {len(snap)} (lang,input) keys to {SNAPSHOT_PATH}")
        return 0
    if flag in ("", "--diff", "diff"):
        records = diff()
        _print_diff(records)
        return 1 if records else 0
    print(f"snapshot: unknown argument {flag!r}; expected --diff or --update")
    return 2


if __name__ == "__main__":
    import sys

    sys.exit(_main(sys.argv))
