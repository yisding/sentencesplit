#!/usr/bin/env python3
"""
Comprehensive analysis of 60 disagreements between pySBD and Punkt sentence
boundary detectors. Assigns definitive verdicts to each case based on
heuristic rules for detecting common sentence-splitting errors.

Output: per-case verdicts with reasoning, and a final tally/accuracy assessment.
"""

import json
import re
from collections import Counter
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESULTS_FILE = "comparison_results.json"

# Header pattern: == Title == or === Title === etc.
HEADER_RE = re.compile(r"^={2,}\s.*={2,}$")

# Abbreviation patterns that should NOT trigger a sentence break
ABBREVIATIONS = {
    # Titles
    "Mr.",
    "Mrs.",
    "Ms.",
    "Dr.",
    "Prof.",
    "Rev.",
    "Sr.",
    "Jr.",
    "Gen.",
    "Gov.",
    "Sgt.",
    "Cpl.",
    "Pvt.",
    "Capt.",
    "Lt.",
    "Col.",
    "Cmdr.",
    "Adm.",
    "Maj.",
    "Supt.",
    "Msgr.",
    # Academic / professional
    "Ph.D.",
    "M.D.",
    "B.A.",
    "M.A.",
    "D.Phil.",
    "LL.B.",
    "LL.M.",
    # Common abbreviations
    "etc.",
    "e.g.",
    "i.e.",
    "vs.",
    "al.",
    "approx.",
    "dept.",
    "est.",
    "govt.",
    "inc.",
    "corp.",
    "assn.",
    "bros.",
    # Initials / multi-part abbreviations
    "U.S.",
    "U.S.A.",
    "U.K.",
    "U.N.",
    "E.U.",
    "W.",
    "E.",
    "B.",
    "D.",
    "C.",
    "F.",
    "G.",
    "H.",
    "I.",
    "J.",
    "K.",
    "L.",
    "M.",
    "N.",
    "O.",
    "P.",
    "Q.",
    "R.",
    "S.",
    "T.",
    "V.",
    "X.",
    "Y.",
    "Z.",
    # Geographic / institution abbreviations
    "St.",
    "Mt.",
    "Ft.",
    "Ave.",
    "Blvd.",
    # Other
    "pp.",
    "vol.",
    "no.",
    "op.",
    "fig.",
    "ch.",
    "sec.",
}

# Specific multi-letter abbreviation sequences (W. E. B., D.C., etc.)
MULTI_ABBREV_RE = re.compile(
    r"(?:[A-Z]\.(?:\s+)?){2,}"  # e.g. W. E. B. or U.S.A.
)

# Known abbreviation patterns that appear before false Punkt splits
# NOTE: Do NOT use re.IGNORECASE here — [A-Z] must only match uppercase
# to avoid false positives on any sentence-final word like "bridges."
ABBREV_BEFORE_SPLIT_RE = re.compile(
    r"(?:"
    r"(?<!\w)[A-Z]\.\s*$"  # single initial at end: "W." "B." (with word boundary)
    r"|[Ee]\.g\.\s*$"
    r"|[Ii]\.e\.\s*$"
    r"|et\s+al\.\s*$"
    r"|U\.S\.(?:A\.)?\s*$"
    r"|D\.C\.\s*$"
    r"|Dr\.\s*$"
    r"|Mr\.\s*$"
    r"|Mrs\.\s*$"
    r"|Ms\.\s*$"
    r"|Prof\.\s*$"
    r"|Gen\.\s*$"
    r"|Gov\.\s*$"
    r"|Jr\.\s*$"
    r"|Sr\.\s*$"
    r"|Inc\.\s*$"
    r"|Corp\.\s*$"
    r"|[Vv]s\.\s*$"
    r"|approx\.\s*$"
    r"|pp\.\s*$"
    r"|[Vv]ol\.\s*$"
    r")"
)

# Orphan fragment: sentence that is only punctuation or extremely short garbage
ORPHAN_RE = re.compile(r"^[\.\!\?\s\-–—…]+$")

# Very short fragments that aren't real sentences (excluding known short forms)
MIN_REAL_SENTENCE_LEN = 6  # anything shorter is suspicious


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def strip_headers(sentences: List[str]) -> List[str]:
    """Remove section header lines (=== Title ===) from sentence list.
    Also strip header prefixes from sentences where Punkt merged a header
    with the first sentence (e.g., '=== Title ===\\nFirst sentence...')."""
    result = []
    for s in sentences:
        stripped = s.strip()
        if HEADER_RE.match(stripped):
            continue
        # Check if the sentence starts with a merged header (header + newline + text)
        m = re.match(r"^(={2,}\s.*?={2,})\s*\n\s*", s)
        if m:
            # Strip the header prefix, keep the rest
            remainder = s[m.end() :]
            if remainder.strip():
                result.append(remainder)
            continue
        result.append(s)
    return result


def is_header(s: str) -> bool:
    return bool(HEADER_RE.match(s.strip()))


def is_orphan(s: str) -> bool:
    """Check if a sentence is an orphan fragment (just punctuation or dots)."""
    stripped = s.strip()
    if ORPHAN_RE.match(stripped):
        return True
    return False


def is_very_short_fragment(s: str) -> bool:
    """Check if a sentence is suspiciously short and not a real sentence."""
    stripped = s.strip()
    # Remove quotes and punctuation to check core content
    core = re.sub(r"[\"\'\u2018\u2019\u201c\u201d\.\!\?\,\;\:\(\)\[\]\{\}\u2026\u2013\u2014\-]", "", stripped).strip()
    if len(core) < MIN_REAL_SENTENCE_LEN and len(stripped) < 20:
        # Exception: intentional short sentences like "I see." are fine
        # But fragments like "." or "pp." or "(BDFL)" or "v-vi." are not
        if not re.match(r"^[A-Z].*[\.!\?]$", stripped):
            return True
    return False


def count_orphans(sentences: List[str]) -> int:
    """Count orphan/garbage fragments in a sentence list."""
    return sum(1 for s in sentences if is_orphan(s) or is_very_short_fragment(s))


def has_dotnet_split(sentences: List[str]) -> bool:
    """Check if pySBD incorrectly split '.NET' across sentence boundaries."""
    for i in range(len(sentences) - 1):
        current = sentences[i].rstrip()
        next_s = sentences[i + 1].lstrip()
        # pySBD splits "the .NET" into "the ." and "NET ..."
        if current.endswith(".") and next_s.startswith("NET"):
            return True
    return False


def has_bdfl_style_split(sentences: List[str]) -> bool:
    """Check if pySBD incorrectly splits at parenthetical like (BDFL)."""
    for i in range(len(sentences) - 1):
        current = sentences[i].rstrip()
        next_s = sentences[i + 1].lstrip()
        # pySBD splits before "(BDFL)" creating a break mid-sentence
        if next_s.startswith("(") and not current.endswith("."):
            # The next sentence starts with a parenthetical that continues
            # the thought from the previous sentence
            if re.match(r"^\([A-Z]+\)", next_s):
                return True
    return False


def check_quote_balance(s: str) -> int:
    """
    Return the quote nesting depth at the end of the string.
    Tracks: " " " (straight and curly double quotes).
    Returns > 0 if we are still inside a quote at string end.
    """
    depth = 0
    # Track opening and closing curly quotes
    for ch in s:
        if ch in '"\u201c':  # opening quote or straight quote
            if ch == '"':
                # Straight quote: toggle
                if depth > 0:
                    depth -= 1
                else:
                    depth += 1
            else:
                depth += 1
        elif ch == "\u201d":  # closing curly quote
            depth = max(0, depth - 1)
    return depth


def smarter_quote_check(sent: str, next_sent: Optional[str]) -> bool:
    """
    Check if a sentence ends mid-quote (the quote was opened but not closed),
    and the next sentence contains the closing quote.
    """
    if next_sent is None:
        return False

    # Count quotes in the current sentence
    open_q = sent.count("\u201c") + sent.count("\u201e")  # left double quotes
    close_q = sent.count("\u201d")
    straight = sent.count('"')

    # For straight quotes, try to figure out open vs close by position
    if straight > 0 and open_q == 0 and close_q == 0:
        # All straight quotes - count them
        if straight % 2 == 1:
            # Odd number of straight quotes means unclosed
            # Check if next sentence has the closing quote
            next_straight = next_sent.count('"')
            if next_straight > 0:
                return True

    # For curly quotes
    if open_q > close_q:
        # Unclosed opening quote
        next_close = next_sent.count("\u201d") + next_sent.count('"')
        if next_close > 0:
            return True

    return False


def check_punkt_splits_inside_quote(punkt_sents: List[str], pysbd_sents: List[str]) -> bool:
    """
    Check if Punkt splits a quoted passage that pySBD keeps together.
    Returns True if Punkt appears to incorrectly break inside a quote.
    """
    for i in range(len(punkt_sents) - 1):
        if smarter_quote_check(punkt_sents[i], punkt_sents[i + 1]):
            # Verify pySBD keeps this together by checking if pySBD has fewer
            # sentences in the corresponding region, or the combined text
            # appears as a single pySBD sentence
            combined = punkt_sents[i] + " " + punkt_sents[i + 1]
            # Normalize whitespace for comparison
            combined_norm = " ".join(combined.split())
            for ps in pysbd_sents:
                ps_norm = " ".join(ps.split())
                if combined_norm == ps_norm or combined_norm in ps_norm:
                    return True
    return False


def check_punkt_splits_at_abbreviation(punkt_sents: List[str], pysbd_sents: List[str]) -> bool:
    """
    Check if Punkt incorrectly splits at an abbreviation that pySBD handles.
    """
    for i in range(len(punkt_sents) - 1):
        sent = punkt_sents[i].rstrip()
        next_s = punkt_sents[i + 1].lstrip()

        # Check if the sentence ends with a known abbreviation pattern
        if ABBREV_BEFORE_SPLIT_RE.search(sent):
            # Verify pySBD keeps this together
            combined = punkt_sents[i].rstrip() + " " + punkt_sents[i + 1].lstrip()
            combined_norm = " ".join(combined.split())
            for ps in pysbd_sents:
                ps_norm = " ".join(ps.split())
                if combined_norm == ps_norm or ps_norm.startswith(combined_norm[:80]):
                    return True

        # Check for multi-initial patterns like "W. E. B." split
        if MULTI_ABBREV_RE.search(sent[-10:] if len(sent) >= 10 else sent):
            # The abbreviation ends the sentence - this might be a false split
            if next_s and next_s[0].isupper():
                combined = punkt_sents[i].rstrip() + " " + punkt_sents[i + 1].lstrip()
                combined_norm = " ".join(combined.split())
                for ps in pysbd_sents:
                    ps_norm = " ".join(ps.split())
                    if combined_norm == ps_norm:
                        return True

    return False


def check_punkt_splits_inside_parens(punkt_sents: List[str], pysbd_sents: List[str]) -> bool:
    """
    Check if Punkt splits inside parenthesized text that pySBD keeps together.
    """
    for i in range(len(punkt_sents) - 1):
        sent = punkt_sents[i]
        # Count unbalanced parentheses
        open_parens = sent.count("(") - sent.count(")")
        if open_parens > 0:
            # This sentence has unclosed parentheses - Punkt may have split inside
            # Check if next sentence closes the parenthesis
            next_s = punkt_sents[i + 1]
            close_parens = next_s.count(")") - next_s.count("(")
            if close_parens > 0:
                # Verify pySBD keeps this together
                combined = sent.rstrip() + " " + next_s.lstrip()
                combined_norm = " ".join(combined.split())
                for ps in pysbd_sents:
                    ps_norm = " ".join(ps.split())
                    if combined_norm == ps_norm:
                        return True
    return False


def _boundary_inside_quote(sent: str) -> bool:
    """Check if the end of `sent` is inside an unclosed quote."""
    return check_quote_balance(sent) > 0


# Abbreviation-like endings where pySBD is correct NOT to split.
# Covers single initials, multi-initials, and common continuation abbreviations.
_ABBREV_MERGE_EXCLUDE_RE = re.compile(
    r"(?:"
    r"(?<!\w)[A-Z]\.\s*$"  # single initial: J. B. I. X.
    r"|[A-Z]\.[A-Z]\.\s*$"  # double initial: W.H. A.R. C.S.
    r"|[Ee]\.g\.\s*$"
    r"|[Ii]\.e\.\s*$"
    r"|[Cc]f\.\s*$"
    r"|et\s+al\.\s*$"
    r"|a\.k\.a\.\s*$"
    r"|lit\.\s*$"
    r"|[Oo]p\.\s*$"
    r"|[Vv]ol\.\s*$"
    r"|[Nn]o\.\s*$"
    r"|pp\.\s*$"
    r"|U\.S\.(?:A\.)?\s*$"
    r"|D\.C\.\s*$"
    r")"
)


def check_pysbd_merges_across_newline(pysbd_sents: List[str], punkt_sents: List[str]) -> bool:
    """
    Check if pySBD incorrectly merged two sentences that happen to be
    separated by a newline (paragraph boundary within the text).
    Punkt separates them and pySBD glues them together.

    Excludes merges where pySBD is correctly keeping a quoted passage or
    abbreviation context together.
    """
    for ps in pysbd_sents:
        # If a pySBD sentence is significantly longer than any Punkt sentence
        # and corresponds to multiple Punkt sentences joined
        for i in range(len(punkt_sents) - 1):
            combined = punkt_sents[i].rstrip() + " " + punkt_sents[i + 1].lstrip()
            combined_norm = " ".join(combined.split())
            ps_norm = " ".join(ps.split())
            if combined_norm == ps_norm and len(punkt_sents[i]) > 40 and len(punkt_sents[i + 1]) > 40:
                sent_end = punkt_sents[i].rstrip()

                # Not a merge error if pySBD is keeping a quoted passage together
                if _boundary_inside_quote(sent_end):
                    continue

                # Not a merge error if the split is at an abbreviation / initial
                if _ABBREV_MERGE_EXCLUDE_RE.search(sent_end):
                    continue
                if MULTI_ABBREV_RE.search(sent_end[-10:] if len(sent_end) >= 10 else sent_end):
                    continue

                # Not a merge error if Punkt split inside unclosed parentheses
                if sent_end.count("(") > sent_end.count(")"):
                    continue

                return True
    return False


def normalize_sents(sents: List[str]) -> List[str]:
    """Normalize whitespace in sentences."""
    return [" ".join(s.split()) for s in sents]


def sents_equal_ignoring_headers(pysbd: List[str], punkt: List[str]) -> bool:
    """Check if after stripping headers, the sentence lists are identical."""
    p1 = normalize_sents(strip_headers(pysbd))
    p2 = normalize_sents(strip_headers(punkt))
    return p1 == p2


def find_split_differences(pysbd: List[str], punkt: List[str]) -> dict:
    """
    Analyze the specific differences between pySBD and Punkt outputs.
    Returns a dict with analysis results.
    """
    result = {
        "pysbd_has_headers": any(is_header(s) for s in pysbd),
        "punkt_has_headers": any(is_header(s) for s in punkt),
        "pysbd_orphans": [],
        "punkt_orphans": [],
        "pysbd_dotnet_split": False,
        "pysbd_bdfl_split": False,
        "punkt_quote_split": False,
        "punkt_abbrev_split": False,
        "punkt_paren_split": False,
        "pysbd_merge_error": False,
        "header_only_diff": False,
    }

    # Check for orphans
    for s in pysbd:
        if not is_header(s) and (is_orphan(s) or is_very_short_fragment(s)):
            result["pysbd_orphans"].append(s)

    for s in punkt:
        if not is_header(s) and (is_orphan(s) or is_very_short_fragment(s)):
            result["punkt_orphans"].append(s)

    # Strip headers and check if that resolves the difference
    pysbd_no_h = strip_headers(pysbd)
    punkt_no_h = strip_headers(punkt)
    if normalize_sents(pysbd_no_h) == normalize_sents(punkt_no_h):
        result["header_only_diff"] = True
        return result

    # Check for .NET split in pySBD
    result["pysbd_dotnet_split"] = has_dotnet_split(pysbd)

    # Check for BDFL-style parenthetical split in pySBD
    result["pysbd_bdfl_split"] = has_bdfl_style_split(pysbd)

    # Check for Punkt splitting inside quotes
    result["punkt_quote_split"] = check_punkt_splits_inside_quote(punkt, pysbd)

    # Check for Punkt splitting at abbreviations
    result["punkt_abbrev_split"] = check_punkt_splits_at_abbreviation(punkt, pysbd)

    # Check for Punkt splitting inside parentheses
    result["punkt_paren_split"] = check_punkt_splits_inside_parens(punkt, pysbd)

    # Check for pySBD incorrectly merging sentences
    result["pysbd_merge_error"] = check_pysbd_merges_across_newline(pysbd, punkt)

    return result


# ---------------------------------------------------------------------------
# Verdict determination
# ---------------------------------------------------------------------------


def determine_verdict(case_idx: int, case: dict) -> Tuple[str, str]:
    """
    Determine the verdict for a disagreement case.
    Returns (verdict, reasoning).
    """
    pysbd = case["pysbd"]
    punkt = case["punkt"]
    article = case["article"]

    analysis = find_split_differences(pysbd, punkt)
    reasons = []

    # -----------------------------------------------------------------------
    # 1. HEADER_SPLIT: only difference is that pySBD separates the header
    # -----------------------------------------------------------------------
    if analysis["header_only_diff"]:
        header_text = [s for s in pysbd if is_header(s)]
        return "HEADER_SPLIT", (
            f"The only difference is that pySBD extracts the section header "
            f"{repr(header_text[0][:60]) if header_text else '(header)'} as a "
            f"separate element while Punkt merges it with the first sentence. "
            f"This is a trivial formatting difference, not a real segmentation error."
        )

    # -----------------------------------------------------------------------
    # Collect error signals from both sides
    # -----------------------------------------------------------------------
    pysbd_errors = []
    punkt_errors = []

    # --- pySBD errors ---

    # Orphan fragments
    if analysis["pysbd_orphans"]:
        pysbd_errors.append(f"pySBD creates orphan fragment(s): {analysis['pysbd_orphans']}")

    # .NET split
    if analysis["pysbd_dotnet_split"]:
        pysbd_errors.append("pySBD incorrectly splits '.NET' at the period, creating a false sentence boundary before 'NET'")

    # BDFL-style parenthetical split
    if analysis["pysbd_bdfl_split"]:
        pysbd_errors.append(
            "pySBD incorrectly splits at a parenthetical abbreviation (e.g., "
            "'(BDFL)'), breaking a sentence at a parenthetical that continues "
            "the prior clause"
        )

    # Merge error (pySBD glues two separate sentences into one)
    if analysis["pysbd_merge_error"]:
        pysbd_errors.append(
            "pySBD incorrectly merges two distinct sentences into one (likely across a paragraph/newline boundary)"
        )

    # --- Punkt errors ---

    # Quote splits
    if analysis["punkt_quote_split"]:
        punkt_errors.append("Punkt incorrectly splits inside a quoted passage, breaking a quote across sentence boundaries")

    # Abbreviation splits
    if analysis["punkt_abbrev_split"]:
        punkt_errors.append(
            "Punkt incorrectly splits at an abbreviation (initials, 'e.g.', "
            "'U.S.', etc.), treating it as a sentence-ending period"
        )

    # Parenthesis splits
    if analysis["punkt_paren_split"]:
        punkt_errors.append("Punkt incorrectly splits inside parenthesized text")

    # -----------------------------------------------------------------------
    # Additional heuristic checks when primary checks didn't find errors
    # -----------------------------------------------------------------------

    pysbd_no_h = strip_headers(pysbd)
    punkt_no_h = strip_headers(punkt)

    # If pySBD has more sentences than Punkt (after removing headers),
    # and the difference is ONLY the header, classify accordingly.
    if analysis["pysbd_has_headers"] and not analysis["punkt_has_headers"] and len(pysbd_no_h) == len(punkt_no_h):
        # Header is the only extra -- but sentences themselves differ
        # (header was merged into first Punkt sentence).
        # Check if after stripping the header text from Punkt's first sentence,
        # the lists match.
        if punkt_no_h:
            # Punkt's first sentence might start with the header text
            first_punkt = punkt_no_h[0]
            for h in [s for s in pysbd if is_header(s)]:
                h_text = h.strip()
                if first_punkt.startswith(h_text):
                    remainder = first_punkt[len(h_text) :].strip()
                    if remainder and normalize_sents([remainder]) == normalize_sents(pysbd_no_h[:1]):
                        if not pysbd_errors and not punkt_errors:
                            return "HEADER_SPLIT", (
                                f"pySBD separates header {repr(h_text[:60])} "
                                f"from the body text; Punkt merges them. "
                                f"Trivial formatting difference."
                            )

    # Deep comparison: walk both sentence lists to find specific divergence points
    if not pysbd_errors and not punkt_errors:
        # Try to find where they diverge by joining and re-examining
        pysbd_joined = " ".join(normalize_sents(pysbd_no_h))
        punkt_joined = " ".join(normalize_sents(punkt_no_h))

        if pysbd_joined == punkt_joined:
            # Same text, different splits -- examine the nature of the splits
            pass

        # Check for Punkt splitting "..." (ellipsis in quotes) as sentence end
        for i in range(len(punkt_no_h) - 1):
            sent = punkt_no_h[i]
            if sent.rstrip().endswith("...") or sent.rstrip().endswith('..."'):
                # Check if this is inside a quote
                full_context = " ".join(punkt_no_h[max(0, i - 1) : i + 2])
                quote_depth = 0
                for ch in full_context:
                    if ch in '"\u201c':
                        quote_depth += 1
                    elif ch in '"\u201d':
                        quote_depth -= 1
                # Heuristic: if the ellipsis is inside a quote, Punkt shouldn't split
                if quote_depth != 0 or ('"' in sent and not sent.rstrip().endswith('"')):
                    if not any("quote" in e.lower() for e in punkt_errors):
                        punkt_errors.append("Punkt splits at an ellipsis within a quoted passage")

        # Check for Punkt splitting at "e.g." or "i.e." patterns in the middle
        for i in range(len(punkt_no_h) - 1):
            sent = punkt_no_h[i].rstrip()
            if re.search(r"\be\.g\.\s*$", sent) or re.search(r"\bi\.e\.\s*$", sent):
                if not any("abbreviation" in e.lower() for e in punkt_errors):
                    punkt_errors.append("Punkt splits at 'e.g.' or 'i.e.' abbreviation")

        # Check for pySBD creating fragments from "do..while" style text
        for i, s in enumerate(pysbd_no_h):
            stripped = s.strip()
            # Fragments like "." from splitting "do..while"
            if stripped == "." or stripped == "..":
                if not any("orphan" in e.lower() for e in pysbd_errors):
                    pysbd_errors.append(f"pySBD creates an orphan period fragment: {repr(stripped)}")

    # -----------------------------------------------------------------------
    # 2-5. Assign verdict based on collected errors
    # -----------------------------------------------------------------------

    if pysbd_errors and punkt_errors:
        return "BOTH_WRONG", ("Both splitters have errors. " + " | ".join(pysbd_errors) + " || " + " | ".join(punkt_errors))

    if punkt_errors and not pysbd_errors:
        return "PYSBD_CORRECT", " | ".join(punkt_errors)

    if pysbd_errors and not punkt_errors:
        return "PUNKT_CORRECT", " | ".join(pysbd_errors)

    # -----------------------------------------------------------------------
    # Fallback: no clear error detected by heuristics -- mark as AMBIGUOUS
    # or use structural clues
    # -----------------------------------------------------------------------

    # If pySBD has a header and Punkt doesn't (but not header_only_diff),
    # the remaining differences are typically trivial alongside the header
    if analysis["pysbd_has_headers"] and not analysis["punkt_has_headers"]:
        # The header accounts for the +1 difference; check if the rest aligns
        pysbd_core = strip_headers(pysbd)
        punkt_core = punkt_no_h

        # Handle the case where Punkt's first sentence includes the header text
        if punkt_core and any(is_header(s) for s in pysbd):
            headers = [s for s in pysbd if is_header(s)]
            for h in headers:
                h_stripped = h.strip()
                if punkt_core[0].startswith(h_stripped):
                    punkt_first_cleaned = punkt_core[0][len(h_stripped) :].strip()
                    adjusted_punkt = [punkt_first_cleaned] + punkt_core[1:] if punkt_first_cleaned else punkt_core[1:]
                    if normalize_sents(pysbd_core) == normalize_sents(adjusted_punkt):
                        return "HEADER_SPLIT", (
                            f"pySBD separates header {repr(h_stripped[:60])} "
                            f"while Punkt merges it with the first sentence. "
                            f"Trivial formatting difference."
                        )

        # Even if not exactly matching after header removal, check if the
        # header is the MAIN difference and the rest is close
        if abs(len(pysbd_core) - len(punkt_core)) <= 1:
            # Small difference besides header -- check for additional quote/abbrev issues
            # Try joining both and comparing
            pysbd_text = " ".join(normalize_sents(pysbd_core))
            punkt_text = " ".join(normalize_sents(punkt_core))
            if pysbd_text == punkt_text:
                return "HEADER_SPLIT", (
                    "After removing the header, both split the body text the "
                    "same way (though minor whitespace differences exist). "
                    "Trivial formatting difference."
                )

    # Check if the number of sentences differs by exactly the number of
    # orphans pySBD creates (indicating orphans are the whole difference)
    pysbd_orphan_count = sum(1 for s in pysbd_no_h if is_orphan(s) or is_very_short_fragment(s))
    punkt_orphan_count = sum(1 for s in punkt_no_h if is_orphan(s) or is_very_short_fragment(s))

    if pysbd_orphan_count > punkt_orphan_count:
        diff = pysbd_orphan_count - punkt_orphan_count
        orphans = [s for s in pysbd_no_h if is_orphan(s) or is_very_short_fragment(s)]
        return "PUNKT_CORRECT", (
            f"pySBD creates {diff} more orphan fragment(s) than Punkt: {orphans}. These are not real sentences."
        )

    # If both have orphans equally, could be both wrong
    if pysbd_orphan_count > 0 and punkt_orphan_count > 0:
        p_orph = [s for s in pysbd_no_h if is_orphan(s) or is_very_short_fragment(s)]
        k_orph = [s for s in punkt_no_h if is_orphan(s) or is_very_short_fragment(s)]
        return "BOTH_WRONG", (f"Both produce orphan fragments. pySBD: {p_orph}, Punkt: {k_orph}")

    return "AMBIGUOUS", (
        f"Both produce reasonable sentences with different boundary choices. "
        f"pySBD: {len(pysbd)} sentences, Punkt: {len(punkt)} sentences. "
        f"No clear error detected by heuristic analysis."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_paragraphs = data["total_paragraphs"]
    agree_count = data["agree"]
    disagree_count = data["disagree"]
    disagreements = data["disagreements"]

    print("=" * 80)
    print("FINAL VERDICTS: pySBD vs. Punkt Sentence Boundary Detection")
    print("=" * 80)
    print(f"\nDataset: {total_paragraphs} paragraphs total")
    print(f"  Agreed:    {agree_count}")
    print(f"  Disagreed: {disagree_count} (analyzing first {len(disagreements)})")
    print()

    verdicts = []
    for idx, case in enumerate(disagreements):
        verdict, reasoning = determine_verdict(idx, case)
        verdicts.append(
            {
                "case": idx,
                "article": case["article"],
                "verdict": verdict,
                "reasoning": reasoning,
                "pysbd_count": len(case["pysbd"]),
                "punkt_count": len(case["punkt"]),
            }
        )

    # -----------------------------------------------------------------------
    # Print per-case results
    # -----------------------------------------------------------------------
    print("-" * 80)
    print("CASE-BY-CASE ANALYSIS")
    print("-" * 80)

    for v in verdicts:
        print(f"\nCase {v['case']:2d} | Article: {v['article']}")
        print(f"  pySBD: {v['pysbd_count']} sentences | Punkt: {v['punkt_count']} sentences")
        print(f"  VERDICT: {v['verdict']}")
        # Wrap reasoning text for readability
        reasoning_lines = []
        words = v["reasoning"].split()
        line = "    "
        for w in words:
            if len(line) + len(w) + 1 > 78:
                reasoning_lines.append(line)
                line = "    " + w
            else:
                line += " " + w if line.strip() else "    " + w
        reasoning_lines.append(line)
        for rl in reasoning_lines:
            print(rl)

    # -----------------------------------------------------------------------
    # Tally
    # -----------------------------------------------------------------------
    tally = Counter(v["verdict"] for v in verdicts)

    print("\n" + "=" * 80)
    print("FINAL TALLY")
    print("=" * 80)

    verdict_order = ["PYSBD_CORRECT", "PUNKT_CORRECT", "HEADER_SPLIT", "AMBIGUOUS", "BOTH_WRONG"]
    for vtype in verdict_order:
        count = tally.get(vtype, 0)
        pct = count / len(verdicts) * 100
        bar = "#" * int(pct / 2)
        print(f"  {vtype:18s}: {count:3d} / {len(verdicts):2d}  ({pct:5.1f}%)  {bar}")

    print(f"\n  Total cases analyzed: {len(verdicts)}")

    # -----------------------------------------------------------------------
    # Accuracy assessment
    # -----------------------------------------------------------------------
    pysbd_correct = tally.get("PYSBD_CORRECT", 0)
    punkt_correct = tally.get("PUNKT_CORRECT", 0)
    header_split = tally.get("HEADER_SPLIT", 0)
    ambiguous = tally.get("AMBIGUOUS", 0)
    both_wrong = tally.get("BOTH_WRONG", 0)

    # Among cases with a clear winner, how often did each win?
    clear_winner_cases = pysbd_correct + punkt_correct
    if clear_winner_cases > 0:
        pysbd_win_rate = pysbd_correct / clear_winner_cases * 100
        punkt_win_rate = punkt_correct / clear_winner_cases * 100
    else:
        pysbd_win_rate = punkt_win_rate = 0

    # Paragraph-level accuracy:
    # - Paragraphs where they agree: both presumably correct
    # - Header-split and ambiguous: not real errors, add to "correct" for both
    # - Clear winner: one is correct, the other isn't

    # pySBD accuracy at paragraph level
    pysbd_correct_paras = agree_count + header_split + ambiguous + pysbd_correct
    punkt_correct_paras = agree_count + header_split + ambiguous + punkt_correct

    # Both-wrong subtracts from both
    # (we count agree + header + ambiguous as correct for BOTH)
    # Among the clear-verdict cases, each gets their wins

    total_assessed = agree_count + len(verdicts)

    # Effective accuracy = (agree + header_trivial + ambiguous_ok + wins) / total
    pysbd_accuracy = pysbd_correct_paras / total_assessed * 100
    punkt_accuracy = punkt_correct_paras / total_assessed * 100

    print("\n" + "=" * 80)
    print("PARAGRAPH-LEVEL ACCURACY ASSESSMENT")
    print("=" * 80)

    print(f"""
  Total paragraphs assessed:     {total_assessed}
    Agreed (both correct):       {agree_count}
    Header-split (trivial diff): {header_split}
    Ambiguous (no clear error):  {ambiguous}
    pySBD correct, Punkt wrong:  {pysbd_correct}
    Punkt correct, pySBD wrong:  {punkt_correct}
    Both wrong:                  {both_wrong}

  Among {clear_winner_cases} cases with a clear winner:
    pySBD wins: {pysbd_correct:3d}  ({pysbd_win_rate:.1f}%)
    Punkt wins: {punkt_correct:3d}  ({punkt_win_rate:.1f}%)

  Effective paragraph-level accuracy (agree + trivial + ambiguous + wins):
    pySBD: {pysbd_correct_paras:3d} / {total_assessed} = {pysbd_accuracy:.1f}%
    Punkt: {punkt_correct_paras:3d} / {total_assessed} = {punkt_accuracy:.1f}%
""")

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
  pySBD's main strengths:
    - Correctly handles quoted passages (keeps quotes together)
    - Correctly handles abbreviations (W. E. B., U.S., e.g., etc.)
    - Separates section headers as distinct elements

  pySBD's main weaknesses:
    - Sometimes splits at parentheticals like '(BDFL)'
    - Occasionally merges sentences across paragraph boundaries

  Punkt's main strengths:
    - Keeps parenthetical abbreviations attached

  Punkt's main weaknesses:
    - Splits inside quoted passages (most common error)
    - Splits at abbreviations/initials
    - Merges section headers with body text (minor)
    - Splits inside parenthesized text

  Overall: pySBD demonstrates stronger performance on these Wikipedia texts,
  particularly excelling at quote handling and abbreviation recognition.
  Punkt's most frequent error is splitting inside quoted passages.
""")

    # -----------------------------------------------------------------------
    # Write machine-readable results
    # -----------------------------------------------------------------------
    output_file = "final_verdicts.json"
    output = {
        "summary": {
            "total_paragraphs": total_assessed,
            "agreed": agree_count,
            "disagreements_analyzed": len(verdicts),
            "tally": {vtype: tally.get(vtype, 0) for vtype in verdict_order},
            "pysbd_accuracy_pct": round(pysbd_accuracy, 1),
            "punkt_accuracy_pct": round(punkt_accuracy, 1),
            "pysbd_win_rate_clear_cases_pct": round(pysbd_win_rate, 1),
            "punkt_win_rate_clear_cases_pct": round(punkt_win_rate, 1),
        },
        "verdicts": verdicts,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  Machine-readable results written to: {output_file}")


if __name__ == "__main__":
    main()
