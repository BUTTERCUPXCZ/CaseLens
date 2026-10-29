# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Law students in the Philippines who write and study **reviewers**: study notes that cite Supreme Court cases by G.R. number, usually a PDF or Word file. They are not technical. Today, for every case, they google it, open Lawphil, read a long decision, copy the Facts, Issue, Ruling and Doctrine into a box, and ask a general AI chat tool to explain it: about 15 minutes per case, 10 to 20 cases per reviewer, with nobody checking the citation or the AI's answer.

Devices: laptop first, at a desk or library; a phone must still work.

This surface (the landing page) is also shown in the developer's portfolio, so recruiters and clients see it too. They are a secondary audience: the page is written for students.

## Product Purpose

CaseLens does the repeating case work and keeps the law accurate. A student looks up one case (**Individual**: a case name or G.R. No.) or uploads many (**Bulk**: PDF or Word files, or pasted G.R. numbers) and answers "What subject?". CaseLens gets the official decision from **Lawphil**, or from the **Supreme Court E-Library** when Lawphil does not have it, files it under a subject in the **Case library** (one row per main case; a Resolution, a repeat or a cited case is never a second row), and writes a **case digest** in the client's format:

- Doctrine, Facts (with each side's arguments), Issue, Ruling, Ratio Decidendi, Dissents, Topic Explained, Why This Case Matters, and a one-paragraph Case Summary.
- Downloadable as Word in three sizes: Case Summary and Doctrine; Doctrine, Facts, Issue, Ruling (1 to 2 pages); the full case digest (about 6 pages).
- Plus "Download the full case": the Court's own text, footnotes and opinions as one Word file, nothing reworded.

The student can rewrite any digest section within an upload, put the AI version back, and ask their own questions about a case (answered from the decision, with paragraph cites).

Also available as a **desktop app for Windows** that runs on the student's own computer and updates itself.

## Positioning

The AI writes the digest, and **every sentence is tied to the paragraphs of the decision it rests on and checked**:

1. The writer AI writes sentences and names the paragraphs each one uses.
2. Code sorts every sentence: a paragraph that does not exist, or a number or name the decision never mentions, fails at once; a suspicious sentence (a number or name not in the cited paragraph, "always"/"only", a party's argument written as the Court's holding) goes to the checker. Key sentences always go to the checker.
3. A second AI call, shown each sentence and only its cited paragraphs, must say "supported".
4. What fails is rewritten once from its own paragraphs and checked again; what still fails is dropped.
5. If Doctrine, Facts, Issue or Ruling ends up empty, the digest is marked failed ("Try again"), never shown as finished.

Every digest is marked "Drafted from the decision. Check it." A general AI chat tool cannot make this claim.

Measured (README): on 8 real decisions, 43 of 48 drafted sentences were kept and a person read every one against the decision text: none was unsupported. A plain digest costs 2 AI calls; a case digested before costs none.

## Operating Context

- Sources: Lawphil (lawphil.net, Arellano Law Foundation) and the SC E-Library (elibrary.judiciary.gov.ph). Read at most 1 page per second, with a saved copy kept.
- Search covers decisions from 1987 onward (about 35,000), and finds a case in milliseconds from a local copy of Lawphil's monthly lists.
- A digest takes about 2 minutes to write. Students can keep working meanwhile.
- The website has no accounts; it may be behind an access code.

## Capabilities and Constraints

- Not built: A.M. and A.C. cases, user accounts, sharing.
- A scanned (picture-only) PDF cannot be read.
- For information only; no legal advice. Lawphil gives no warranty that its text is complete or correct: confirm with the Supreme Court. Cite the E-Library as "SC E-Library"; the official printed copy prevails.
- Terminology to keep: G.R. No., ponente, En Banc, Division, decision, resolution, doctrine, digest, reviewer. Avoid system words (parse, ingest, pending, pipeline, API) in student-facing text.

## Brand Commitments

Product name **CaseLens**. Mark: the lucide `Scale` glyph in gilt beside the wordmark. The visual world is set in the app (`frontend/src/index.css`, `.impeccable/surfaces` in `frontend/`): paper work area, ink-blue spine like a bound law volume, deep ink text, gilt, a proofreader's red pen used only to strike what is wrong; Literata for case text and titles, Public Sans for the interface; hairline rules, small radius, no decorative shadows. Binding commitments: always show where data comes from; never guess; plain language; English only.

## Evidence on Hand

- Real saved decisions in `backend/tests/fixtures` (for example G.R. No. 180046, Review Center Association of the Philippines v. Ermita, April 2, 2009), with ground truth in `EXPECTED.md`.
- Measured numbers in `README.md` and `docs/TECHNICAL_DOC.md`.
- No testimonials, user counts, prices or customer logos exist; none may be invented.

## Product Principles

1. **Show the source, always.** Every case links to its official page.
2. **Never guess.** An empty answer is better than a wrong one. A sentence that cannot be tied to the decision is dropped.
3. **The student is in charge.** The app suggests and checks; the student edits.
4. **Say it plainly.**
5. **Waiting is part of the product.** Show honest progress; let the student keep working.

## Accessibility & Inclusion

Plain language is a requirement: the audience is non-technical and reads long, dense legal text. Status never relies on color alone. Keyboard operable. Respect reduced motion.
