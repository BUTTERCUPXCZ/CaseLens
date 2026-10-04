# Ground truth for the catalog fixtures (captured 2026-10-03, read from the raw HTML)

Each case row of a monthly list is `<tr><td>G.R. No. N<br>Date</td><td>Party <a class="vs">vs.</a> Party</td></tr>`
(newer pages, e.g. July 2015, add a third cell holding a PDF icon, so a row has 2 or 3 cells)
nested inside a wrapper table (the wrapper row contains the whole page and must not count as a case).

| File | rows with a link | G.R. rows | other kinds | notes |
|---|---|---|---|---|
| mar1987.html | 52 | 52 | none | `L-` numbers; 2 rows have no space in the date: `March 31,1987`, `March 11,1987` |
| jun1995.html | 64 | 52 | am 11, ac 1 | first G.R. row: `G.R. No. 104234`, June 30, 1995, "Air France vs. Court of Appeals, et al." |
| apr2009.html | 180 | 157 | am 20, bm 1, ac 2 | 157 rows but only **140 distinct pages** (joint decisions share one page); first row `G.R. No. 146408` April 30, 2009 "Philippine Airlines, Inc. vs. Enrique Ligan, et al." |
| jul2015.html | 138 | **119** | am 13, ac 6 | first G.R. row `G.R. No. 213104` July 29, 2015 "People of the Philippines vs. PO1 Cyril A. De Gracia" |

## Label shapes seen (must all parse)
- `G.R. No. 164785 G.R. No. 165636` (two labels in one cell) -> link `gr_164785_2009.html` -> numbers 164785, 165636
- `G.R. No. 148263 and 148271-72` -> numbers 148263, 148271, 148272
- `G.R. No. 170270 & 179411` -> 170270, 179411
- `G.R. Nos. 179240-41` -> 179240, 179241
- `G.R. No. 209353-54/G.R. Nos. 211733-34` -> 209353, 209354, 211733, 211734 (link `gr_209353_2015.html`)
- `G.R. Nos. 211972 & 212045` (link `gr_211972_2015.html`)
- Old style `G.R. No. L-28156` -> link `gr_l-28156_1987.html`

## Real inconsistencies on Lawphil's own list (do not "fix"; the list is the source)
- Row labelled `G.R. No. 155573` (Apr 24, 2009) links to `gr_154473_2009.html`.
- Row labelled `G.R. No. 181726` links to `gr_181377_2009.html` (the page of a sibling petition).
So a row's numbers come from its **label**, and the page to open comes from its **link**.

## Year pages and the master page
- year2023.html links months jan feb mar apr jun jul aug oct nov dec. May and September are named on the page too, but as `<xref="may2023/may2023.html">` (no `href`), so they are not links and must not be counted.
- year2026.html lists jan feb apr aug.
- judjuris.html links years 1901 to 2040: 54 years from 1987 on, of which 2027-2040 are in the future and must be ignored.

## Counting method (and a correction)
G.R. rows = `<a href="gr_...">G.R. ...</a>` anchors counted directly in the raw HTML (a third method, independent of the parser):
mar1987 52, jun1995 52, apr2009 157 (140 distinct hrefs), jul2015 **119**. An earlier hand count said 118 for July 2015 because the
regex assumed 2-cell rows; that count was wrong, not the parser.
