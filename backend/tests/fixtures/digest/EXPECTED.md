# Digest fixtures: where the Facts, Issues and final ruling are

26 decisions downloaded from lawphil.net on 2026-10-03, one picked at random per year from the catalog
(1988 to 2025; every third year skipped to keep the set at a size that can be read by hand), plus the 5 decisions
already in `tests/fixtures/` (GR 148263, 173931, 180046, 183905, 211972). `MANIFEST.txt` lists the 26 and `fetch.py`
downloads them again (1 request per second).

Paragraph numbers are positions in `Case.full_text.split("\n")` (0-based, ends included). The values in
`tests/unit/test_digest_structure.py` were read by hand from the pages, not produced by the code under test.

## What the real pages showed

- **The Court's headings vary.** Seen: The Case, The Facts, The Antecedent Facts, Antecedents, The Antecedents,
  The Facts and Antecedent Proceedings, The Issue, The Issues, Issue, Issues, The Issue Before the Court,
  The Issues Before the Court, Ruling of the Court, The Court's Ruling, Our Ruling, The Ruling of this Court.
- **No Facts heading in 18 of 31, no Issues heading in 21 of 31.** Mostly decisions before 2005, but also
  GR 161425 (2016), 172846 (2013), 174941 (2012), 240774 (no Issues heading). Those are the ones an AI has to pick (D2), shown as "Suggested".
  Facts without a heading but with an inline lead-in ("The facts are as follows:") are NOT treated as headed.
- **A decision quotes lower-court rulings.** GR 260071, 272689, 165678, 148263 print the RTC's and the CA's
  `WHEREFORE ... SO ORDERED` before the Court's own. The Court's ruling is the paragraphs before the LAST
  `SO ORDERED`.
- **The ruling does not always open with WHEREFORE.** `ACCORDINGLY` (GR 221664, 260071, 272689) and
  `IN VIEW OF THE FOREGOING` (GR 89967). The old finder returned nothing for 221664 and 89967, and the CA's
  paragraph for 260071 and 272689.
- **A section can be long.** GR 180046's Facts (9-62) include the full text of the executive order the Court quotes,
  because the Court's next heading is "The Issues". The digest must cap what it shows, not move the boundary.
- **Newer layout (from about 2016).** `[ G.R. No. 161425. November 23, 2016 ]`, `PETITIONERS, VS. ... RESPONDENTS.`,
  plain `DECISION`, footnote marker `<a class="nt">1</a>` with no anchor. The parser could not read 5 of these
  (GR 161425, 196510, 221664, 240774, 272689); fixed in parser version 5.

## Known gaps in the existing parser (not part of the digest, not fixed here)

- Before about 2000 there is no "D E C I S I O N" line, so the ponente is not read (10 of the 31).
- GR 175483 and 233850 print the date on its own line before the G.R. number, so `decision_date` is empty.
- (Fixed by the new ruling finder: GR 119935 and 89967 used to give disposition UNKNOWN; none of the 31 does now.)
