---
version: 1
slug: "src-routes-root-tsx"
primary_target: "src/routes/__root.tsx"
related_targets: ["src/routes/index.tsx"]
---

# Surface brief: CaseLens app shell and screens

Scope and visitor mode: the whole app. Operate (Home, My reviews, review results, Case library, Patterns, G.R. search) with a Read surface inside it (the case page's full text).

Audience, job, action: law students in the Philippines, non-technical, laptop first (phone must work). Job: check the citations in a reviewer against the official record and read the real case. Primary action: drop a reviewer file. Success: in seconds they see which citations match and which need a look, and can open the official Lawphil page (or footnote) in one click.

Proof and content: real data from the running backend, never invented. Example that must be shown truthfully: the sample reviewer cites GR 180046 as April 2, 2010; the Court's record says April 2, 2009. Official case: 42 footnotes, 13 concurring justices, ruling in the Court's words.

Constraints: plain language (all wording in src/lib/copy.ts), English only, status never color-only, source link and the Lawphil disclaimer always reachable, shadcn/ui + Tailwind v4 tokens, TanStack Router/Query/Form/Table, keyboard operable, readable down to 375px.

Unresolved decisions: none for the first build. Not designed: accounts, sharing, export.

## Direction contract

THESIS: A citation checker that reads like a proofread reviewer. The student's own words sit beside the Court's record, and a difference is marked the way a proofreader would mark it. Refuses: the SaaS dashboard of stat tiles and same-size icon cards.

OWN-WORLD: Ink-blue shell field (the sidebar, like the spine of a bound law volume, about oklch(0.30 0.07 255)) against a paper work area (about oklch(0.975 0.008 90)), deep ink text (oklch(0.22 0.03 255)); dark theme is an ink-blue night. Status colors: matches deep green, needs a look ochre, red-pen oxblood used only for struck values, not found slate. Type: Literata for case titles and case text, Public Sans for the interface (open zeros: Atkinson Hyperlegible's slashed zero was tried first and read as a typo in dates and sizes), tabular numerals for G.R. numbers and dates. Hairline rules, small radius, no decorative shadows, footnote markers as superscript buttons.

STORY: The student understands within seconds which citations are right, believes it because every result links to the official page and footnote, and acts: corrects the year or opens the case.

FIRST VIEWPORT: Home at 1440x900. Left ink-blue rail (CaseLens, Check a reviewer, My reviews, Case library, Patterns). The first item is named for the action rather than "Home", per the plain-language commitment (PRODUCT.md): a student sees what it does. Header carries an always-visible "Find a case by G.R. number" field. Main area: one large drop target, "Drop your reviewer here" (PDF or Word, up to 10 MB) with "or choose a file", and beneath it "Your recent reviews" as plain rows ("sample case.pdf, 1 case checked, 1 needs a look"). The drop target is the primary action.

FORM: User-pinned direction ("Calm library", refined with the user to "The proofread reviewer", signature move: red-pen corrections, struck value beside the Court's value). Not rolled; no concept-seed run. Seed key: pinned-by-user. Position on the ordered list: not applicable.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance


## Revision log
- Interface face changed from Atkinson Hyperlegible Next to Public Sans after the independent finish review (slashed zero cannot be switched off in that face). Dark theme sidebar lifted lighter than the work area so the spine stays distinct.
