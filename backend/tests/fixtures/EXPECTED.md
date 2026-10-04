# Ground truth for fixtures (captured 2026-10-03)

Source: https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html
Fixtures: `gr_180046_2009.html` (92,551 B), `apr2009.html` (39,467 B), `sample_case.pdf` (185,005 B)

## VERIFIED from the real HTML (Phase 0 script output)
| Field | Value | How verified |
|---|---|---|
| G.R. no. | 180046 | body text "G.R. No. 180046" |
| `<title>` tag | `G.R. No. 180046` (NOT the case title) | regex on `<title>` |
| Decision date | April 2, 2009 | text after "G.R. No. 180046" |
| Court body | EN BANC | text match |
| Ponente | CARPIO (header "D E C I S I O N CARPIO, J.:"; signed ANTONIO T. CARPIO) | text match |
| Disposition | GRANTED ("WHEREFORE, we GRANT the petition and the petition-in-intervention. We DECLARE Executive Order No. 566 and CHED Memorandum Order No. 30, series of 2007 VOID for being unconstitutional.") | text match |
| Case title (body) | "REVIEW CENTER ASSOCIATION OF THE PHILIPPINES, Petitioner, vs. EXECUTIVE SECRETARY EDUARDO ERMITA and COMMISSION ON HIGHER EDUCATION represented by its Chairman ROMULO L. NERI, Respondents. ..." | text match |
| Footnote markers `name="rntN"` | 42 (N = 1..42, contiguous) | regex |
| Footnote notes `name="fntN"` | 42 (N = 1..42, contiguous) | regex |
| Month index `apr2009.html` | 140 unique `gr_*.html` links; includes `gr_180046_2009.html` | regex |

## CORRECTIONS to earlier statements
- Earlier "110 footnotes" and "~55 footnotes" were WRONG. Verified decision footnotes = **42**.
- Total `name=` anchors in file = 110, so ~26 other anchors exist. Not yet explained (likely the separate opinion below). Resolve in Phase 4.

## KEY STRUCTURE FACT
The same HTML page contains the decision AND a separate concurring opinion by Justice BRION (starts after the footer text "The Lawphil Project - Arellano Law Foundation" at ~char 43,646 of 76,731 extracted text chars). Parser must split the page into decision vs separate opinion(s), not treat the whole page as one document.

## sample_case.pdf (verified earlier from text extraction)
- 5 pages, Google Docs export, 3,669 words.
- Exactly one citation line (appears twice): `Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)`.
- Claimed year 2010 vs official 2009 -> MISMATCH expected.
- Contains `​` zero-width chars and watermark leftovers `1awphi1` / `1avvphi1`.
- Official Lawphil text does NOT contain "538 SCRA" or "583 SCRA": SCRA cite cannot be verified from Lawphil, so the matcher must not check it.

## Added in Phase 6/7 (regression fixtures, fetched 2026-10-03 from the April 2009 index)
Read from the raw HTML, not from the parser:
| File | Facts |
|---|---|
| `gr_173931_2009.html` | April 2, 2009; ponente TINGA; 60 footnote anchors 1-60 where `fnt6` is EMPTY (`<a name="fnt6"></a>`); body says "Republic Act (R.A.) No. 7722" |
| `gr_183905_2009.html` | April 16, 2009; SECOND DIVISION; `<title>` is "G.R. No. 183905 & 184275"; 72 footnotes; ruling spans paragraphs ("... G.R. No. 184275 is EXPUNGED ... G.R. No. 183905 is DISMISSED"); footnote 34 = "Citing Turquenza v. Hernando, et al., G.R. No. 51626, 30 April 1980." |
| all three decisions | end with a boilerplate CERTIFICATION citing Article VIII, Section 13; it appears nowhere else in body or footnotes |
| GR 180046 signature | 13 concurring justices in a `<table>` (PUNO ... PERALTA), listed in `tests/unit/test_insights.py` |

Lawphil URL facts verified live: all 12 month codes jan..dec work; old cases are `gr_l-10854_1960.html`; consolidated `gr_l-12091-92_1960.html`.

## NOT yet verified (do not assert in tests until checked)
- Exact footnote count inside the separate opinion.
- Division/doc_type handling for resolutions and opinions.
- Old-style `L-12345` G.R. filenames on Lawphil.
- Lawphil Terms of Use. E-Library search behavior.

## Environment facts (Phase 0)
- Docker 29.8.1, Compose v5.5.1, daemon running, Python 3.13.7.
- Host port 5432 IN USE (container `rideflow-postgres-1`, another project), 6379 IN USE (host redis), 6380 used by `rideflow-redis-1`. Port 8000 free.
- This project must NOT reuse or touch those. Use host ports 5434 (postgres), 6381 (redis), 8000 (api).

## Joint decisions (added with the catalog; read from the real pages)
- `gr_211972_2015.html` (July 22, 2015, First Division): caption prints `G.R. No. 211972 July 22, 2015`, then the first party block,
  `x - - - x`, then a separate line `G.R. No. 212045` and the second party block, then `D E C I S I O N`. Numbers: 211972, 212045.
- `gr_148263_2009.html` (April 21, 2009, First Division): one line `G.R. Nos. 148263 and 148271-72 April 21, 2009`. Numbers: 148263, 148271, 148272.
