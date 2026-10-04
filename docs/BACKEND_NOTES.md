# CaseLens

Internal tool for law students. Upload a reviewer (PDF/DOCX); the app finds every cited
**G.R. number**, pulls the **official** decision from [Lawphil](https://lawphil.net) into
PostgreSQL, checks the student's citation against it, and shows findings parsed from the
official text. No manual lookups.

The API is in [`backend/`](backend/) and the web app in [`frontend/`](frontend/).

## What it guarantees (and what it does not)

| | |
|---|---|
| Official text is stored **verbatim** with its source URL, fetch time and original HTML | `raw_html`, `full_text`, `source_url`, `fetched_at` |
| A citation is checked only on facts the official page contains | G.R. no., year/date, parties' names |
| The reporter cite (`538 SCRA 428`) is **not on Lawphil's page** | reported as `unverified`, never as right or wrong |
| Unknown G.R. numbers are never guessed | status `not_found` with the reason |
| Insights are **parsed or counted, never generated** (no AI) | every value traces to the stored text |
| Every response with official text carries Lawphil attribution + its own disclaimer | `attribution` field |
| It does **not** judge whether a digest's *meaning* is right | out of scope without AI |

Real example (your sample reviewer): it cites `GR no 180046 (April 2, 2010)`; the official
decision is **April 2, 2009**. The app reports `mismatch: year claimed 2010, official 2009`
and links to the official page.

## Architecture: Clean Architecture, dependencies point inward

```
backend/caselens/
  domain/           pure Python. Entities, value objects, rules. Imports no framework/DB/HTTP.
    services/         TextNormalizer, GrCitationExtractor, CitationMatcher, StatuteExtractor,
                      CitedCaseExtractor, DispositionClassifier, DispositiveExtractor,
                      SignatureReader, CaseInsightBuilder
  application/      use cases + the ports (ABCs) they need
    ports/            repositories.py, gateways.py, queries.py
    use_cases/        ProcessUpload, ResolveUploadCitations, FetchCaseByGrNumber, IngestCase,
                      SearchCaseByGrNumber, GetCase, GetUpload, GetCaseInsights, GetTrends,
                      ReparseStoredCases
  infrastructure/   adapters that implement the ports
    db/               SQLAlchemy models, mappers, repositories, trend SQL
    lawphil/          URL scheme, throttled HTTP client, case source (locate+fetch), HTML parser
    extraction/       PDF, DOCX, composite reader
    queue/            RabbitMQ (Dramatiq) job queue + worker jobs
  presentation/     FastAPI routers and response schemas
  composition.py    the ONE place that picks concrete classes for the ports
```

How the SOLID principles show up, so you can check them in the code:

- **S**: one reason to change per class. `LawphilCaseParser` only parses HTML, `ThrottledPageClient`
  only does polite HTTP, `CitationMatcher` only compares, each text rule in `text_normalizer.py` is its own class.
- **O**: a new file format is a new `DocumentTextExtractor`; a new source (e.g. the Supreme Court
  E-Library) is a new `CaseLocator`/`CaseFetcher`/`CaseParser`. No use case changes.
- **L**: use cases run unchanged on SQL repositories or on the in-memory fakes in `tests/fakes.py`.
- **I**: small ports. `CaseLocator` and `CaseFetcher` are separate; `MonthIndexRepository`,
  `CaseRepository`, `UploadRepository`, `InsightQueries` are separate.
- **D**: use cases depend on ports only. `composition.py` wires the concrete classes.

SQLAlchemy models are an infrastructure detail: `infrastructure/db/mappers.py` converts them to
domain entities, so the domain never imports SQLAlchemy.

## Flow

```
POST /uploads  -> read file -> find G.R. citations -> for each:
                     case already stored?  yes -> check it now
                                           no  -> status "pending", job queued (202)
worker (lawphil queue) -> locate on Lawphil -> fetch -> parse -> store -> check -> status
GET /uploads/{id}  poll until "done"
```

Lawphil's own search is Google CSE (not scrapeable), so the app keeps its own **catalog**: Lawphil
publishes a monthly list of every decision (`/judjuris/juri2009/apr2009/apr2009.html`). A background job reads
those lists once (1987 to now) into PostgreSQL. A G.R. number or case name is then found in the local
catalog with no year needed and no Lawphil request; the full text is fetched only when a case is opened.
If the catalog has nothing for a number, the worker falls back to scanning month lists around the claimed year.
Requests are throttled to 1 per second with retry/backoff.

| What | Time (measured) |
|---|---|
| Build the catalog once, 1987 to now (464 months, 34,684 decisions) | about 8 min 10 s, in the background; search works on what is read so far |
| Search by name or number | 1 to 37 ms, no Lawphil request |
| Open a case not saved yet | about 2 to 4 s (one page) |
| Keep it fresh | re-reads the current and previous month, at most once a day, on demand |

## Run it

```bash
cd backend
cp .env.example .env
docker compose up -d --build      # postgres (5434), rabbitmq (5675; management page 15675), api (8000), 2 workers, web app (8080)
# if port 8000 is taken on your machine: API_PORT=8002 docker compose up -d --build
open http://localhost:8080        # the web app for students
curl localhost:8000/health        # the API directly
```

Upload your reviewer and poll:

```bash
curl -F "file=@reviewer.pdf" localhost:8000/uploads        # 202 + {"id": 1, "status": "processing", ...}
curl localhost:8000/uploads/1                              # until "status": "done"
```

The web app is served by nginx, which forwards `/api/*` to the API, so the browser only talks to one
origin. See [`frontend/README.md`](frontend/README.md) for development and design notes.

Ports 5434/5675/15675 are chosen to avoid other services on this machine (5432/5433/5672 were taken).

## Background jobs (RabbitMQ)

Slow work runs in workers, not in the web request. Jobs go through **RabbitMQ** using **Dramatiq**, behind the
`JobQueue` interface, so no use case knows which broker is used.

| Queue | Jobs | Worker |
|---|---|---|
| `lawphil` | resolve an upload's citations, fetch a case, build or refresh the Lawphil catalog | 1 thread, so "1 request per second to Lawphil" holds |
| `digests` | write the AI answers of a digest | 4 threads (they only wait for Gemini) |

- **A worker dies mid-job:** the job is delivered again (measured: killed with SIGKILL, restarted, finished). Every job is safe to run twice.
- **A job keeps failing:** retried 3 times (15 s, 1 min, 4 min), then parked in `<queue>.XQ` (see the management page, http://localhost:15675, login `caselens`/`caselens`, development only).
- **RabbitMQ is down:** the API answers `503 The job queue is not reachable right now`; reading and searching keep working; workers reconnect by themselves.
- **"Only one at a time"** (one catalog build, one fetch per case, one AI run per digest) is a lock in PostgreSQL (`job_locks`, with a time limit so a crashed worker cannot block it forever), because a message broker has no such lock. There is no Redis.
- Measured with the real stack: a message goes from publish to consumed in about 26 ms; 4 digests together take 28 s, one after another 85 s.

## Case digests (Facts, Issue, Ruling, Doctrine, Topic explained, Why this case matters)

`POST /cases/{id}/digest` returns the Court's own text at once (Facts and Issue only when the Court labelled them, the
Ruling always, the Doctrine left for the student to pick). The written answers ("Topic explained", "Why this case matters",
and any question the student adds) are written by Gemini in the background, and every sentence must pass two checks:
code (it cites real passages; its numbers and names are in the decision) and a second Gemini call (the cited passages
really say it). A sentence that fails is dropped; if nothing passes, the field says so and stays empty.
Set `GEMINI_API_KEY` in `backend/.env`; without it the digest still works, minus the written answers.
The student can type over, pick paragraphs of the decision, paste, or reset any field.

## API

| Method | Path | |
|---|---|---|
| POST | `/uploads` | PDF/DOCX (≤5 MB by default). 202 while citations are still being fetched |
| GET | `/uploads?limit=` | recent uploads, newest first, with how many citations are in each state |
| GET | `/uploads/{id}` | per-citation result: `match` / `mismatch` / `not_found` / `error` / `pending`, with the official record each was checked against |
| POST | `/uploads/{id}/retry` | check again the citations that could not be checked (source down) |
| POST | `/uploads/{id}/citations/{cid}/attach` `{"url": ...}` | the student pastes the Lawphil link for a citation that could not be found |
| GET | `/catalog/search?q=&year=&limit=&offset=` | search Lawphil's list by case name or G.R. number (any year); each hit says if it is already in the library |
| POST | `/cases/{id}/digest` | start (or return) a digest: Court text at once, AI answers in the background |
| GET | `/digests/{id}` | the digest; poll until `status` is `ready` |
| PUT | `/digests/{id}/fields/{key}/text` `/passage`, POST `.../paste` `.../reset` | edit a field: type, pick the Court's paragraphs, paste, restore |
| POST | `/digests/{id}/questions` | add a question of your own; answered in the background |
| GET | `/catalog/status` | how much of the list has been read (`building` / `partial` / `ready`) |
| POST | `/catalog/build` | start or resume reading the list |
| GET | `/cases?gr_no=180046&year=2009` | stored case, or 202 + background fetch. `year` is optional; the catalog finds it |
| GET | `/library/cases?q=&limit=&offset=` | stored cases without their text, searchable by name or the start of a G.R. number |
| GET | `/cases/{id}` | full official text, footnotes (each with a `#fntN` deep link), opinions, statutes, cited cases |
| POST | `/cases/fetch` `{"url": ...}` | manual fallback: fetch one official Lawphil page by URL |
| GET | `/cases/{id}/insights` | ponente, division, ruling (verbatim), concurring justices, statutes, cited cases + footnote links |
| GET | `/insights/trends` | top statutes, rulings by year, most-cited cases, cases per ponente. `enough_data=false` below 5 stored decisions |

## Operate

```bash
docker compose exec api python -m caselens.manage catalog build     # read Lawphil's monthly lists (resumable)
docker compose exec api python -m caselens.manage catalog refresh   # re-read current + previous month
docker compose exec api python -m caselens.manage catalog status
docker compose exec api python -m caselens.manage reparse   # re-read stored pages with the current parser (no network)
docker compose exec api python -m caselens.manage refetch   # download again cases whose stored text was damaged on download
docker compose logs -f worker-lawphil worker-digests
```

Pages are decoded by the encoding they declare (Lawphil says `windows-1252` only inside the page), so
curly apostrophes and quotes survive; `refetch` repairs any case stored before that fix.

Original HTML is stored for every case, so improving the parser never means re-downloading.
`cases.parser_version` marks which rows need `reparse`.

## Test

```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
pytest -m "not live"      # offline + PostgreSQL (uses its own `caselens_test` database, built by the real migrations)
pytest -m live            # hits the real lawphil.net, throttled (about 1 minute)
```

Expected values in tests come from real saved Lawphil pages and are documented in
`tests/fixtures/EXPECTED.md`. Values that were written for a test rather than read from Lawphil are
labelled `(synthetic)`. Real pages found several parser bugs that one-page tests missed (empty
footnotes, multi-paragraph rulings, justices in a `<table>`, boilerplate certification counted as a
citation); each has a regression test.

## Known limitations

- **Catalog covers 1987 onward.** Older cases (1901-1986) are not in it; a lookup falls back to scanning
  around the year given, and the student can paste the Lawphil link. Reading the older archive is possible
  (about 25 more minutes) but wait for the Foundation's consent first.
- **A.M. and A.C. matters** are not searchable (only G.R. cases).
- **Case names are Lawphil's own text**, typos included; searching "Comelec" will not find "Commission on
  Elections" (no abbreviation aliases yet).
- **Joint decisions** (`G.R. Nos. 211972 & 212045`) keep every number (`cases.numbers`), so a citation of
  either number matches.
- Only the **primary decision** file is stored; separate-opinion files (`gr_207145_so_2015`) are located
  but not ingested. Opinions printed on the decision's own page are stored.
- **Disposition** (GRANTED, DENIED, ...) is a keyword reading of the ruling. The verbatim ruling is
  returned next to it so it can be checked. Rulings with no standard verb are `UNKNOWN`.
- **Scanned PDFs** (images only) are rejected, not OCR'd.
- Supreme Court **E-Library** is not implemented (its search was not inspected).
- Statutes recognised: Republic Acts, Executive Orders, Batas Pambansa, Commonwealth Acts, Constitution
  articles. Administrative orders and memorandum circulars are not.

## Before real use: permission

Lawphil's Acceptable Use Policy and Disclaimer (read 2026-10-03) neither forbid nor permit automated
access, and there is no `robots.txt`. They say the content is informational, carries **no warranty of
accuracy or completeness**, and should be confirmed with the originating body. The app therefore
shows attribution and that notice, throttles to 1 request/second and caches everything. The catalog crawl is about 510 requests once, then 2-3 a day. Ask the
Arellano Law Foundation (https://lawphil.net/contactus.html) for written permission before going live.
