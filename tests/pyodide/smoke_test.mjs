// Pyodide smoke test for sentencesplit.
//
// Loads the built pure-Python wheel into a Pyodide (CPython-on-WebAssembly)
// runtime via micropip and exercises the public API, asserting that the library
// imports and segments correctly in the browser/WASM environment. Run by the
// `pyodide-test` CI job; also runnable locally:
//
//     uv build --wheel
//     npm ci
//     node tests/pyodide/smoke_test.mjs dist/sentencesplit-*.whl
//
// Exits non-zero on any failed expectation so CI fails loudly.

import { loadPyodide } from "pyodide";
import { readFileSync } from "node:fs";
import { basename } from "node:path";

const wheelPath = process.argv[2];
if (!wheelPath) {
  console.error("usage: node smoke_test.mjs <path-to-sentencesplit-wheel>");
  process.exit(2);
}

function assertDeepEqual(actual, expected, label) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) {
    console.error(`FAIL ${label}\n  expected: ${e}\n  actual:   ${a}`);
    process.exit(1);
  }
  console.log(`ok   ${label}`);
}

const pyodide = await loadPyodide();
console.log(`pyodide ${pyodide.version} | python ${pyodide.runPython("import sys; sys.version.split()[0]")}`);

await pyodide.loadPackage("micropip");
const micropip = pyodide.pyimport("micropip");

// Mount the local wheel into the Emscripten in-memory FS and install from it.
const wheelName = basename(wheelPath);
pyodide.FS.writeFile(`/${wheelName}`, readFileSync(wheelPath));
await micropip.install(`emfs:/${wheelName}`);

const result = pyodide.runPython(`
import json
import sentencesplit

en = sentencesplit.Segmenter(language="en")
en_clean = sentencesplit.Segmenter(language="en", clean=True)
zh = sentencesplit.Segmenter(language="zh")

json.dumps({
    "abbrev": en.segment("My name is Jonas E. Smith. Please turn to p. 55."),
    # Guards the TableOfContentsRule cleaner path (a possessive-quantifier
    # regression that surfaced on alternative runtimes).
    "clean_toc": en_clean.segment("Send it to P.O. box 6554"),
    "cjk": zh.segment("這是第一句。這是第二句！"),
    "n_langs": len(sentencesplit.list_languages()),
    "version": sentencesplit.__version__,
})
`);

const data = JSON.parse(result);
console.log("segmentation result:", JSON.stringify(data));

assertDeepEqual(
  data.abbrev,
  ["My name is Jonas E. Smith. ", "Please turn to p. 55."],
  "English abbreviation handling",
);
assertDeepEqual(data.clean_toc, ["Send it to P.O. box 6554"], "clean=True preserves trailing number");
assertDeepEqual(data.cjk, ["這是第一句。", "這是第二句！"], "CJK sentence-ending punctuation");

if (data.n_langs < 24) {
  console.error(`FAIL expected >= 24 languages, got ${data.n_langs}`);
  process.exit(1);
}
console.log(`ok   ${data.n_langs} languages registered`);

if (!data.version) {
  console.error("FAIL __version__ did not resolve under Pyodide");
  process.exit(1);
}
console.log(`ok   __version__ resolved to ${data.version}`);

console.log("\nPyodide smoke test passed.");
