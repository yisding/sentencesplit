# Cross-Library Sentence-Boundary Comparison Report

This report compares **sentencesplit** (this library) against four other sentence
boundary detection (SBD) tools across multilingual, multi-domain corpora. It combines
an *objective* scoreboard (exact-match and boundary-F1 against gold annotations) with a
*qualitative* adjudication of 120 cases where the libraries disagreed.

---

## Methodology

### Corpora

| Corpus | Domain / type | Languages |
| --- | --- | --- |
| `golden_rules` | pySBD/pragmatic_segmenter "Golden Rules" edge cases | en |
| Universal Dependencies treebanks | Annotated news / wiki / web prose (gold sentence segmentation) | en (EWT, GUM), de (GSD), fr (GSD), es (GSD), it (ISDT), nl (Alpino), ru (GSD), el (GDT), zh (GSD) |
| Wikipedia | Multi-domain encyclopedic text (multilingual) | en, de, fr, es, it, nl, ru |
| Project Gutenberg | Literary prose / dialogue | en |
| Legal | U.S. Supreme Court syllabi & opinions | en |

UD gold paragraphs were reconstructed by space-joining the gold sentences (no-space join
for `zh`). Golden-rules, Wikipedia, Gutenberg, and legal units are used as-is. Wikipedia /
Gutenberg / legal units have **no gold annotation** and were adjudicated by linguistic
judgment only.

### Segmenters compared

| Segmenter | Kind | Notes |
| --- | --- | --- |
| **sentencesplit** | rule-based | This library (pySBD-derived). |
| pysbd | rule-based | Python port of pragmatic_segmenter. |
| pragmatic_segmenter | rule-based | Original Ruby reference implementation. |
| punkt | statistical | NLTK Punkt unsupervised tokenizer (10 languages). |
| syntok | rule-based | Tokenizer-driven (8 languages). |

### Excluded segmenters

Three segmenters could not run in this environment and were dropped:

| Segmenter | Reason |
| --- | --- |
| blingfire | `import blingfire` failed: `libblingfiretokdll.so: cannot open shared object file` (no native ARM build). |
| spacy_sentencizer | Crashed importing spaCy (signal 4; native/ARM incompatibility). |
| stanza | Crashed importing stanza (signal 4; native/ARM incompatibility). |

### Metrics

From the scoreboard's `metric_notes`:

- **exact_match**: the predicted sentence list equals the gold list *exactly* (strict
  string equality over the whole list).
- **boundary_f1**: F1 over whitespace-insensitive boundary positions. Units where a tool
  *altered the underlying characters* are excluded and counted separately
  (`altered_text_units`: syntok = 9, pragmatic_segmenter = 2).

`n` differs per segmenter because each tool only runs on the languages it supports:
sentencesplit / pysbd / pragmatic_segmenter cover all 348 gold units; punkt covers 318
(10 languages, no zh); syntok covers 258 (8 languages, no ru/el/zh).

### Adjudication procedure

Of **596** total units, **218** were divergent (libraries disagreed) -- a 63.4% agreement
rate. Divergences were **capped at 120** for individual review, so **98 divergences were
not adjudicated**. Each of the 120 reviewed cases received a single-judge verdict
(`winner`, `ranking`, `category`, `severity`, `confidence`, and a `sentencesplit_assessment`
of correct/incorrect). This is a **single-judge** adjudication: verdicts reflect one
reviewer's reading of gold (where present) or linguistic plausibility (where gold is null),
and should be read as informed opinion rather than a second gold standard.

---

## Objective Scoreboard

### Overall (all gold units)

| Segmenter | Exact-match % | Boundary-F1 % | n |
| --- | ---: | ---: | ---: |
| **sentencesplit** | **74.4** | **93.7** | 348 |
| pysbd | 73.3 | 93.5 | 348 |
| pragmatic_segmenter | 73.0 | 93.5 | 348 |
| punkt | 70.4 | 90.4 | 318 |
| syntok | 64.3 | 90.7 | 258 |

**sentencesplit leads on both metrics overall**, narrowly ahead of pysbd /
pragmatic_segmenter (its lineage) and clearly ahead of punkt and syntok. Note that punkt's
and syntok's lower `n` (they skip several languages) makes the overall numbers not strictly
comparable -- the per-language table below is the fairer view.

### By language (exact-match % / boundary-F1 %)

| Language | sentencesplit | pysbd | pragmatic_segmenter | punkt | syntok |
| --- | --- | --- | --- | --- | --- |
| en | 82.4 / 95.7 | **83.3 / 95.9** | 82.4 / 95.9 | 62.0 / 83.8 | 67.6 / 89.8 |
| de | 63.3 / 92.1 | 63.3 / 92.1 | 63.3 / 91.7 | **73.3 / 94.6** | 66.7 / 92.9 |
| fr | 86.7 / 97.7 | 86.7 / 97.7 | 86.7 / 97.7 | **90.0 / 98.6** | 70.0 / 94.2 |
| es | 73.3 / 95.8 | 63.3 / 93.9 | 63.3 / 93.9 | 70.0 / 95.1 | **80.0 / 97.5** |
| it | 50.0 / 81.5 | 50.0 / 83.0 | 50.0 / 83.0 | **56.7 / 89.9** | 33.3 / 83.3 |
| nl | 63.3 / 91.4 | 66.7 / 91.8 | 66.7 / 91.8 | **90.0 / 98.9** | 60.0 / 88.9 |
| ru | 70.0 / 95.3 | 70.0 / 94.6 | 70.0 / 94.6 | **80.0 / 97.2** | -- |
| el | 63.3 / 88.6 | 63.3 / 88.6 | 63.3 / 88.6 | 63.3 / 81.9 | -- |
| zh | **96.7 / 99.5** | 86.7 / 98.1 | 86.7 / 98.1 | -- | -- |

**Where sentencesplit leads:** Chinese (96.7% exact, +10 pts over pysbd thanks to its CJK
quote-continuation resplit logic), Spanish (73.3% exact, +10 over the pysbd pair), and it
ties the rule-based pack on English/French/Greek.

**Where punkt leads:** German, French, Italian, Dutch, and Russian on exact-match. punkt's
statistical abbreviation model is notably stronger on Dutch (90.0% vs 63.3%) and on the
noisier UD treebanks where capitalization/numeric cues matter. Greek boundary-F1 is the one
place punkt trails (81.9% vs 88.6%) because it does not recognize the Greek question mark.

**English Golden Rules** (the classic pySBD edge-case suite) is where the rule-based trio
shines: sentencesplit / pysbd / pragmatic_segmenter all hit **97.9% exact / 99.6 F1**,
versus punkt 56.2% and syntok 70.8% -- the statistical and tokenizer-driven tools fail the
list-numbering, abbreviation, and ellipsis edge cases that rule-based systems are tuned for.

---

## Adjudication Results

### Overall win counts (120 adjudicated cases)

| Segmenter | Wins |
| --- | ---: |
| **sentencesplit** | **73** |
| pragmatic_segmenter | 72 |
| pysbd | 68 |
| punkt | 47 |
| syntok | 37 |

(A "win" credits *every* library in a case's winning set, so totals exceed 120. In **22**
cases **no** library matched gold/correct output -- `none_correct` -- and **1** case was a
clean tie among the rule-based group.)

### sentencesplit head-to-head

- **In 73 of 120 adjudicated cases (60.8%), sentencesplit was among the winners** (produced
  the correct / closest output).
- **In 47 of 120 (39.2%), it was not** -- it lost outright or was the worse representative of
  a non-matching group.
- Breakdown of the 47 losses by severity: **13 major, 31 minor, 3 trivial**.
- `sentencesplit_assessment`: **73 correct, 47 incorrect, 0 tied, 0 not-applicable** --
  exactly mirroring the win/loss split.

### Distribution of adjudicated cases by category

| Category | Cases |
| --- | ---: |
| abbreviation | 33 |
| quotation | 19 |
| under_split | 18 |
| other | 13 |
| whitespace_or_formatting | 8 |
| parenthetical | 7 |
| list_item_or_numbering | 5 |
| ellipsis | 5 |
| decimal_or_number | 4 |
| initials_or_name | 3 |
| over_split | 2 |
| header_or_title | 2 |
| url_or_email | 1 |

Abbreviation handling is the single most contested category (33 cases), followed by
quotation (19) and under-splitting (18) -- these three account for over half of all reviewed
divergences.

---

## Where sentencesplit Wins

The following are representative *high-confidence* wins (prioritizing `major` severity). In
each, sentencesplit alone or with the rule-based group matched gold / the correct reading.

**case_0014 -- `ud_fr_gsd`, abbreviation, major.** sentencesplit was the *sole* winner.
> *"The disputed boundary is the period after the parenthetical '...Venezueliens, etc.)', which gold treats as a sentence terminator... sentencesplit splits exactly there and matches gold verbatim (5 sentences). pysbd, pragmatic_segmenter, and punkt under-split: they treated 'etc.' as a non-terminal abbreviation and merged '...etc.) C'est a Dakhla...' into one sentence. syntok found the boundary but over-split..."*

**case_0028 -- `ud_fr_gsd`, quotation, major.** Disputed text: `...a la Haye ».` / `...Republique islamique ».`
> *"sentencesplit, pysbd, pragmatic_segmenter, and punkt all reproduce gold exactly. syntok produced only 3 sentences... failing to split at the French closing-guillemet boundaries. The terminal period after the closing guillemet » is a true sentence boundary in French."*

**case_0032 -- `ud_it_isdt`, under_split, major.** Disputed text: `...due figli (Cattaneo). era partito...` and `...state bene. assassini...`
> *"Gold splits at two periods that are followed by a lowercase word... sentencesplit... correctly treating the sentence-final period+space as a boundary even though the next sentence opens lowercase. syntok under-splits (only 3 segments)... evidently requiring an uppercase sentence-start."*

**case_0038 -- `ud_en_ewt`, abbreviation, major.** Disputed text: `...his involvement at the D.C. Circuit level...`
> *"Gold keeps this as part of the first sentence. sentencesplit, pysbd, pragmatic_segmenter, and syntok all correctly treat 'D.C.' as an abbreviation and do not split. punkt wrongly split after 'D.C.'... failing to recognize the abbreviation followed by the capitalized word 'Circuit'."*

**case_0047 -- `golden_rules`, abbreviation, major.** Disputed text: `I can see Mt. Fuji from here.`
> *"The period after 'Mt' is the abbreviation dot for 'Mount'... sentencesplit, pysbd, pragmatic_segmenter, and syntok all correctly kept 'Mt. Fuji' together... punkt is the only loser: it split after 'Mt.'"*

**case_0082 -- `wikipedia_de`, decimal_or_number, major.** Disputed text: `(* 14. Maerz 1879 in Ulm; + 18. April 1955 in Princeton...)`
> *"the German ordinal-day markers '14.' and '18.' are followed by month names... and are NOT sentence boundaries. sentencesplit, pysbd, pragmatic_segmenter and punkt all correctly kept these attached... syntok wrongly split after '14.'... and after '18.'..."*

**case_0103 -- `legal`, abbreviation, major.** Disputed text: `In Los Angeles Dept. of Water and Power v. Manhart`
> *"'Dept.' abbreviates 'Department' and is mid-citation, not a sentence end. sentencesplit, pysbd, pragmatic_segmenter, and syntok all correctly treated it as an abbreviation... punkt wrongly split after 'Dept.', emitting the spurious fragment 'In Los Angeles Dept.'"*

**case_0099 -- `legal`, ellipsis, major.** Disputed text: spaced ellipses `. . .` and citation `42 U. S. C. 2000e-2(a)(1).` plus `Pp. 4-12.`
> *"sentencesplit (tied with pysbd and pragmatic_segmenter) correctly produced exactly these three sentences, keeping the citation attached to the quote and 'Pp. 4-12.' intact. syntok wrongly split at the closing quote... punkt was worst: it shattered each '. . .' ellipsis into separate fragments..."*

Also notable: **case_0003/0005/0006** (Chinese full-stop + closing-quote continuation,
sentencesplit the sole winner -- its CJK resplit beats pysbd/pragmatic) and **case_0085**
(Gutenberg embedded `"Oh dear!"` exclamations kept inside one sentence, where punkt/syntok
over-split).

---

## Where sentencesplit Loses

The following are representative *high-confidence* losses (prioritizing `major` severity).

**case_0080 -- `gutenberg`, quotation, major.** Disputed text: a single multi-sentence quotation `"...a little more. Just a trifle more... Watson. And in practice... I observe. You did not..."`
> *"punkt and syntok correctly split at these three internal terminal periods, yielding four sentences. sentencesplit, pysbd, and pragmatic_segmenter treated the entire span as one segment, suppressing all internal boundaries simply because the text is wrapped in one pair of quotation marks (the closing quote does not arrive until after the fourth sentence)."*

This is the clearest systematic weakness: **multi-sentence quotations whose closing quote is
far away** make sentencesplit suppress *all* interior sentence-final periods. Same failure in
**case_0106** (Sherlock Holmes dialogue, major) and **case_0110** (minor).

**case_0017 -- `ud_el_gdt`, abbreviation, major.** Disputed text: `apo ti Synodo E.E. - IPA stin Praga`
> *"sentencesplit, pysbd, and pragmatic_segmenter... wrongly treat each period of 'E.E.' as a boundary, producing the bogus fragments '...ti Synodo E.' and a standalone 'E.'; punkt correctly keeps 'Synodo E.E. - IPA' intact."*

Missing Greek/Russian abbreviations recurs: **case_0056** (Greek `m.Ch.` = A.D., major;
"sentencesplit evidently lacks 'm.Ch.' in its Greek abbreviation list"), **case_0069**
(Russian `Sr.` = cf.), **case_0079** (Russian `angl.`/`nem.`/`fr.` before Latin words, major).

**case_0019 -- `ud_de_gsd`, over_split, major.** Disputed text: `...einfach Top!!! Der Fisch ist immer frisch...`
> *"sentencesplit, pysbd, and pragmatic_segmenter FAILED to split at 'Top!!!', merging... into one segment... sentencesplit's failure to break on '!!!' before a capitalized word is the concrete error."*

Same multi-exclamation failure (minor) in **case_0075** (`...ignoriert!!! Bei Rechtsanwalt...`):
*"sentencesplit's continuous-punctuation handling protected the '!!!' cluster and did not re-split before the capitalized 'Bei'."*

**case_0116 -- `wikipedia_de`, decimal_or_number, major.** Disputed text: `Im Laufe des 19. und fruehen 20. Jahrhunderts...`
> *"sentencesplit (tied with pysbd and pragmatic_segmenter) wrongly split the period after 'des'->'19.' and after 'fruehen'->'20.', emitting the fragments 'Im Laufe des', '19. und fruehen', '20. Jahrhunderts...'. punkt alone keeps this as one sentence."*

Interesting: sentencesplit handles German ordinal-before-month correctly (case_0082, 0086,
0104) but **fails on ordinal-before-noun mid-clause** here (`19. ... Jahrhunderts`).

**case_0101 -- `wikipedia_en`, abbreviation, major.** Disputed text: `...in Washington, D.C. Justices have lifetime tenure...`
> *"The period in 'D.C.' is doing double duty: it abbreviates the second initial AND terminates the sentence... sentencesplit, pysbd, pragmatic_segmenter, and syntok all treated 'D.C.' purely as a non-terminal abbreviation and ran the two sentences together. punkt correctly split here."*

The mirror of case_0038 -- abbreviation-as-terminal at a true sentence end is the hard case
that rule-based abbreviation suppression gets wrong.

**case_0024 -- `ud_ru_gsd`, under_split, major.** Disputed text: `...Tverskoy oblasti. Dohod...` and `...dollarov v god. 2,7...`
> *"sentencesplit, pysbd, and pragmatic_segmenter (identical 3-sentence output) collapsed gold sentences 2, 3 and 4 into one block... sentencesplit additionally failing the clean 'oblasti.' -> 'Dohod' capital-start boundary."*

Also: **case_0092 / 0117 / 0118 / 0119 / 0120** (Spanish Wikipedia, whitespace_or_formatting)
-- sentencesplit gets all real boundaries right but emits a **spurious trailing zero-width-space
(U+200B) fragment** as a phantom final "sentence". A genuine, repeatable cosmetic bug.

---

## Patterns & Recommendations

### sentencesplit's error profile (47 losses by category)

| Category | Losses |
| --- | ---: |
| abbreviation | 13 |
| under_split | 7 |
| quotation | 6 |
| other | 6 |
| whitespace_or_formatting | 6 |
| list_item_or_numbering | 2 |
| header_or_title | 2 |
| initials_or_name | 1 |
| over_split | 1 |
| parenthetical | 1 |
| ellipsis | 1 |
| decimal_or_number | 1 |

The losses cluster in five areas. Concrete, actionable recommendations:

1. **Multi-sentence quotation handling (quotation, 6 losses; the worst systematic gap).**
   When a quotation spans several sentences and the closing quote is far away, sentencesplit
   suppresses *every* interior terminal period (case_0080, 0106, 0110). Recommendation: stop
   treating an open quotation as a blanket split-suppression region. Allow interior splits at
   `. ` / `? ` / `! ` followed by a capitalized word *even while inside an unclosed quote*,
   as punkt/syntok do. This is the single highest-value fix and would also help Gutenberg
   exact-match.

2. **Missing non-Latin abbreviations (abbreviation, multiple losses).** The Greek and Russian
   abbreviation lists are incomplete. Add at minimum: Greek `m.Ch.` (A.D.), `p.Ch.` (B.C.),
   `E.E.` (E.U.); Russian `Sr.` (cf.), and ensure inline language tags `angl.`/`nem.`/`fr.`
   (and similar) are suppressed *even when followed by a capitalized Latin-script word*
   (case_0017, 0056, 0069, 0079). Also add the all-caps company form `CO.` (case_0095) and
   chained botanical-author initials like `N.E.Br.` followed by a comma (case_0073).

3. **Multiple-punctuation terminators before a capital (over_split / whitespace, 2 losses).**
   `!!!`, `???`, and `!?` clusters followed by a capitalized word are being protected by the
   continuous-punctuation rule and never re-split (case_0019, 0075). Recommendation: after the
   continuous-punctuation pass, re-apply a boundary check for `[!?]{2,}\s+[A-Z...]` (including
   accented German/European capitals).

4. **Trailing zero-width-space phantom fragment (whitespace, ~5 losses).** A lone U+200B (and
   likely other zero-width / format chars) at the end of input is emitted as an empty final
   "sentence" (case_0092, 0117-0120). Recommendation: strip / merge segments that contain only
   whitespace or zero-width characters in `split_into_segments()` post-processing. This is a
   trivial, repeatable fix that would flip several Spanish-Wikipedia cases.

5. **German ordinal-before-noun (decimal_or_number, 1 loss).** Ordinals before month names are
   handled, but `19.`/`20.` before a noun like `Jahrhundert` are split (case_0116). Recommend
   extending the numeric-ordinal protection to the general German pattern of `\d{1,2}\.` in
   ordinal contexts, not just month names.

### Honesty about competitors

- **punkt is genuinely better at the abbreviation-as-terminal problem** (case_0038's mirror
  case_0101, and `Pp.`/`107` legal-citation nuances) and at German/Dutch/Russian
  exact-match overall. Its statistical model resolves the "abbreviation that also ends a
  sentence" ambiguity that no current rule reliably handles.
- **syntok and pragmatic_segmenter** each win the trailing-zero-width-space cases purely by
  dropping empty fragments -- a behavior sentencesplit should copy.
- Many `none_correct` losses (e.g. UD-Greek colon-as-boundary, UD-Italian colon fragments,
  UD-EWT colon list entries) are **corpus annotation artifacts**, not real sentence boundaries;
  these are not worth chasing and would hurt normal-text quality if "fixed".

Overall, sentencesplit's rule base is the strongest of the group on the objective metrics and
the adjudication win count, and dominant on Chinese and the English Golden Rules. The
addressable gaps are narrow and concrete: multi-sentence quotations, a handful of non-Latin
abbreviations, multi-bang terminators, and a one-line zero-width-space cleanup.

---

## Appendix -- All Adjudicated Cases

| case_id | corpus | lang | winner | category | severity | reason (one-line) |
| --- | --- | --- | --- | --- | --- | --- |
| case_0001 | ud_it_isdt | it | none_correct | list_item_or_numbering | major | Gold treats article numbers "889."/"892." as sentence STARTS; sentencesplit splits AFTER the number, corrupting two boundaries. |
| case_0002 | ud_es_gsd | es | sentencesplit | abbreviation | minor | "41,76 hab. / km2" -- sentencesplit alone keeps the density unit intact; others split after "hab." |
| case_0003 | ud_zh_gsd | zh | sentencesplit | quotation | minor | CJK full-stop+closing-quote -- sentencesplit splits after closing bracket; pysbd/pragmatic merge. |
| case_0004 | ud_es_gsd | es | sentencesplit | abbreviation | minor | "133,45 hab. / km2" -- sentencesplit alone keeps the density unit intact. |
| case_0005 | ud_zh_gsd | zh | sentencesplit | quotation | minor | CJK quotation end -- sentencesplit splits after closing CJK quote; pysbd/pragmatic merge. |
| case_0006 | ud_zh_gsd | zh | sentencesplit | quotation | minor | CJK quote-end before new sentence -- sentencesplit splits after closing quote; the two Ruby-derived tools merge. |
| case_0007 | ud_nl_alpino | nl | pysbd | initials_or_name | minor | "F.J.G. Buschman" -- sentencesplit & punkt wrongly split after chained initials. |
| case_0008 | ud_ru_gsd | ru | punkt | abbreviation | minor | Russian "dr." (etc.) -- only punkt keeps the sentence whole; sentencesplit splits once. |
| case_0009 | ud_it_isdt | it | none_correct | quotation | major | Dangling open quote makes sentencesplit suppress all boundaries (0/4); punkt/syntok recover 3/4. |
| case_0010 | ud_it_isdt | it | none_correct | list_item_or_numbering | minor | Article number "867." -- sentencesplit attaches it to prior sentence; pysbd group over-splits it (closer). |
| case_0011 | golden_rules | en | none_correct | abbreviation | minor | "At 5 a.m. Mr. Smith..." -- sentencesplit wrongly splits "a.m."; punkt misses the "P.M." boundary. |
| case_0012 | ud_el_gdt | el | none_correct | under_split | minor | Greek distance list -- gold splits at colons+"chlm."; rule-based trio under-splits; punkt worst. |
| case_0013 | ud_en_gum | en | sentencesplit | over_split | minor | Colon-introduced semicolon list -- sentencesplit keeps it intact; syntok over-splits. |
| case_0014 | ud_fr_gsd | fr | sentencesplit | abbreviation | major | "...etc.) C'est a Dakhla..." -- sentencesplit sole winner; others under-split or over-split. |
| case_0015 | golden_rules | en | sentencesplit | ellipsis | major | ". . . ." ellipsis kept attached -- punkt alone shatters it into "." fragments. |
| case_0016 | ud_el_gdt | el | none_correct | abbreviation | minor | Greek "chlm."+colon list -- no library matches gold; rule-based group closest. |
| case_0017 | ud_el_gdt | el | none_correct | abbreviation | major | "Synodo E.E. - IPA" -- sentencesplit wrongly splits "E.E."; punkt keeps it intact (closest). |
| case_0018 | ud_it_isdt | it | none_correct | other | major | UD colon-fragments -- sentencesplit produces one blob (0/4); punkt/syntok recover 2/4. |
| case_0019 | ud_de_gsd | de | none_correct | over_split | major | "...Top!!! Der Fisch..." -- sentencesplit fails to split on "!!!"; punkt/syntok succeed. |
| case_0020 | ud_en_ewt | en | none_correct | parenthetical | minor | Parenthetical-as-sentence -- sentencesplit merges it; syntok captures boundary but corrupts text. |
| case_0021 | ud_en_gum | en | none_correct | other | major | GUM semicolon-per-clause + citation-attach convention -- no library matches; sentencesplit group closest. |
| case_0022 | ud_fr_gsd | fr | sentencesplit | other | major | ". promulgation" lowercase continuation -- sentencesplit splits correctly; syntok under-splits. |
| case_0023 | ud_nl_alpino | nl | none_correct | quotation | minor | Trailing closing-quote placement -- sentencesplit group misplaces (3/5); punkt 4/5 but over-splits "O.J." |
| case_0024 | ud_ru_gsd | ru | none_correct | under_split | major | "oblasti. Dohod" and "god. 2,7" -- sentencesplit group under-splits both; punkt gets one. |
| case_0025 | golden_rules | en | sentencesplit | list_item_or_numbering | minor | "1.) / 2.)" list markers -- sentencesplit keeps them attached; punkt splits them off. |
| case_0026 | ud_en_gum | en | none_correct | other | minor | Trailing "[1]" citation -- all detach it; sentencesplit group has only that error, syntok worse. |
| case_0027 | ud_es_gsd | es | none_correct | header_or_title | minor | Unmarked title + semicolon boundary -- syntok captures the semicolon; sentencesplit misses both. |
| case_0028 | ud_fr_gsd | fr | sentencesplit | quotation | major | "a la Haye »." / "islamique »." -- sentencesplit splits after guillemet+period; syntok under-splits. |
| case_0029 | golden_rules | en | sentencesplit | list_item_or_numbering | major | "1. / 2." list markers -- sentencesplit keeps them attached; punkt splits them off. |
| case_0030 | ud_el_gdt | el | none_correct | abbreviation | minor | Greek colon+"chlm." distance list -- rule-based group splits only first "chlm."; punkt 1 segment. |
| case_0031 | ud_el_gdt | el | none_correct | under_split | minor | Greek table rows -- rule-based group recovers row boundary only; punkt under-splits entirely. |
| case_0032 | ud_it_isdt | it | sentencesplit | under_split | major | "(Cattaneo). era..." lowercase continuations -- sentencesplit splits; syntok merges. |
| case_0033 | ud_it_isdt | it | sentencesplit | under_split | minor | Lowercase-initial news fragments -- sentencesplit splits all 4; syntok under-splits 2. |
| case_0034 | ud_it_isdt | it | sentencesplit | under_split | major | "Essayah. atleta" lowercase continuations -- sentencesplit splits; syntok merges. |
| case_0035 | ud_de_gsd | de | none_correct | under_split | minor | Unpunctuated "PEFERKTION" boundary -- no library detects it; syntok additionally detaches a period. |
| case_0036 | ud_en_ewt | en | sentencesplit | other | minor | "Argghhh! has..." blog-name exclamation -- sentencesplit keeps attached; punkt splits. |
| case_0037 | ud_de_gsd | de | sentencesplit | ellipsis | minor | "reserviert... An den..." sentence-final ellipsis -- sentencesplit splits; punkt merges. |
| case_0038 | ud_en_ewt | en | sentencesplit | abbreviation | major | "D.C. Circuit" -- sentencesplit keeps abbreviation attached; punkt wrongly splits. |
| case_0039 | ud_nl_alpino | nl | sentencesplit | quotation | major | Period before low opening quote -- sentencesplit splits; syntok merges. |
| case_0040 | ud_ru_gsd | ru | sentencesplit | parenthetical | minor | "(?)" editorial marker -- sentencesplit keeps the sentence whole; punkt splits at it. |
| case_0041 | ud_de_gsd | de | sentencesplit | ellipsis | minor | "fehlte... Auf Fax..." sentence-final ellipsis -- sentencesplit splits; punkt merges. |
| case_0042 | ud_en_ewt | en | sentencesplit | other | minor | Semicolon inside sentence -- sentencesplit keeps whole; syntok over-splits at ";". |
| case_0043 | ud_en_gum | en | sentencesplit | abbreviation | minor | "Gibbons et al. [4]" in parenthetical -- sentencesplit keeps attached; punkt splits "et al." |
| case_0044 | ud_es_gsd | es | sentencesplit | abbreviation | minor | "siglo XX. Nunca..." -- sentencesplit splits the true boundary; syntok merges. |
| case_0045 | ud_fr_gsd | fr | sentencesplit | list_item_or_numbering | minor | "Gdem Izik. iii)" -- sentencesplit splits before the list marker; syntok merges. |
| case_0046 | ud_nl_alpino | nl | sentencesplit | initials_or_name | minor | "O.J. en de FBI" -- sentencesplit keeps initials mid-sentence; punkt splits at "O.J." |
| case_0047 | golden_rules | en | sentencesplit | abbreviation | major | "Mt. Fuji" -- sentencesplit keeps attached; punkt splits after "Mt." |
| case_0048 | ud_de_gsd | de | sentencesplit | under_split | minor | "sowieso. biene maja..." lowercase continuation -- sentencesplit splits; syntok merges. |
| case_0049 | ud_en_ewt | en | sentencesplit | under_split | major | "last century. em ... no ..." lowercase continuation -- sentencesplit splits; syntok merges+corrupts. |
| case_0050 | ud_en_gum | en | sentencesplit | quotation | minor | "experiences?” Respondents..." -- sentencesplit splits after closing curly quote; punkt merges. |
| case_0051 | ud_es_gsd | es | sentencesplit | abbreviation | minor | "sus ex. Se basa..." -- "ex" is a noun, true boundary; sentencesplit splits; pysbd/pragmatic merge. |
| case_0052 | ud_fr_gsd | fr | sentencesplit | quotation | minor | "« negocier ». Son destin..." -- sentencesplit splits after guillemet; syntok under-splits. |
| case_0053 | ud_nl_alpino | nl | sentencesplit | quotation | minor | "Erwin de Vries. ,,Een beeld..." -- sentencesplit splits before low opening quote; syntok merges. |
| case_0054 | golden_rules | en | sentencesplit | abbreviation | minor | "the U.S. How about you?" -- sentencesplit splits the dual-duty period; punkt under-splits. |
| case_0055 | ud_de_gsd | de | sentencesplit | under_split | minor | "verwundert hat. das sind..." lowercase continuation -- sentencesplit splits; syntok merges. |
| case_0056 | ud_el_gdt | el | punkt | abbreviation | major | Greek "m.Ch." (A.D.) -- only punkt keeps it; sentencesplit splits into 3 fragments (missing abbreviation). |
| case_0057 | ud_en_ewt | en | none_correct | other | minor | UD colon-as-terminator list entry -- no library splits; sentencesplit group is the clean representative. |
| case_0058 | ud_en_gum | en | sentencesplit | abbreviation | minor | "Op. 46" opus abbreviation -- sentencesplit keeps attached; punkt/syntok split off "46." |
| case_0059 | ud_fr_gsd | fr | pysbd | under_split | minor | "ouvert. 19h15." -- sentencesplit fails to split before digit-initial time stamp; pysbd/pragmatic/punkt succeed. |
| case_0060 | ud_nl_alpino | nl | sentencesplit | under_split | minor | "ziek thuis zit. Het concern..." -- sentencesplit splits; syntok merges. |
| case_0061 | golden_rules | en | sentencesplit | parenthetical | major | "(...engineer.) at the local University." -- sentencesplit keeps one sentence; punkt splits in-paren period. |
| case_0062 | ud_de_gsd | de | sentencesplit | whitespace_or_formatting | minor | "spartanisch.Das" run-together -- gold keeps as one; sentencesplit matches gold; syntok splits. |
| case_0063 | ud_el_gdt | el | sentencesplit | other | minor | Greek question mark (U+037E) -- sentencesplit splits; punkt fails to recognize it. |
| case_0064 | ud_en_gum | en | sentencesplit | abbreviation | minor | "e.g." abbreviation -- sentencesplit keeps attached; punkt splits after it. |
| case_0065 | ud_fr_gsd | fr | none_correct | under_split | minor | Semicolon-as-terminator + lowercase continuation -- each library gets one of two boundaries; sentencesplit misses the semicolon. |
| case_0066 | golden_rules | en | sentencesplit | url_or_email | minor | "Jane.Doe@example.com. I sent..." -- sentencesplit splits only the true boundary; syntok under-splits. |
| case_0067 | ud_el_gdt | el | sentencesplit | other | minor | Greek erotimatiko ";" question mark -- sentencesplit splits; punkt merges. |
| case_0068 | ud_ru_gsd | ru | punkt | abbreviation | minor | "QA. Kod..." acronym+period boundary -- only punkt splits; sentencesplit treats "QA." as non-terminal. |
| case_0069 | ud_ru_gsd | ru | punkt | abbreviation | minor | Russian "Sr." (cf.) -- only punkt keeps attached; sentencesplit splits (missing abbreviation). |
| case_0070 | ud_es_gsd | es | syntok | other | minor | Semicolon-joined UD sentences -- only syntok splits at ";"; sentencesplit merges (defensible). |
| case_0071 | ud_ru_gsd | ru | punkt | under_split | minor | "Shveycarii. V 1932..." -- sentencesplit under-splits; only punkt splits (empty "()"+dash suppressed boundary). |
| case_0072 | ud_en_ewt | en | punkt | ellipsis | minor | "slides....they" run-on -- sentencesplit splits a false boundary; punkt/syntok keep attached. |
| case_0073 | ud_es_gsd | es | punkt | abbreviation | minor | "N.E.Br., es..." botanical author -- sentencesplit splits a stray fragment; punkt/syntok keep intact. |
| case_0074 | ud_nl_alpino | nl | punkt | quotation | minor | Trailing closing quote -- only punkt keeps it attached; sentencesplit emits a lone quote fragment. |
| case_0075 | ud_de_gsd | de | punkt | whitespace_or_formatting | minor | "ignoriert!!! Bei..." -- sentencesplit fails to re-split after "!!!"; punkt/syntok split. |
| case_0076 | ud_en_ewt | en | sentencesplit | other | minor | Text-fidelity only -- sentencesplit byte-identical to gold; syntok mangles "doesn't"->"doesnot". |
| case_0077 | ud_es_gsd | es | syntok | other | minor | Semicolon-as-boundary UD artifact -- only syntok splits at ";"; sentencesplit merges (defensible). |
| case_0078 | legal | en | sentencesplit | abbreviation | minor | "Art. I, sec.8, cl. 8." citation -- sentencesplit sole winner keeping citation intact; all others break it. |
| case_0079 | wikipedia_ru | ru | none_correct | abbreviation | major | "angl. Moscow, nem. Moskau..." -- sentencesplit splits 3 false boundaries on abbreviations; punkt fewer errors. |
| case_0080 | gutenberg | en | punkt | quotation | major | Multi-sentence quotation -- sentencesplit suppresses all interior boundaries (1 blob); punkt/syntok split correctly. |
| case_0081 | legal | en | pysbd | abbreviation | minor | "sec.107." citation + "Pp. 21-35." -- pysbd/pragmatic get both; sentencesplit under-splits "sec.107." |
| case_0082 | wikipedia_de | de | sentencesplit | decimal_or_number | major | "14. Maerz / 18. April" ordinal-day -- sentencesplit keeps attached; syntok splits the parenthetical apart. |
| case_0083 | wikipedia_en | en | sentencesplit | parenthetical | major | "thymine (T), ... uracil (U)." inline symbols -- sentencesplit keeps attached; pragmatic_segmenter over-splits. |
| case_0084 | wikipedia_es | es | tie | whitespace_or_formatting | major | Period + U+200B reference marker -- sentencesplit (and 3 others) split correctly; punkt blocked by invisible char. |
| case_0085 | gutenberg | en | sentencesplit | quotation | major | "Oh dear! Oh dear!" embedded exclamations -- sentencesplit keeps one sentence; punkt/syntok over-split. |
| case_0086 | wikipedia_de | de | sentencesplit | decimal_or_number | major | "14. Maerz / 50. Geburtstag" ordinals -- sentencesplit keeps attached; syntok splits. |
| case_0087 | wikipedia_de | de | sentencesplit | under_split | minor | "Kontakt. 1940" / "scheiterten. 1942" -- sentencesplit splits before year-initial sentences; syntok merges. |
| case_0088 | wikipedia_fr | fr | sentencesplit | parenthetical | minor | "Paris (/pa.Ki/ )" IPA parenthetical -- sentencesplit keeps attached; syntok splits subject off. |
| case_0089 | wikipedia_it | it | sentencesplit | quotation | minor | Period inside guillemet register quote -- sentencesplit keeps quote unified; punkt/syntok split inside it. |
| case_0090 | wikipedia_nl | nl | sentencesplit | initials_or_name | minor | "graaf Willem IV. Spoedig..." -- sentencesplit splits the true boundary; syntok treats "IV." as initial. |
| case_0091 | wikipedia_en | en | sentencesplit | parenthetical | major | "five prime end (5' )" inline parenthetical -- sentencesplit keeps one sentence; syntok over-splits. |
| case_0092 | wikipedia_es | es | pragmatic_segmenter | whitespace_or_formatting | trivial | Trailing U+200B -- sentencesplit emits phantom 6th fragment; pragmatic/syntok drop it; punkt under-splits. |
| case_0093 | wikipedia_fr | fr | sentencesplit | under_split | minor | "« haussmannien ». Il est..." -- sentencesplit splits after guillemet+period; syntok under-splits. |
| case_0094 | wikipedia_ru | ru | sentencesplit | under_split | minor | "centr. Moskovskiy Kreml..." -- sentencesplit splits; punkt under-splits (merges 1+2). |
| case_0095 | gutenberg | en | punkt | abbreviation | minor | All-caps "CO." (Company) imprint -- only punkt keeps attached; sentencesplit splits (case defeats abbreviation lookup). |
| case_0096 | legal | en | sentencesplit | quotation | minor | "as a woman.” Each employee..." -- sentencesplit splits after closing curly quote; punkt under-splits. |
| case_0097 | wikipedia_en | en | sentencesplit | abbreviation | minor | "(lit. 'Roman Peace')" -- sentencesplit keeps attached; punkt splits after "lit." |
| case_0098 | gutenberg | en | sentencesplit | quotation | minor | "personal love.” This distinction..." -- sentencesplit splits after closing quote; punkt under-splits. |
| case_0099 | legal | en | sentencesplit | ellipsis | major | Spaced ". . ." + "U. S. C." + "Pp. 4-12." -- sentencesplit gets all 3 sentences; syntok & punkt err. |
| case_0100 | wikipedia_de | de | sentencesplit | under_split | minor | "bezeichnet wird. 1915 publizierte..." -- sentencesplit splits before year-initial sentence; syntok merges. |
| case_0101 | wikipedia_en | en | punkt | abbreviation | major | "Washington, D.C. Justices..." dual-duty period -- only punkt splits the true boundary; sentencesplit merges. |
| case_0102 | gutenberg | en | sentencesplit | quotation | minor | "I deduce it." mid-quotation period -- sentencesplit keeps quote balanced (one segment); punkt/syntok split, dangling quote. |
| case_0103 | legal | en | sentencesplit | abbreviation | major | "Los Angeles Dept. of Water..." -- sentencesplit keeps citation intact; punkt splits after "Dept." |
| case_0104 | wikipedia_de | de | sentencesplit | decimal_or_number | major | "im 17. Jahrhundert" ordinal -- sentencesplit keeps attached; syntok splits after "17." |
| case_0105 | wikipedia_en | en | sentencesplit | abbreviation | minor | "(see, e.g. Old Supreme Court Chamber)" -- sentencesplit keeps attached; punkt splits after "e.g." |
| case_0106 | gutenberg | en | punkt | quotation | major | Multi-sentence Holmes quotation -- sentencesplit returns one blob; punkt splits all 4; syntok over-splits ";". |
| case_0107 | legal | en | sentencesplit | abbreviation | minor | "Pp. 15-33." page citation -- sentencesplit keeps attached; punkt/syntok split after "Pp." |
| case_0108 | wikipedia_de | de | sentencesplit | parenthetical | minor | "Kreuzberg (). Die groesste..." empty paren -- sentencesplit splits; syntok merges. |
| case_0109 | wikipedia_en | en | sentencesplit | abbreviation | minor | "(e.g. purple bacteria)" -- sentencesplit keeps attached; punkt splits after "(e.g." |
| case_0110 | gutenberg | en | punkt | quotation | minor | "process. And yet..." inside open quotation -- sentencesplit merges two declaratives; punkt/syntok split (ambiguous). |
| case_0111 | legal | en | sentencesplit | abbreviation | minor | "Pp. 16-23." page citation -- sentencesplit keeps attached; punkt/syntok split after "Pp." |
| case_0112 | wikipedia_en | en | sentencesplit | abbreviation | minor | "lit. \"goddess of the sky\"" parenthetical -- sentencesplit keeps attached; punkt splits after "lit." |
| case_0113 | gutenberg | en | none_correct | header_or_title | trivial | Flattened table of contents -- no library recovers heading units; sentencesplit internally inconsistent. |
| case_0114 | legal | en | sentencesplit | abbreviation | minor | "Pp. 23-33." page citation -- sentencesplit keeps attached; punkt/syntok split after "Pp." |
| case_0115 | wikipedia_es | es | sentencesplit | other | major | Semicolon clause-list + U+200B boundary -- sentencesplit produces correct 2 sentences; syntok over-splits, punkt under-splits. |
| case_0116 | wikipedia_de | de | punkt | decimal_or_number | major | "des 19. und fruehen 20. Jahrhunderts" -- sentencesplit splits ordinal periods; only punkt keeps them. |
| case_0117 | wikipedia_es | es | pragmatic_segmenter | whitespace_or_formatting | trivial | Trailing U+200B -- sentencesplit emits phantom 4th fragment; pragmatic/syntok drop it; punkt under-splits. |
| case_0118 | wikipedia_es | es | pragmatic_segmenter | whitespace_or_formatting | minor | Trailing U+200B -- sentencesplit emits phantom 4th fragment; pragmatic/syntok drop it; punkt under-splits. |
| case_0119 | wikipedia_es | es | pragmatic_segmenter | whitespace_or_formatting | minor | Trailing U+200B -- sentencesplit emits phantom 4th fragment; pragmatic/syntok drop it; punkt under-splits. |
| case_0120 | wikipedia_es | es | pragmatic_segmenter | whitespace_or_formatting | minor | Trailing U+200B -- sentencesplit emits phantom 3rd fragment; pragmatic/syntok drop it; punkt under-splits. |
