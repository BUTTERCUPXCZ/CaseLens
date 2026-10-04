# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Law students (Philippines) who write and study **reviewers**: digests and notes, usually a PDF or Word file, that cite Supreme Court cases by G.R. number. They are not technical. Main moment (confirmed): they have a reviewer and want to know whether their citations are right and to read the real case, instead of looking each one up on Lawphil by hand and copy-pasting.

Devices (confirmed): laptop first, at a desk or library; quick checks on a phone must still work.

## Product Purpose

CaseLens removes the repetitive part of case work. A student uploads a reviewer; the app finds every cited G.R. number, pulls the **official** decision from Lawphil, and tells the student plainly which citations match the Court's record and which need a look (for example: "you wrote 2010, the Court's record says 2009"). The student can then read the full official text with its footnotes, and see quick findings about a case. Success is that a student never has to visit the source site manually, and trusts what they see because it is shown with its source.

## Positioning

Checks a student's own citations against the official record and links every result back to the exact official page (and footnote), without rewording the Court's text. The only written text is the explanations a student asks for ("Topic explained", "Why this case matters"): each sentence is tied to the paragraphs of the decision it rests on, checked twice, and always marked "Drafted from the decision. Check it." A general search site or an AI summary tool does not verify the student's own document and cannot truthfully make that claim.

## Operating Context

- Input: PDF (text-based) or DOCX reviewers, up to 5 MB. Scanned image PDFs are not supported.
- Source of truth: Lawphil (lawphil.net, Arellano Law Foundation). The backend fetches on demand, throttled and cached; a first lookup can take about 30 to 60 seconds, repeat lookups are instant.
- Backend API already exists (FastAPI, PostgreSQL): uploads, case search by G.R. number, stored cases with footnotes, per-case findings, and cross-case patterns. The app is an internal tool; no accounts or login in this version.
- A G.R. number alone cannot be searched: the backend needs the year the student wrote (it tolerates a year that is off by up to 2). Without a year the student can paste the case's Lawphil link instead.

## Capabilities and Constraints

- Citation check result per citation: matches / needs a look (year, date, case name or G.R. number differs) / could not be found / could not be checked right now / still checking.
- The reporter reference (e.g. "538 SCRA 428") is **not** on Lawphil's page, so it can never be confirmed or refuted. It must be shown as "can't be checked", never as right or wrong.
- Case page content comes verbatim from the official text: ruling, who wrote and concurred, laws cited, cases cited (each linking to its footnote on Lawphil), full text with footnotes, opinions printed on the same page.
- Findings are parsed or counted from the stored text, never generated. The digest's Facts, Issue, Ruling and Doctrine are the Court's own paragraphs (or text the student pasted or picked), never reworded. Only the explanations are written by an AI service, and they are labelled as drafts. The ruling label (granted, denied, ...) is a keyword reading shown next to the verbatim ruling.
- Patterns (most-cited laws, rulings by year, most-cited cases, cases per justice) only mean something with enough cases (the backend flags fewer than 5).
- Terminology to keep: G.R. No., ponente, En Banc, Division, decision, resolution, concurring opinion. Avoid system words (parse, ingest, pending, mismatch, API).
- Not decided: user accounts, sharing a review with classmates, exporting a corrected reviewer (the finished reviewer with digest boxes IS exported as a Word file), the Supreme Court E-Library as a second source.

## Brand Commitments

Product name: **CaseLens** (working name from the backend). No logo, brand colors or typography exist yet. Binding commitments from the user: always show where data comes from; never guess; plain language; English only for now.

## Evidence on Hand

- A real sample reviewer: `~/Downloads/sample case.pdf` (5 pages, cites GR 180046 as April 2, 2010; the official decision is April 2, 2009).
- Real stored data from the running backend (cases from the April 2009 Lawphil index, with footnotes, justices and rulings).
- Lawphil's Acceptable Use Policy and Disclaimer (read 2026-10-03): informational only, no warranty of accuracy or completeness, confirm with the originating body. No testimonials, user counts or benchmarks exist; none may be invented.

## Product Principles

1. **Show the source, always.** Every result links to the official page, and to the exact footnote where one exists. The disclaimer is visible, not hidden.
2. **Never guess.** If something could not be found or checked, say so and say what the student can do next. No invented or reworded legal content. A drafted explanation is a draft: it says where it came from, which paragraphs it rests on, and invites the student to check it and change it.
3. **Say it plainly.** Plain words for status and errors; keep only the law terms students already use.
4. **Respect the student's own work.** Show "what you wrote" beside "what the Court's record says"; the student decides, the app does not overrule them.
5. **Waiting is part of the product.** Lookups take time; show honest progress and let the student keep working.

## Accessibility & Inclusion

Plain language is a requirement, not a nicety: the audience is non-technical and reads long, dense legal text. English only in this version. Status must never rely on color alone. (Further standards, such as a WCAG level, were not specified by the user.)
