# -*- coding: utf-8 -*-
from sentencesplit.abbreviation_replacer import AbbreviationReplacer
from sentencesplit.lang.common import Common, Standard
from sentencesplit.lang.english import English


class EnglishLegal(Common, Standard):
    iso_code = "en_legal"

    class Abbreviation(Standard.Abbreviation):
        LEGAL_ABBREVIATIONS = [
            # --- Court & Tribunal Abbreviations ---
            "app",  # Appellate
            "arb",  # Arbitration
            "bankr",  # Bankruptcy
            "cir",  # Circuit
            "crim",  # Criminal
            "fam",  # Family (court)
            "prob",  # Probate
            "sup",  # Superior / Supreme
            "surr",  # Surrogate
            # --- Case & Citation Abbreviations ---
            "aff'd",  # Affirmed
            "cert",  # Certiorari
            "rev'd",  # Reversed
            "reh'g",  # Rehearing
            "vacated",
            # --- Legal Reporter / Source Abbreviations ---
            "f.supp",  # Federal Supplement
            "f.2d",  # Federal Reporter, Second Series
            "f.3d",  # Federal Reporter, Third Series
            "f.4th",  # Federal Reporter, Fourth Series
            "s.ct",  # Supreme Court Reporter
            "l.ed",  # Lawyers' Edition
            "l.ed.2d",  # Lawyers' Edition, Second Series
            "u.s.c",  # United States Code
            "c.f.r",  # Code of Federal Regulations
            "fed.reg",  # Federal Register
            "stat",  # Statutes at Large
            "pub.l",  # Public Law
            # --- Legal Title Abbreviations ---
            "atty",  # Attorney
            "j",  # Justice / Judge
            "jj",  # Justices (plural)
            "ch",  # Chancellor / Chapter
            "mag",  # Magistrate
            # --- Document & Procedural Abbreviations ---
            "aff",  # Affidavit
            "amend",  # Amendment
            "app'x",  # Appendix
            "compl",  # Complaint
            "decl",  # Declaration
            "def",  # Defendant / Definition
            "defs",  # Defendants
            "dep",  # Deposition
            "ex",  # Exhibit / Example
            "mot",  # Motion
            "op",  # Opinion (already in Standard)
            "par",  # Paragraph
            "paras",  # Paragraphs
            "pet",  # Petition / Petitioner
            "pl",  # Plaintiff (already in Standard)
            "pls",  # Plaintiffs
            "proc",  # Proceedings
            "reg",  # Regulation
            "regs",  # Regulations
            "resp",  # Respondent
            "stip",  # Stipulation
            "supp",  # Supplement / Supplemental
            "syl",  # Syllabus
            # --- Legal Latin Abbreviations ---
            "et al",  # And others
            "ibid",  # In the same place
            "infra",  # Below
            "supra",  # Above
            "loc.cit",  # In the place cited
            "op.cit",  # In the work cited
            "passim",  # Throughout
            "arguendo",
            "seriatim",
            "sub nom",  # Under the name
            # --- Contract & Transactional Abbreviations ---
            "agmt",  # Agreement
            "assgt",  # Assignment
            "auth",  # Authority / Authorization
            "cl",  # Clause (already in Standard)
            "eff",  # Effective
            "encl",  # Enclosure
            "exec",  # Executive / Executed
            "guar",  # Guaranty / Guarantee
            "indem",  # Indemnity
            "jt",  # Joint
            "lic",  # License
            "mem",  # Memorandum
            "mgmt",  # Management
            "mtg",  # Meeting / Mortgage
            "neg",  # Negligence / Negotiable
            "oblig",  # Obligation
            "prov",  # Provision
            "provs",  # Provisions
            "pty",  # Party (entity)
            "recit",  # Recital
            "sched",  # Schedule
            "subpar",  # Subparagraph
            "subsec",  # Subsection
            "approx",  # Approximately
            # --- Regulatory & Administrative Abbreviations ---
            "admin",  # Administrative
            "comm'n",  # Commission
            "comm'r",  # Commissioner
            "dept",  # Department (already in Standard)
            "div",  # Division
            "gov't",  # Government
            "legis",  # Legislative / Legislature
            "mun",  # Municipal
            "nat'l",  # National
            "twp",  # Township
        ]

        ABBREVIATIONS = sorted(set(Standard.Abbreviation.ABBREVIATIONS + LEGAL_ABBREVIATIONS))

        LEGAL_PREPOSITIVE_ABBREVIATIONS = [
            "atty",  # Attorney [name]
            "j",  # Justice [name]
            "jj",  # Justices [names]
            "ch",  # Chancellor [name]
            "mag",  # Magistrate [name]
            # Court/tribunal types often followed by "Court", "Judge", etc.
            "admin",  # Admin. Law Judge
            "app",  # App. Div., App. Ct.
            "arb",  # Arb. Panel
            "bankr",  # Bankr. Court
            "cir",  # 9th Cir. Court
            "crim",  # Crim. Court
            "dist",  # Dist. Court (also in Standard ABBREVIATIONS)
            "fam",  # Fam. Court
            "prob",  # Prob. Court
            "sup",  # Sup. Court
            "surr",  # Surr. Court
            # Document references often followed by uppercase identifiers
            "amend",  # Amend. XIV
            "sched",  # Sched. A
        ]

        PREPOSITIVE_ABBREVIATIONS = sorted(
            set(Standard.Abbreviation.PREPOSITIVE_ABBREVIATIONS + LEGAL_PREPOSITIVE_ABBREVIATIONS)
        )

        LEGAL_NUMBER_ABBREVIATIONS = [
            "par",  # par. 5
            "paras",  # paras. 1-3
            "cl",  # cl. 7
            "sec",  # sec. 12 (already in Standard as general)
            "amend",  # amend. XIV
            "reg",  # reg. 4
            "sched",  # sched. A
            "subsec",  # subsec. (a)
            "subpar",  # subpar. (i)
        ]

        NUMBER_ABBREVIATIONS = sorted(set(Standard.Abbreviation.NUMBER_ABBREVIATIONS + LEGAL_NUMBER_ABBREVIATIONS))

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = English.AbbreviationReplacer.SENTENCE_STARTERS + [
            "After",
            "Although",
            "And",
            "As",
            "Because",
            "Before",
            "But",
            "Each",
            "Even",
            "Here",
            "His",
            "Her",
            "If",
            "Its",
            "No",
            "On",
            "Our",
            "So",
            "Such",
            "Their",
            "This",
            "Thus",
            "Under",
            "Yet",
        ]
        # Court/tribunal abbreviations that are prepositive (e.g. "Bankr. Court")
        # but can also legitimately end a sentence (e.g. "The 9th Cir. The panel
        # reversed.").  Listing them here allows sentence splits before known
        # sentence starters while still protecting them before non-starters.
        STARTER_AWARE_PREPOSITIVE = AbbreviationReplacer.STARTER_AWARE_PREPOSITIVE | frozenset(
            {
                "admin",
                "app",
                "arb",
                "bankr",
                "cir",
                "crim",
                "dist",
                "fam",
                "prob",
                "sup",
                "surr",
            }
        )
