---
version: 1
slug: "src-app-tsx"
primary_target: "src/App.tsx"
related_targets: ["src/demo/AppReplica.tsx"]
---

# Surface brief: CaseLens landing page

Scope and visitor mode: the public landing page (one page, `src/App.tsx`). Persuade.

Audience, job, action: Philippine law students who write reviewers. Job: stop spending about 15 minutes per case on lookup, copy and unchecked AI answers. Action: open a case in CaseLens (the working search box sends a case name or G.R. No. to the app's search) or "Open CaseLens". Secondary visitors: recruiters and clients from the developer's portfolio (a short "How it's built" note near the end).

Proof and content: an interactive replica of the real app playing the real flow on G.R. No. 180046 (Review Center v. Ermita, April 2, 2009), with real paragraphs from the stored decision. The only number: 43 of 48 sentences kept on 8 real decisions, none unsupported on a person's reading. No testimonials, prices, user counts or invented integrations.

Constraints: the app's tokens copied from frontend/src/index.css; shadcn + Tailwind v4; wording in src/copy.ts; reduced motion; keyboard; 320 px and up; no access code.

## Direction contract

THESIS: The landing page reads like a volume of checked case digests: chapters in the reporter's numbered outline, and every claim on the page cites its source the way a digest cites the Court's paragraphs. It refuses the split hero over a row of icon cards.

OWN-WORLD: Paper ground, ink text, one paper navbar with a hairline and a primary rule under the current part, an ink-blue closing band with gilt rules, Literata display set like a reporter's title page, Public Sans for controls, P-numbered paragraph chips, hairline rules, a red pen that only strikes what was dropped, and superscript source notes gathered at the end like a decision's footnotes.

STORY: The student sees the app turn G.R. 180046 into a checked digest, believes it because every sentence shows its paragraph and the dropped one is struck out, and opens a case.

FIRST VIEWPORT: A sticky navbar across the top holds every link (CaseLens, How it works, The check, Library, Downloads, Questions, Desktop app, Open CaseLens). Below it, the headline in Literata on the left and, on the right, the support line, the search box with Open, and "See how a sentence is checked". Under them, at full measure, the app replica in its window frame, with its step strip.

FORM: The bound volume, position 5 on my ordered list, dealt as lead by the roll. Seed seed:9a1bdfe35b9c9d2b.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Kept from declined challengers:
- HyperCard stack: every replica scene is addressable (#demo-find, #demo-check, …), and Back retraces the scenes.
- VU-meter bridge: the red pen is the only red the page allows.

## Revision log
- 2026-10-29: the user asked to remove the left spine and put all navigation in a top navbar. The volume now carries through the chapter numerals, source notes and closing band, not a spine. The hero was split (headline left, lead and search right) so the replica starts in the first screen.
- 2026-10-29: the user pinned a SaaS hero from a reference (Antimetal): a framed panel inset from the window, two guide rails 9.8% in from each side (their margins copied), the nav inside the panel, a centred headline and search, and the app replica overlapping the panel's lower edge. The whole page then followed: the rails run its full height, each part opens on a hairline with nodes at the rails, headings are centred, and content sits in ruled grids whose outer edges are the rails. A light/dark button was added; light is the default.
