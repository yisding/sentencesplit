# -*- coding: utf-8 -*-
import pytest

from sentencesplit.segmenter import Segmenter

LEGAL_TEST_CASES = [
    # --- Case citations with "v." should not split ---
    (
        "The ruling in Brown v. Board of Education changed the law.",
        ["The ruling in Brown v. Board of Education changed the law."],
    ),
    (
        "In Roe v. Wade, the Court held that the right to privacy exists.",
        ["In Roe v. Wade, the Court held that the right to privacy exists."],
    ),
    # --- Legal reporter abbreviations ---
    (
        "See 42 U.S.C. § 1983 for the relevant statute.",
        ["See 42 U.S.C. § 1983 for the relevant statute."],
    ),
    (
        "The case is reported at 521 U.S. 844.",
        ["The case is reported at 521 U.S. 844."],
    ),
    # --- Court abbreviations ---
    (
        "The 9th Cir. reversed the lower court. The case was remanded.",
        ["The 9th Cir. reversed the lower court.", "The case was remanded."],
    ),
    (
        "The Bankr. Court approved the plan.",
        ["The Bankr. Court approved the plan."],
    ),
    # --- Legal title abbreviations ---
    (
        "J. Roberts delivered the opinion of the Court.",
        ["J. Roberts delivered the opinion of the Court."],
    ),
    (
        "Atty. Smith filed the motion on Monday.",
        ["Atty. Smith filed the motion on Monday."],
    ),
    # --- Document/procedural abbreviations ---
    (
        "See Compl. at par. 12 for the factual allegations.",
        ["See Compl. at par. 12 for the factual allegations."],
    ),
    (
        "The Def. filed a mot. to dismiss the complaint.",
        ["The Def. filed a mot. to dismiss the complaint."],
    ),
    (
        "Pursuant to Amend. XIV, equal protection is guaranteed.",
        ["Pursuant to Amend. XIV, equal protection is guaranteed."],
    ),
    # --- Legal Latin abbreviations ---
    (
        "Smith et al. filed the brief. The court agreed.",
        ["Smith et al. filed the brief.", "The court agreed."],
    ),
    (
        "See supra at 5. The argument is well-founded.",
        ["See supra at 5.", "The argument is well-founded."],
    ),
    # --- Contract abbreviations ---
    (
        "Under cl. 7 of the agmt. the parties must arbitrate.",
        ["Under cl. 7 of the agmt. the parties must arbitrate."],
    ),
    (
        "See sched. A for the list of assets.",
        ["See sched. A for the list of assets."],
    ),
    # --- Regulatory abbreviations ---
    (
        "The Admin. Law Judge ruled in favor of the petitioner.",
        ["The Admin. Law Judge ruled in favor of the petitioner."],
    ),
    (
        "Under 29 C.F.R. § 1910.134, employers must comply.",
        ["Under 29 C.F.R. § 1910.134, employers must comply."],
    ),
    # --- Multiple legal abbreviations in one passage ---
    (
        "In Smith v. Jones, 550 F.Supp. 123, the Dist. Court held for the Pl. The 2nd Cir. affirmed.",
        [
            "In Smith v. Jones, 550 F.Supp. 123, the Dist. Court held for the Pl.",
            "The 2nd Cir. affirmed.",
        ],
    ),
    # --- Sentence boundaries should still work ---
    (
        "The court granted the motion. The case was dismissed.",
        ["The court granted the motion.", "The case was dismissed."],
    ),
    (
        "Is the defendant liable? The jury must decide.",
        ["Is the defendant liable?", "The jury must decide."],
    ),
]


@pytest.mark.parametrize(
    "text,expected",
    LEGAL_TEST_CASES,
    ids=[f"legal_{i}" for i in range(len(LEGAL_TEST_CASES))],
)
def test_en_legal(text, expected):
    segmenter = Segmenter(language="en_legal", clean=False)
    result = [s.strip() for s in segmenter.segment(text)]
    assert result == expected
