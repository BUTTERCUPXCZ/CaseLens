# CaseLens: Deployment Plan

**Database:** Supabase. **API:** Render. **Web app:** Vercel.

**Status:** the code changes (F1) are done and tested. The deploy steps (F2 onward) are not done yet. Free plans change often, so do the check in section 12 before you start.

---

## 1. The stack

```
 Student's browser
        |   https://caselens.vercel.app
        v
 +-------------------+   /api/*  (Vercel rewrite)   +--------------------------------+
 |  Vercel           | ---------------------------> |  Render Web Service            |
 |  React web app    |                              |  the API (FastAPI)             |
 +-------------------+                              |  + the background jobs         |
                                                    +---------+----------------+-----+
                                                              |                |
                                                              v                v
                                                   +------------------+   lawphil.net
                                                   |  Supabase        |   Google Gemini
                                                   |  PostgreSQL      |
                                                   +------------------+
```

| Part | Service | Why |
|---|---|---|
| Web app | **Vercel** | Free hosting for React apps. Fast worldwide. Deploys on every push to GitHub. |
| API and jobs | **Render** | Runs our Docker image. Free web service available. |
| Database | **Supabase** | Free PostgreSQL (500 MB). We use it only as a database. |
| AI | Google Gemini | Free tier to start. |

## 2. Two ways to run the background jobs

The app has slow jobs (reading Lawphil, writing the AI explanations). Today they run in **two worker programs fed by RabbitMQ**. The deployment can run them in one of two ways. It is **one setting**, `QUEUE_BACKEND`.

| | **Mode A: Free (start here)** | **Mode B: Workers (when you can pay)** |
|---|---|---|
| Setting | `QUEUE_BACKEND=threads` | `QUEUE_BACKEND=rabbitmq` |
| Jobs run | As threads **inside the API** | In **2 separate Render workers**, fed by RabbitMQ |
| Extra services | None | 2 Render Background Workers (paid) and RabbitMQ on **CloudAMQP** (free starter plan) |
| Render plan | Free Web Service | Starter for the API and each worker |
| Cost | **$0** | about $21 a month on Render, plus Supabase and Vercel |
| If the service restarts | The API picks up unfinished work again on start | The queue keeps the message and gives it to a worker again |
| Needs RabbitMQ? | **No** | **Yes** |

**Why Mode A exists:** Render has **no free background workers**, so on the free plan there is nowhere to run them. Because the backend has a `JobQueue` interface, the thread version is one new adapter, not a rewrite.

**The rest of this plan is Mode A.** Mode B notes are marked **[B]**.

---

## 3. Decisions to confirm

1. **Mode A for now?** The jobs run inside the API, and the first visit after a quiet time waits 30 to 60 seconds (Render's free service sleeps).
2. **An access code before sharing the link.** The app has no login. Without a gate, anyone with the link can upload files and use up the student's Gemini quota.
3. **Gemini free tier and privacy.** Google may use free-tier prompts to improve its products. Only the citing paragraph of the reviewer and public decision text are sent. Tell the student.
4. **Vercel's free Hobby plan is for non-commercial use.** Fine for a student project. If the app becomes a paid service, move to Pro.

---

## 4. Changes to the code and files

| # | Change | Mode |
|---|---|---|
| 1 | **Thread job queue** (`ThreadJobQueue`) and `QUEUE_BACKEND`. The job code becomes plain functions that both the thread queue and the Dramatiq actors call. | A |
| 2 | **Recover unfinished work on start.** Re-run uploads still "processing" and digests still "pending". | A |
| 3 | **Database address.** Accept `postgres://` or `postgresql://`, turn it into `postgresql+psycopg://`, and require SSL (`sslmode=require`). | A and B |
| 4 | **Row Level Security on every table** (a migration). See section 5. | A and B |
| 5 | **Port.** Start the API on `$PORT` (`--port ${PORT:-8000}`). | A and B |
| 6 | **Upload clean-up.** Delete uploads (and their stored files) older than 7 days. Lower the file limit to 5 MB. | A and B |
| 7 | **Lower AI limit** (`DIGEST_AI_DAILY_LIMIT=20`) to stay inside Gemini's free quota. | A and B |
| 8 | **Access gate** (a shared access code). | A and B |
| 9 | **`render.yaml`** and **`frontend/vercel.json`**. | A and B |
| 10 | **Docs.** The environment variables and the steps. | A and B |

Draft `render.yaml` for Mode A (check the field names against Render's current docs):

```yaml
services:
  - type: web
    name: caselens-api
    runtime: docker
    plan: free
    region: singapore
    rootDir: backend
    dockerfilePath: ./Dockerfile
    healthCheckPath: /health
    envVars:
      - { key: QUEUE_BACKEND, value: threads }
      - { key: DIGEST_AI_DAILY_LIMIT, value: "20" }
      - { key: DATABASE_URL, sync: false }     # the Supabase session pooler address
      - { key: GEMINI_API_KEY, sync: false }
      - { key: ACCESS_CODE, sync: false }
```

**[B]** For Mode B, add two `type: worker` services with `dockerCommand: dramatiq caselens.infrastructure.queue.actors --queues lawphil --processes 1 --threads 1` and `... --queues digests --processes 1 --threads 4`. Set `QUEUE_BACKEND=rabbitmq` and `RABBITMQ_URL` (from CloudAMQP) on the API and both workers.

`frontend/vercel.json`:

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://caselens-api.onrender.com/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Content-Security-Policy", "value": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'" }
      ]
    }
  ]
}
```

---

## 5. Supabase

We use Supabase **only as a PostgreSQL database**, not its login, storage or other tools.

1. **Create the project.** Pick the region closest to Render (**Singapore** for both). Save the database password.
2. **Use the Session pooler address.** Supabase's "direct" address works only over IPv6, and Render's free service may not reach it. Open **Connect** and copy the **Session pooler** address:
   `postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
   Do **not** use the "Transaction pooler" (port 6543): it does not allow the prepared statements our database driver uses.
3. **Turn on Row Level Security (RLS) on every table. This is important.** Supabase puts a public REST API in front of every table in the `public` schema. Anyone with the project's public "anon" key could read and change our data through it. Our backend connects as the owner role, which ignores RLS. So we enable RLS on every table with **no policies**: the public API sees nothing, and our app keeps working. This is change 4. Check it in **Database → Tables** (every table shows RLS enabled). Never put the **service role** key in Vercel or in the repo. We do not need it.
4. **`pg_trgm`.** Our first migration runs `CREATE EXTENSION IF NOT EXISTS pg_trgm`. Supabase allows it. If it fails, enable it in **Database → Extensions**.
5. **Load Lawphil's list from the laptop** (about 5 minutes, instead of a 9-minute crawl on the free server). Run it after the API has started once, because the API creates the tables.
   ```bash
   pg_dump -h localhost -p 5434 -U caselens -d caselens \
     -t catalog_entries -t catalog_numbers -t catalog_months \
     --data-only --no-owner -Fc -f catalog.dump
   pg_restore --data-only --no-owner -d "<Supabase session pooler address>" catalog.dump
   ```
6. **The 1-week pause.** A free project with no activity for a week is paused (you click **Restore**). The pinger in section 8 calls `/health`, which queries the database.
7. **Backups.** The free plan has **no automatic backups**. Once a month, run `pg_dump` from the laptop and keep the file. The catalog can always be rebuilt. The saved cases and uploads are what matter.
8. **Size.** 500 MB. Our database is about 39 MB (the catalog is 24 MB). A saved case is about 150 KB. Uploaded files are stored in the database (up to 5 MB each), so change 6 (auto-delete after 7 days) protects the limit.

## 6. Render

1. Log in with GitHub. Choose **New → Blueprint** and pick the `CaseLens` repo (it reads `render.yaml`), or **New → Web Service** and fill in the same settings by hand.
2. Settings: runtime **Docker**, root directory `backend`, plan **Free**, region **Singapore**, health check `/health`.
3. Set the environment variables from section 7.
4. **Deploy.** On start the API runs `alembic upgrade head` and creates every table.
5. Open `https://<service>.onrender.com/health`.

Facts about the free web service: it **sleeps after about 15 minutes** without visitors (the next visit waits 30 to 60 seconds), has **512 MB** of memory, about **750 free hours** a month (enough for one service all month), and its disk is wiped on every deploy and restart. We store nothing on its disk.

## 7. Environment variables

| Name | On | Value |
|---|---|---|
| `DATABASE_URL` | Render | The Supabase session pooler address |
| `QUEUE_BACKEND` | Render | `threads` (Mode A) or `rabbitmq` (Mode B) |
| `GEMINI_API_KEY` | Render | Your key from Google AI Studio |
| `GEMINI_WRITER_MODEL`, `GEMINI_CHECKER_MODEL` | Render | `gemini-2.5-flash`, `gemini-3.5-flash` |
| `DIGEST_AI_DAILY_LIMIT` | Render | `20` |
| `ACCESS_CODE` | Render | A code you choose (the gate) |
| `UPLOAD_MAX_MB`, `UPLOAD_KEEP_DAYS` | Render | `5`, `7` |
| `LAWPHIL_USER_AGENT` | Render | Include a contact email, so Lawphil can reach you |
| `RABBITMQ_URL` | Render **[B]** | From CloudAMQP (`amqps://...`) |
| *(none)* | Vercel | Not needed with the rewrite |

No secret goes in the GitHub repo. Never put the Gemini key in Vercel.

## 8. Keep it awake (optional, recommended)

Use a free pinger such as **UptimeRobot** (the free plan checks every 5 minutes) on `https://<service>.onrender.com/health`. It keeps Render awake (no 30 to 60 second wait) and keeps the Supabase project active.

---

## 9. Phases (each has a gate)

**F0. Accounts** (about 30 minutes)
Create Render, Vercel and Supabase accounts (all with GitHub). Make a Gemini API key.
*Gate:* three accounts and one key. **No credit card should be needed.** If one asks for a card, stop.

**F1. Prepare the code** (about 1 day)
Changes 1 to 8 from section 4, with tests: the thread queue (the same behaviour as the queue tests), the recovery on start, the database address, RLS on every table, the upload clean-up, and the access gate.
*Gate:* backend and frontend tests pass. A local run with `QUEUE_BACKEND=threads` and **no RabbitMQ** can upload a reviewer and get its digests.

**F2. Supabase** (about 30 minutes)
Create the project, copy the session pooler address, and start the API against it once to create the tables. Load the catalog (section 5, step 5).
*Gate:* every table shows **RLS enabled**. The anon key cannot read a table. `catalog_entries` has 34,684 rows.

**F3. Render** (about 30 minutes)
Deploy the API (section 6).
*Gate:* `GET /health` returns `{"status":"ok","db":"ok","pg_trgm":true}`, and `GET /catalog/status` is `ready`.

**F4. Vercel** (about 30 minutes)
Import the repo. Settings: **Root Directory** `frontend`, **Framework** Vite, **Install** `npm ci`, **Build** `npm run build`, **Output** `dist`. Add `vercel.json` with the real Render address. Deploy.
*Gate (on the real address):*
1. The start page loads, and the menu has 3 links.
2. Search `Ermita` gives 37 results.
3. Upload the plain sample reviewer. The check finishes, the Finished reviewer shows a box, and the explanations arrive.
4. **Upload a 4 MB and a 5 MB file.** If Vercel blocks one, call the API directly from the browser (a code change: `VITE_API_BASE_URL`, CORS in the API, and the API address in `connect-src`).
5. Download the Word file and open it in Word.
6. Reload on `/reviews/1?view=finished` (no 404).

**F5. Keep it awake and safe** (about 1 hour)
Set up the pinger. Check the access gate on the live site. Take the first `pg_dump` backup.
*Gate:* after 20 minutes of no visits, the first visit is fast. Without the access code the app shows nothing, and the API refuses upload and search calls.

**F6. Go live** (about 30 minutes)
Share the address and the access code. Watch the first days.

**Total:** about 2 days, mostly the code in F1.

**[B] F7. Add real workers (later):** create the CloudAMQP instance (free "Little Lemur" plan, region Singapore), set `RABBITMQ_URL` and `QUEUE_BACKEND=rabbitmq`, add the two Render workers, and upgrade the API to Starter. *Gate:* the CloudAMQP page shows the queues `lawphil` and `digests`, each with 1 consumer. The free plan has a small limit on open connections, so watch it.

---

## 10. After deploying: the check list

- [ ] `GET /health` is OK, and the API has not restarted in the last hour.
- [ ] Search is fast and the catalog is `ready`.
- [ ] Upload, check, finished reviewer, edit, ask a question, and Word download all work.
- [ ] A digest takes about 15 seconds, and the Court's text shows even if Gemini fails.
- [ ] RLS is on for every Supabase table.
- [ ] No secret is in the GitHub repo or the browser's network tab.
- [ ] The pinger is green.

## 11. Limits and risks

| Risk | What we do |
|---|---|
| The first visit is slow (the free service sleeps) | The pinger. Tell users the first load can take a minute. |
| Jobs stop when the service restarts | Recovery on start (change 2). All jobs are safe to run twice. |
| The Supabase project pauses | The pinger. A manual **Restore** if it happens. |
| The 500 MB database fills up | Uploads auto-delete after 7 days, a 5 MB limit, and a monthly size check. |
| The free Gemini quota runs out | A daily limit of 20 digests. The app already shows "The explanation service did not answer" and keeps the Court's text. |
| The public tables are exposed | RLS on every table. Checked in F2. |
| Anyone can use the quota | The access gate (change 8). |
| Free plan terms change | Check section 12 again before each release. |
| Lawphil blocks us | 1 request per second, a clear `User-Agent` with a contact, and **written permission** from the Arellano Law Foundation (https://lawphil.net/contactus.html). |
| A bad deploy | Render and Vercel can roll back to the last version in one click. Take a backup before any release that adds a database migration. |

**Cost:** Mode A is **$0 a month** (Vercel Hobby, Render free, Supabase free, Gemini free tier, UptimeRobot free). Mode B is about $21 a month on Render for the API and two workers, with CloudAMQP free to start.

**Rollback:** Vercel → Deployments → promote the previous one. Render → the service → Deploys → roll back. The database goes back only from a backup, because migrations only go forward.

## 12. Check before you start (free plans change)

- [ ] Render: the free web service (sleep time, hours, memory). Free background workers are still not offered.
- [ ] Supabase: the free plan (database size, pause after inactivity, backups, the IPv4 session pooler).
- [ ] Vercel: Hobby terms (non-commercial) and the request size limit.
- [ ] Google AI Studio: free-tier limits and the data-use terms.
- [ ] Does a `/health` call that queries the database count as activity for the Supabase pause?
- [ ] CloudAMQP (Mode B only): the free plan's connection and message limits.

## 13. Paid mode for about 2,000 case digests a month

The free setup (sections 1 to 12) is for a few students. The library with Bulk is meant for about 2,000 digests a month, which needs paid plans. Numbers below come from one measured run unless marked *estimate*.

**Measured (Marcos v. Manglapus, one run):** 7 AI calls, about 87K input and 56K output tokens, 208 s per digest, 89 of 94 sentences kept. A long decision with long dissents costs more.

| Part | Needs | Why |
|---|---|---|
| Gemini key | **Paid** (billing on) | The free tier allows only a few digests a day. *Estimate:* with current prices checked on the Google AI pricing page, 2,000 digests is on the order of a few hundred US dollars a month (about 87K input and 56K output tokens each; the output tokens, including thinking, cost most). Measure the real bill on the first 20 digests before promising a number. |
| Render | API + `worker-lawphil` + `worker-digests` (paid background workers) | Mode B of section 2. `QUEUE_BACKEND=rabbitmq`. |
| RabbitMQ | CloudAMQP (small paid plan) or a Render private service | The free plan's limits are enough for messages, but check connections. |
| Supabase | **Pro** (8 GB) | *Estimate:* about 150 KB per saved decision plus its digest, roughly 300 MB a month, 3 to 4 GB a year. Free is 500 MB. To grow slower, drop `raw_html` after parsing (it is the largest column) once `reparse` is not needed. |
| Vercel | Hobby is fine for the pages | Bulk files go up a few at a time (the 4.5 MB request limit). Hobby terms are non-commercial; use Pro if the client sells access. |

**Time.** One digest takes about 3 to 4 minutes of waiting on Gemini. The `digests` worker runs 4 threads, so about 70 to 80 digests an hour; 2,000 take about 26 to 29 hours of worker time spread over the month, and a 300-item bulk upload about 4 hours. More threads (`--threads 8`) is a one-line change if the Gemini quota allows it. Resolving a bulk item (Lawphil) is limited to 1 request per second by design: 2,000 cases is about 35 minutes of fetching.

**Budget guard.** `CASE_DIGEST_MONTHLY_LIMIT` (default 2,500) stops new digests with a plain message instead of overspending. When the month turns or the limit is raised, `python -m caselens.manage resume-digests` (also run at every restart) starts the waiting ones again. Set it from the budget: limit = budget / measured cost per digest.

**Gemini limits.** A rate-limited call (429) is retried after 20 s, 40 s and so on; if it still fails, the digest says the writing service did not answer and "Write it again" retries. Keep the worker threads within the paid tier's requests-per-minute.

**Other changes for paid mode**
- Run `alembic upgrade head` on the live database first (migrations 0010 to 0012 add subjects, main case, bulk and case digests). Take a backup first.
- Set `ACCESS_CODE`, `GEMINI_API_KEY`, `QUEUE_BACKEND=rabbitmq`, `RABBITMQ_URL`, `CASE_DIGEST_MONTHLY_LIMIT` on Render.
- `python -m caselens.manage reparse` once, so stored pages are read with the current parser.
- Shared library with no accounts: everyone with the access code sees every saved digest.
- Ask the Arellano Law Foundation for written permission before bulk reading of Lawphil; at this scale it matters more.

**Not yet measured:** a 50 to 300 item dry run with real timing and cost. Do that on the paid key before the client relies on the numbers.
