
import pysbd

seg = pysbd.Segmenter(language="en", clean=False)

# Test 1: Number-period merges
tests = [
    ("April 14 merge", "Lincoln attended the play on the evening of April 14. At the last minute, Grant decided to go."),
    (
        "version 2 merge",
        "The Linux kernel is licensed under the GPL, version 2. The GPL requires that anyone who distributes software must share source code.",
    ),
    ("April 14 simple", "It happened on April 14. The next day was different."),
    ("version 2 simple", "This is version 2. The new version is better."),
]

for name, text in tests:
    result = seg.segment(text)
    print(f"\n{name}:")
    for i, s in enumerate(result):
        print(f"  [{i}] {s}")

# Test 2: "white man" merge (case 672)
print("\n\nwhite man merge:")
result = seg.segment(
    "I had never heard this slur used by a more sophisticated Negro, or by any white man. I tried to convey this effect."
)
for i, s in enumerate(result):
    print(f"  [{i}] {s}")

# Test 3: Check if "man" is in abbreviation list
from pysbd.lang.english import English

abbrs = English.Abbreviation.ABBREVIATIONS
man_in_abbrs = "man" in abbrs
print(f"\n'man' in abbreviations: {man_in_abbrs}")
# Check similar words
for a in sorted(abbrs):
    if "man" in a.lower():
        print(f"  Found: {repr(a)}")

# Test 4: Components.) case (592)
print("\n\ncomponents.) merge:")
result = seg.segment(
    "The Internet protocol suite (also called TCP/IP, based on the first two components.) This is a suite of protocols."
)
for i, s in enumerate(result):
    print(f"  [{i}] {s}")

# Test 5: Trace what happens to "version 2." through pipeline
from pysbd.lang.english import English as EnglishLang
from pysbd.processor import Processor

p = Processor("This is version 2. The new version is better.", EnglishLang, char_span=False)
# Manually step through
p.text = p.text.replace("\n", "\r")
from pysbd.lists_item_replacer import ListItemReplacer

li = ListItemReplacer(p.text)
p.text = li.add_line_break()
print(f"\nAfter ListItemReplacer: {repr(p.text)}")
p.replace_abbreviations()
print(f"After abbreviations: {repr(p.text)}")
p.replace_numbers()
print(f"After numbers: {repr(p.text)}")
