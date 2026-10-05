# CaseLens: Technical Document

Simple guide to how the app is built and how it works.

---

## 1. What is CaseLens about?

### 1.1 The short idea

CaseLens is a web app for **law students in the Philippines**. It saves them from the slow, boring work of looking up Supreme Court cases and copying them into their study notes. The student gives the app their notes. The app finds the real cases, checks the student's work, and builds the case summaries for them. The student then reads, fixes, and downloads the result.

### 1.2 Who uses it and why

Law students write **reviewers**. A reviewer is a set of study notes, usually a Word or PDF file. It explains a topic of law, for example "Legislative Department, Article VI of the 1987 Constitution". Inside the reviewer, the student mentions **Supreme Court cases** that explain or prove each point. A case is named by its **G.R. number** (for example "G.R. No. 180046") and often by its name and date (for example "Review Center v. Ermita, April 2, 2010").

For each case, a good reviewer has a small **digest**. A digest is a short summary box. It usually has:

- **Facts**: what happened.
- **Issue**: the legal question the Court had to answer.
- **Ruling**: what the Court decided.
- **Doctrine**: the rule of law the case teaches.
- **Topic explained** and **Why this case matters**: short notes in the student's own plain words.

### 1.3 The problem (how students work today)

A reviewer can cite 10, 20, or more cases. For **each** case, a student does this by hand:

1. Search the case on Google.
2. Open the case on lawphil.net (a free website of Supreme Court decisions).
3. Read a long decision (often many pages).
4. Copy the Facts, the Issue, the Ruling, and the Doctrine one by one.
5. Paste them into a box in the reviewer.
6. Ask an AI chat tool to explain the topic and why the case matters, then paste that too.
7. Repeat for the next case.

This takes about **15 minutes per case** and it is the same work every time. There are also two risks:

- **Wrong citations.** The student may write the wrong year or the wrong name (for example "2010" when the Court's record says "2009"). Nobody checks.
- **Wrong AI answers.** A general AI chat tool can say things the decision does not say. For law, a wrong sentence is a real problem.

### 1.4 What CaseLens does instead

The student uploads the reviewer (PDF or Word). Then, with no extra clicks:

1. **Reads the file** and finds every cited case.
2. **Gets the real decision** from lawphil.net for each case, and keeps a copy.
3. **Checks the citation.** It compares what the student wrote with the Court's record. If they differ, it says so in plain words ("You wrote 2010; the Court's record says 2009"). The app does not change the student's text. The student decides.
4. **Builds a digest box** for each case:
   - Facts and Issue: the Court's own words, taken from the Court's own headings.
   - Ruling: the Court's own final paragraphs.
   - Doctrine: the student picks the paragraph, or pastes their own. The app does not guess it.
   - Topic explained and Why this case matters: a short explanation written by an AI from the decision, and checked (see section 6).
5. **Puts each box in the right place**, right after the paragraph that cites the case.
6. **Lets the student change anything**: type, paste, pick other paragraphs of the decision, or put back the first version. The student can also ask their own question about a case.
7. **Gives a Word file** to download, with the digest boxes inside.

A student can also **search** any decision by name or G.R. number (from 1987 onward) and read it with its footnotes. This works fast because the app keeps its own copy of Lawphil's list of decisions.

### 1.5 A simple example

A student uploads a reviewer with one line: *"See Review Center v. Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)."*

- The app finds "GR no 180046" and gets the decision from Lawphil.
- It shows: **"Needs a look: you wrote 2010, the Court's record says 2009."** and links to the official page.
- In the **Finished reviewer** tab, a digest box appears right under that line:
  - **Facts:** the Court's first paragraphs about the nursing exam leak.
  - **Issue:** "Whether EO 566 is an unconstitutional exercise by the Executive of legislative power…"
  - **Ruling:** "WHEREFORE, we GRANT the petition… We DECLARE Executive Order No. 566… VOID…"
  - **Doctrine:** empty, with buttons to pick or paste.
  - **Topic explained** and **Why this case matters:** short points marked *"Drafted from the decision. Check it."*, each with the paragraph numbers it is based on.
- The student picks the doctrine paragraph, rewrites one explanation, and clicks **Download as Word**.

### 1.6 What CaseLens is NOT

- It is **not a lawyer** and gives **no legal advice**.
- It does **not rewrite or shorten the Court's words**. Facts, Issue, Ruling, and Doctrine are always exact copies of the decision (or the student's own text, clearly marked).
- It does **not replace reading the case**. It helps the student read and organize faster.
- It does **not guess**. If something is missing (for example the Court did not label the facts), the app says so and asks the student to choose.
- It is **not a general AI chat**. The AI only writes short explanations, only from the decision, and every sentence is checked.

### 1.7 Where the data comes from, and why this matters

All case text comes from **Lawphil** (lawphil.net, run by the Arellano Law Foundation). The app always shows a link to the official page and this notice: *the text is for information only, and Lawphil gives no warranty that it is complete or correct, so confirm with the Supreme Court.* The app is polite to Lawphil. It makes at most **1 request per second** and keeps a copy of everything it downloads, so it never asks for the same page twice. Before real use, written permission from the Arellano Law Foundation should be asked.

Law needs **accuracy**. That is why the design has three rules:

1. **Show the source** for everything.
2. **Never guess.** An empty answer is better than a wrong one.
3. **The student is in charge.** The app suggests and checks. The student decides.

---

## 2. Main features

> **Check a reviewer** and **My reviews** were removed from the app (the client does not need them). The backend routes for uploads and the old digests still exist but no page uses them; Flows B to D below describe that older path.

| Feature | What it does |
|---|---|
| **Case library** (`/library`) | The main page. A left rail of subjects (Civil Code, Constitutional Law, Remedial, Philosophy of Law, and more) and a table with three columns: Case, G.R. No. with date and ponente, View / Download. One row per **main case**: a later Resolution, a repeat, or a decision filed under several G.R. numbers is never a second row. |
| **Search finds unsaved decisions too** | In the library search box, saved cases come first. Below them, "Also on Lawphil, not saved yet" lists matches from Lawphil's own list (the catalog), each with "Open this case". Pressing it fetches the decision and saves it, then opens it. So the library only holds cases someone used, and no case needs to be downloaded in advance. |
| **Individual** | On the library page: type a case name or G.R. No., answer "What subject?", and the case opens with its full text. The subject is suggested by the AI and the student can change it. |
| **Bulk** | On the library page: paste G.R. numbers and/or add PDF or Word files, answer "What subject?" (or let the system decide). One main case per file or number; cases a file only cites are never added. After Start, the page becomes the **result of that upload**: only the main cases the student gave, one row each (a repeat, a Resolution or a cited case is never a row), each with its digest state, and a separate "Not added" list with the reason (not found, unreadable, Lawphil did not answer; Retry). Safe to leave. Files go up a few at a time (Vercel limits one request to about 4.5 MB). |
| **Case digest** (`/cases/{id}/digest`) | The client's format, written from the decision: Doctrine, Facts (story and the parties' arguments), Issue (YES/NO question), Ruling, Ratio Decidendi, Dissents, Topic Explained, Why this case matters. Every sentence cites the Court's paragraphs, is checked by code and by a second model, and is dropped if not supported. Marked "Drafted from the decision. Check it." Three Word downloads: *Facts and Doctrine*, *Doctrine, Facts, Issue, Ruling* (1 to 2 pages), *Full case digest* (about 6 pages). |
| **Search** | Find a case by name or G.R. number. Works in 1 to 37 milliseconds. |
| **Case library** | Saved cases with footnotes and facts read from each decision. |
| **Suggested Facts, Issue, Doctrine** | When the Court did not label a part, the box is filled with the Court's own paragraphs, marked "Suggested for you: check it". Order: the Court's heading, then rules (cue words such as "The issue is", "raises the following issues"; Issue only), then an AI that **only returns paragraph numbers**. Code copies the text from the stored decision and a second model must say "supported"; otherwise the box stays empty. The AI never writes the text. "Suggest for me" asks again. |
| **Download the full case** | `GET /cases/{id}/document.docx` (one decision) and `GET /uploads/{id}/cases.docx` (every found case a review cites, in cited order, at most 40). Text, footnotes (listed at the end of each decision, numbers raised in the text) and opinions as the Court printed them. No AI text. |
| **Guide** | `/guide`: steps, what each label means, a few questions and answers. A welcome card on the start page shows once (closed with "Got it", remembered in the browser). The wording is in `frontend/src/lib/copy.ts` (`guideCopy`). |

**Two rules the app always follows:**

- It always shows where the data comes from (Lawphil, with a link).
- It never guesses. If it does not know, it says so.

---

## 3. Tech stack

| Part | Tools |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 (with `pg_trgm` for fast name search) |
| Queue | RabbitMQ and Dramatiq (background jobs) |
| AI | Google Gemini (only writes explanations) |
| Frontend | React, TypeScript, Vite, Tailwind v4, shadcn, TanStack (Router, Query, Form, Table) |
| Files | PyMuPDF (read PDF), python-docx (read and write Word) |
| Web | nginx (serves the web app and forwards `/api` to the backend) |
| Run | Docker Compose |
| Tests | pytest, Vitest, Playwright |

---

## 4. Big picture

```
 Student's browser
        |
        v
 +---------------+     /api      +------------------+
 |  Web app      | ------------> |  API (FastAPI)   |
 |  (React)      |               |  port 8000       |
 +---------------+               +---+----------+---+
                                     |          |
                          reads/writes|          | sends jobs
                                     v          v
                             +-------------+  +-------------+
                             | PostgreSQL  |  |  RabbitMQ   |
                             | (data)      |  |  (queues)   |
                             +------^------+  +------+------+
                                    |                |
                                    |        +-------+---------+
                                    |        |                 |
                              +-----+--------v--+       +------v----------+
                              | worker-lawphil  |       | worker-digests  |
                              | 1 thread        |       | 4 threads       |
                              +--------+--------+       +--------+--------+
                                       |                         |
                                       v                         v
                                  lawphil.net               Google Gemini
```

**Why a queue?** Reading Lawphil and asking the AI is slow. The API answers fast and the workers do the slow work in the background.

---

## 5. App flow

### Flow A: Search a case

```
Student types "Ermita" or "180046"
        |
        v
API: GET /catalog/search
        |
        v
Search the local copy of Lawphil's list (PostgreSQL)  -- no call to Lawphil, takes milliseconds
        |
        v
Show results (name, G.R. number, date, Lawphil link)
        |
Student clicks "Open this case"
        |
        v
Is the case already saved?
   yes -> open it at once
   no  -> download the page from Lawphil (about 3 seconds), save it, open it
```

The **catalog** is a local copy of Lawphil's monthly lists (1987 to now, 34,684 decisions). It is built once in the background (about 9 minutes), then kept fresh.

### Flow B: Upload and check a reviewer

```
Student uploads PDF/Word (max 5 MB, set by UPLOAD_MAX_MB)
        |
        v
API reads the text, finds citations like "GR no 180046"
Saves the upload AND the original file
        |
        v
For each citation:
   case already saved?  yes -> check it now
                        no  -> status "pending", send job to RabbitMQ (queue: lawphil)
        |
        v
worker-lawphil: find the case (catalog first) -> download -> read -> save -> check
        |
        v
Result per citation:
   Matches the Court's record
   Needs a look  (example: you wrote 2010, the Court says 2009)
   Could not find this case
   Could not check right now
```

The web page asks the API every 3 seconds until all citations are done.

### Flow C: Finished reviewer (digests)

```
Citations are checked
        |
        v
App starts one digest for each case that was found   (automatic)
        |
        v
At once (no AI):
   Facts   <- the Court's own heading "The Facts" (if there is one)
   Issue   <- the Court's own heading "The Issues" (if there is one)
   Ruling  <- the paragraphs before the last "SO ORDERED"
   Doctrine<- left empty: the student picks or pastes it
        |
        v
In the background (queue: digests, uses Gemini):
   Topic explained
   Why this case matters
   Any question the student adds
        |
        v
Web page shows one digest box for each case. Each box says where it sits in the reviewer
("under I. Legislative power…"). A switch can show the reviewer's full text with each box after
the paragraph that cites the case.
```

### Flow D: Edit and download

```
Student can, for each field:
   Edit              -> type their own words          (marked "Written by you")
   Pick paragraphs   -> choose paragraphs of the decision (the server copies the Court's exact words)
   Paste text        -> paste their own text           (marked "Pasted by you")
   Put back          -> return to the system's version
   Write it again    -> ask the AI again (explanations only)
        |
        v
"Download as Word"
   Word file upload -> boxes are inserted into a COPY of the student's file
   PDF upload       -> a new Word file is built from the PDF text (layout is different)
```

---

## 6. How the AI stays honest

The AI **only writes explanations**. It never writes Facts, Issue, Ruling, or Doctrine. Those are always the Court's own words.

Every AI sentence goes through these steps:

```
1. WRITER (Gemini 2.5 Flash) writes sentences. Each sentence must name the paragraphs it uses.
2. CODE CHECK:
     - the paragraphs must exist
     - every number must be in the cited paragraph
     - every name must be in the decision
3. CHECKER (a second Gemini model) says: supported / partly / not supported.
     - only "supported" is kept
4. If nothing is left, the field stays empty and says why. It never shows a guess.
```

On screen, an AI answer is marked **"Drafted from the decision. Check it."** and shows its sources ("Based on paragraphs 7, 65").

Test result: 43 of 48 sentences kept on 8 real decisions. A person read all of them. None was wrong. One was a little too strong (it was fixed).

---

## 7. Project folders

```
scraper/
├── backend/
│   ├── caselens/
│   │   ├── domain/            Rules and data shapes. No tools or libraries from outside.
│   │   │   ├── entities.py, case_digest.py, finished_reviewer.py, ...
│   │   │   └── services/      Pure logic (citation matcher, ruling finder, heading finder, ...)
│   │   ├── application/       "Use cases" (one job each) and ports (interfaces)
│   │   │   ├── ports/         What the app needs from outside (JobQueue, repositories, AI, ...)
│   │   │   └── use_cases/     ProcessUpload, BuildCaseDigest, SearchCatalog, ...
│   │   ├── infrastructure/    The real tools: PostgreSQL, Lawphil, RabbitMQ, Gemini, Word files
│   │   └── presentation/api/  FastAPI routes and response shapes
│   ├── alembic/versions/      Database migrations (0001 to 0008)
│   ├── tests/                 Backend tests and real saved Lawphil pages
│   └── docker-compose.yml
├── frontend/
│   └── src/
│       ├── routes/            Pages
│       ├── features/          Parts of pages (search, reviews, digest, ...)
│       ├── api/               Calls to the backend and TanStack Query
│       └── lib/copy.ts        All student-facing words in one place
└── README.md, TECHNICAL_DOC.md
```

**Clean Architecture rule:** code points inward. The domain does not know about the database, the queue, or the AI. Tools can be swapped in one file (`composition.py`). Example: we changed Redis to RabbitMQ and no use case changed.

### Flow E: Case library, Bulk and case digest

```
Individual (name or G.R. No.)  ─┐
Bulk (G.R. numbers / PDFs)     ─┤  MainCaseIdentifier reads only the caption (first lines): the G.R. No. and date
                                │  -> the official decision is fetched from Lawphil (a PDF is only used to read the number)
                                v
                      CaseFamily: same numbers as a saved case?  yes -> duplicate / related (hidden, linked to the main case)
                                                                  no  -> a new main case, listed in the library
                                v
                      subject: AI suggests one name from the fixed list (or "unsure"); the student's choice always wins
                                v
                      case digest job (queue `digests`): writer -> code checks -> checker -> one repair pass -> saved once
                                v
                      Library row: Case digest | Full text | Download (3 levels)
```

The three levels only choose which sections print; the digest is written once with every section. Related cases a decision merely *cites* are never opened.

---

## 8. Database tables

| Table | What it stores |
|---|---|
| `cases` | Full decision text and original page; `subject_id`, `subject_source` (ai, student or batch), `main_case_id` (set on a related page) |
| `subjects` | The fixed list of subjects (seeded, ordered) |
| `case_digests_v2` | The case digest of one main case: sections as JSON, state (pending, ready, failed), model, prompt version, tokens |
| `bulk_batches`, `bulk_items` | A bulk upload and each of its items with status and message (PDFs are not stored) |
| `case_footnotes`, `case_opinions`, `case_statutes`, `case_citations` | Parts read from a decision |
| `uploads` | Uploaded reviewer (text and original file) |
| `upload_citations` | Each citation found, its status, and what differs |
| `digests` | One digest per case per upload. Fields are stored as JSON. |
| `catalog_entries`, `catalog_numbers`, `catalog_months` | Local copy of Lawphil's lists |
| `month_indexes` | Cache of Lawphil month pages |
| `job_locks` | "Only one at a time" locks for background jobs |

---

## 9. Background jobs

| Queue | Jobs | Worker |
|---|---|---|
| `lawphil` | check an upload, fetch a case, build or refresh the catalog | 1 thread (keeps Lawphil to 1 request per second) |
| `digests` | write the AI answers and the case digests (3 to 5 minutes of AI work each) | 4 threads (they only wait for Gemini) |
| `lawphil` (bulk) | resolve one bulk item: read the number, find or fetch the main case | same 1 thread |

- **Retries:** a failed job retries 3 times (after 15 s, 1 min, 4 min). Then it goes to a dead-letter queue (`<queue>.XQ`).
- **Worker dies:** the job is given to a worker again. All jobs are safe to run twice.
- **RabbitMQ is down:** the API answers `503` with a clear message. Reading and searching still work.
- **Monthly limit:** `CASE_DIGEST_MONTHLY_LIMIT` (default 2,500) counts case digests started this month. Over it, a digest stops with a plain message instead of spending more. When the month turns, or the limit is raised, `python -m caselens.manage resume-digests` (also run at every restart) starts the waiting ones again, oldest first, as far as the limit allows.
- **Gemini limits:** a "rate limited" answer (429) is retried after 20 s, 40 s, ... The thinking budget (`CASE_DIGEST_THINKING_BUDGET`, default -1 = the model decides) was measured at 1024 on one case: 16% faster, 14% fewer output tokens, 3 fewer sentences kept; the default stays at -1.
- **Restart:** queued bulk items and pending case digests are queued again.
- **Locks:** RabbitMQ cannot do "only one at a time", so we use the `job_locks` table. Locks expire by time, so a crashed worker cannot block work forever.

---

## 10. Main API routes

| Route | Use |
|---|---|
| `GET /catalog/search?q=` | Search Lawphil's list |
| `POST /uploads` | Upload a reviewer |
| `GET /uploads/{id}` | Check results (poll until done) |
| `GET /uploads/{id}/document` | Reviewer with digest boxes (JSON) |
| `GET /uploads/{id}/document.docx` | Download the Word file |
| `POST /cases/{id}/digest` | Start a digest |
| `GET /digests/{id}` | Read a digest |
| `PUT /digests/{id}/fields/{key}/text` | Type over a field |
| `PUT /digests/{id}/fields/{key}/passage` | Pick paragraphs |
| `POST /digests/{id}/fields/{key}/paste` | Paste text |
| `POST /digests/{id}/fields/{key}/reset` | Put back the original |
| `POST /digests/{id}/questions` | Add your own question |
| `GET /cases/{id}` | One case |
| `GET /library/cases?q=&subject_id=&batch_id=&limit=&offset=` | The library: main cases only, one row each. With `batch_id`: only what that bulk upload gave, each main case once, in the order given. Each row carries `digest_state` (none, pending, ready, failed). |
| `GET /library/subjects`, `GET /library/subject-list` | Subjects with counts; the plain list |
| `PUT /cases/{id}/subject` | File a case under a subject (the student's choice wins) |
| `POST /cases/{id}/case-digest` | Ask for the case digest (202; written in the background) |
| `GET /cases/{id}/case-digest` | Read it (poll while pending) |
| `GET /cases/{id}/case-digest.docx?level=short\|standard\|full` | Word download of one level |
| `POST /bulk` | Start a bulk upload (G.R. numbers, subject) |
| `POST /bulk/{id}/files` | Add PDF or Word files, a few at a time |
| `GET /bulk`, `GET /bulk/{id}`, `GET /bulk/{id}/items` | Progress |
| `POST /bulk/{id}/retry` | Try the failed items again |

Full list with examples: open `http://localhost:8000/docs`.

---

## 11. How to run

```bash
cd backend
cp .env.example .env            # then put your GEMINI_API_KEY in .env
docker compose up -d --build
```

| What | Address |
|---|---|
| Web app | http://localhost:8080 |
| API and docs | http://localhost:8000 and http://localhost:8000/docs |
| RabbitMQ page | http://localhost:15675 (login `caselens` / `caselens`, for development only) |
| Database | `localhost:5434` |

Port 8000 busy? Use `API_PORT=8002 docker compose up -d`.

Frontend development (hot reload): `cd frontend && npm install && npm run dev` then open http://localhost:5173.

First time only: build the Lawphil catalog (about 9 minutes). The first search starts it. Or run:
`docker compose exec api python -m caselens.manage catalog build`

**Settings (`backend/.env`):** `DATABASE_URL`, `RABBITMQ_URL`, `GEMINI_API_KEY`, `GEMINI_WRITER_MODEL`, `GEMINI_CHECKER_MODEL`, `DIGEST_AI_DAILY_LIMIT`, `AUTO_DIGEST_ON_UPLOAD`. Without a Gemini key, digests still work. Only the AI explanations are missing.

---

## 12. How to test

```bash
cd backend  && . .venv/bin/activate && pytest -m "not live"   # 615 tests
cd frontend && npm test                                        # 146 tests
cd frontend && npm run e2e                                     # browser tests (needs the stack running)
```

- Tests use **real saved Lawphil pages** (31 decisions from 1988 to 2025). Expected values were read by hand.
- `pytest -m live` calls the real Lawphil site (slow, optional).
- AI quality check: `python -m tests.eval.run_answer_eval` (costs a few cents).

---

## 13. Real numbers (measured)

| Check | Result |
|---|---|
| Search | 1 to 37 ms |
| Build the Lawphil catalog (once) | about 8 min 10 s |
| Open a case that is not saved yet | about 2 to 4 s |
| One digest (AI answers, the two explanations written at the same time) | about 15 s |
| 4 digests together vs one by one | 28 s vs 85 s |
| 3-case reviewer, upload to finished | about 27 s |
| Message in the queue, publish to consumed | 26 ms |

---

## 14. Limits to know

- The catalog starts in **1987**. Older cases need the year or the Lawphil link.
- A **scanned** PDF (picture only) cannot be read.
- A **PDF** is rebuilt as a new Word file, so the layout is different. A Word file keeps its own layout.
- If the uploaded file **already has digests** written by the student, the app cannot tell them from the other text. It keeps them, adds its own box, and shows a notice that says to upload the reviewer without the digests for a cleaner result.
- The AI explanation can be thin or incomplete. That is why it is marked as a draft.
- Lawphil gives **no warranty** about its text. The app shows this notice. Ask the Arellano Law Foundation for written permission before real use.
- The **case digest** is AI-written. It can still miss a point or word a holding too loosely; each sentence is checked and unsupported ones are dropped, so a section can be short (the vote count, for example, is dropped when the checker cannot tie it to a paragraph). Always read it against the decision.
- The digest only knows the stored Lawphil text: events after the decision, and the SCRA citation, appear only if the decision says so.
- At about 2,000 digests a month the free hosting is not enough; see `DEPLOYMENT_PLAN.md` section 13.
- Not built yet: A.M. and A.C. cases, the Supreme Court E-Library, user accounts, a two-column box layout like the student's own file.

---

## 15. Quick glossary

| Word | Meaning |
|---|---|
| **Reviewer** | The student's study notes (PDF or Word) that cite cases |
| **G.R. No.** | The number of a Supreme Court case |
| **Digest** | A short summary box for one case |
| **Doctrine** | The rule the case teaches |
| **Ponente** | The justice who wrote the decision |
| **Catalog** | The app's local copy of Lawphil's list of decisions |
| **Worker** | A program that does slow jobs in the background |
| **Queue** | A waiting line of jobs (RabbitMQ) |
