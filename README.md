# CaseLens

**A web app that turns a law student's reviewer into a finished, checked, case-by-case digest.**

Upload a reviewer (PDF or Word). CaseLens finds every Philippine Supreme Court case it cites, gets the real decision from [Lawphil](https://lawphil.net), checks the student's citations against the Court's record, and builds a **digest box** for each case: Facts, Issue, Ruling, Doctrine, and short explanations. The student edits anything and downloads a Word file.

> For information only. CaseLens gives no legal advice. Lawphil gives no warranty that its text is complete or correct: confirm with the Supreme Court.

---

## Why it exists

Law students write **reviewers**: study notes that cite Supreme Court cases by G.R. number. For every case they search the decision, read it, copy the Facts, Issue, Ruling and Doctrine, paste them into a box, and ask an AI chat tool to explain it. That is about **15 minutes per case**, repeated for 10 to 20 cases, with two risks: a wrong citation nobody checks, and an AI answer that says something the decision does not say.

CaseLens does the repeating work and keeps the law accurate:

- It **shows the source** of everything, with a link to the official page.
- It **never guesses**. If something is missing, it says so and asks the student.
- The **student decides**. The app suggests and checks. The student edits.

## Features

| | |
|---|---|
| **Search** | Find a decision by case name or G.R. number (1987 onward) in about 1 to 37 ms. |
| **Check a reviewer** | Finds each cited case and compares it with the Court's record (for example: "You wrote 2010; the Court's record says 2009"). |
| **Finished reviewer** | One digest box per cited case. A switch shows the whole reviewer text with each box after its paragraph. |
| **Court's own words** | Facts and Issue come from the Court's own headings. The Ruling is the paragraphs before the last `SO ORDERED`. The Doctrine is picked or pasted by the student. Nothing is reworded. |
| **Explanations in plain words** | "Topic explained", "Why this case matters" and any question the student adds. Written by Gemini from the decision, then checked twice. Marked "Drafted from the decision. Check it." |
| **Edit everything** | Type, paste, pick paragraphs of the decision, put the original back, or write an answer again. |
| **Word download** | The reviewer with the digest boxes inside, as a `.docx`. A Word upload keeps its own layout. A PDF is rebuilt as a new Word file. |
| **Download the full case** | For a student who is not happy with a digest: one Word file per case, or every case a review cites in one file. The Court's own text, footnotes and opinions, nothing reworded, with the official link. |
| **Case library** | Saved cases with their footnotes, and facts read from each decision (ruling, justice, laws and cases cited). |
| **Guide** | A "How to use it" page for first-time students, and a short welcome card on the start page. |

## How the AI is kept honest

The AI only writes explanations. It never writes Facts, Issue, Ruling or Doctrine. Every AI sentence passes:

1. **Writer** (Gemini) writes sentences and names the decision paragraphs each one uses.
2. **Code check:** the paragraphs must exist, every number must be in the cited paragraph, every name must be in the decision.
3. **Checker** (a second Gemini model) must say "supported". Anything else is dropped.
4. If nothing is left, the field stays empty and says why.

On 8 real decisions, 43 of 48 drafted sentences were kept and a person read every one against the decision text: none was unsupported.

## Tech stack

| Part | Tools |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic |
| Database | PostgreSQL 16 (`pg_trgm` for fast name search) |
| Background jobs | RabbitMQ and Dramatiq (two workers: Lawphil jobs, AI jobs) |
| AI | Google Gemini (explanations only) |
| Reading and writing files | PyMuPDF (PDF), python-docx (Word), selectolax and httpx (Lawphil pages) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, shadcn/ui, TanStack Router, Query, Form and Table |
| Serving | nginx (web app and `/api` proxy) |
| Run | Docker Compose |
| Tests | pytest, Vitest and Testing Library with MSW, Playwright, axe-core |

The backend follows **Clean Architecture** (domain, application, infrastructure, presentation) with SOLID design, so tools such as the queue or the AI can be swapped in one place.

## Quick start

You need Docker. Python and Node are only needed for development.

```bash
cd backend
cp .env.example .env              # put your GEMINI_API_KEY in .env (optional: digests work without it)
docker compose up -d --build
```

| What | Address |
|---|---|
| Web app | http://localhost:8080 |
| API and docs | http://localhost:8000 and http://localhost:8000/docs |
| RabbitMQ page | http://localhost:15675 (login `caselens` / `caselens`, development only) |
| Database | `localhost:5434` |

Port 8000 busy? Run `API_PORT=8002 docker compose up -d`.

**First search:** the app copies Lawphil's monthly list of decisions (1987 to now, about 34,000 decisions). It takes about 9 minutes, once, in the background. The first search starts it, or run:

```bash
docker compose exec api python -m caselens.manage catalog build
```

### Development

```bash
# backend tests (needs the db container running)
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
pytest -m "not live"

# frontend with hot reload (proxies /api to http://localhost:8000)
cd frontend && npm install && npm run dev      # http://localhost:5173
npm test                                       # unit and component tests
npm run e2e                                    # browser tests (needs the stack running)
```

`pytest -m live` calls the real Lawphil site (slow, optional). The AI quality check is `python -m tests.eval.run_answer_eval` (costs a few cents).

## Project layout

```
backend/
  caselens/
    domain/            rules and data shapes (no outside tools)
    application/       use cases and ports (interfaces)
    infrastructure/    PostgreSQL, Lawphil, RabbitMQ, Gemini, Word files
    presentation/api/  FastAPI routes
  alembic/             database migrations
  tests/               tests and real saved Lawphil decisions
frontend/
  src/                 routes, features, API layer, wording (lib/copy.ts)
  e2e/                 Playwright tests
docs/
  TECHNICAL_DOC.md     how the app works, with flows (start here)
  BACKEND_NOTES.md     backend notes and commands
```

## Documentation

- **[docs/TECHNICAL_DOC.md](docs/TECHNICAL_DOC.md)**: what the app is about, the flows, the AI checks, jobs, database, API, limits.
- **[docs/DEPLOYMENT_PLAN.md](docs/DEPLOYMENT_PLAN.md)**: deployment plan (Vercel web app, Render API, Supabase database; free mode and paid workers mode).
- **[docs/BACKEND_NOTES.md](docs/BACKEND_NOTES.md)**: backend notes, commands and known limits.
- **[frontend/PRODUCT.md](frontend/PRODUCT.md)**: who the app is for and the product principles.

## Known limits

- The searchable list starts in **1987**. Older cases need the year or the Lawphil link.
- A **scanned** (picture-only) PDF cannot be read.
- If an uploaded file **already contains digests** the student wrote, the app keeps them, adds its own box and shows a notice.
- Not built yet: A.M. and A.C. cases, the Supreme Court E-Library, user accounts.
- This is an **internal tool**: no login yet. Change the development passwords and add accounts before real use.

## Data source and permission

All case text comes from Lawphil (Arellano Law Foundation). CaseLens reads at most 1 page per second and keeps a copy of what it downloads. Lawphil's terms neither forbid nor allow automated access, so **ask the Arellano Law Foundation for written permission** (https://lawphil.net/contactus.html) before real use. There is no software license yet.
