# CaseLens frontend

The web app for law students: drop a reviewer, see which cited cases match the Supreme Court's
record, and read the official decisions with their footnotes. React 19 + TypeScript, shadcn/ui,
Tailwind v4 and TanStack (Router, Query, Form, Table). The backend is in [`../backend`](../backend).

Product context for design decisions is in [`PRODUCT.md`](PRODUCT.md). The design direction
("the proofread reviewer") is recorded in `.impeccable/surfaces/`.

## Run it

With the whole stack (recommended):

```bash
cd ../backend && docker compose up -d --build   # api, workers, db, rabbitmq, and this app
# open http://localhost:8080
```

For development (hot reload), with the backend already running on port 8000:

```bash
npm install
npm run dev          # http://localhost:5173
```

The browser only ever talks to its own origin. In development Vite forwards `/api/*` to
`http://localhost:8000` (prefix removed); in production nginx does the same. The API therefore
needs no CORS setup. Change the dev target with `VITE_API_PROXY_TARGET`.

## Scripts

| Command | |
|---|---|
| `npm run dev` | dev server with hot reload |
| `npm run build` | type-check and build into `dist/` |
| `npm run typecheck` / `npm run lint` | TypeScript and ESLint |
| `npm test` | 100+ unit and component tests (Vitest, Testing Library, MSW) |
| `npm run e2e` | end-to-end tests in real Chrome against the **real** backend and Lawphil |
| `npm run api:types` | regenerate `src/api/schema.d.ts` from the running backend's OpenAPI |
| `npm run detect` | Impeccable's deterministic design checks on `src/` |

`E2E_BASE_URL=http://127.0.0.1:8080 npm run e2e` tests the production container instead of the
dev server. The end-to-end tests upload the real sample reviewer (`../backend/tests/fixtures/sample_case.pdf`).

## How it is organised

```
src/
  routes/       one file per screen (TanStack Router, file-based); routes only compose
  features/     reviews/ cases/ upload/ search/: components and pure logic per feature
  components/   app shell (sidebar, header search), states, shadcn components in ui/
  api/          typed client, query definitions, mutations; schema.d.ts is GENERATED
  lib/          copy.ts (all student-facing wording), format.ts, theme.ts
tests/          unit + component tests; fixtures/api/*.json are REAL backend responses
e2e/            Playwright tests (laptop and phone size, with accessibility scans)
```

Decisions worth knowing:

- **Plain language lives in one file.** Every sentence about a result ("Needs a look", "We couldn't find
  this case…") and every error message is in `src/lib/copy.ts`, so wording stays consistent and reviewable.
  Backend messages are never shown raw.
- **Types come from the backend.** `schema.d.ts` is generated from `/openapi.json`; statuses are exact
  string unions, so the compiler flags a status the UI forgot to handle.
- **Official text is shown exactly as stored.** The reader (`features/cases/readerBlocks.ts`) changes only
  styling: every line becomes one block, nothing is added, removed or reworded.
- **Polling is bounded.** A review is re-fetched every 3 s only while it is `processing`; a G.R. search
  stops after about two minutes and offers the "paste the Lawphil link" way out.
- **The red pen.** When a citation differs, what the student wrote is struck through (`<del>`, red) and the
  Court's value is highlighted beside it (`<ins>`). The words "Same", "Different", "Can't be checked"
  carry the meaning too, so it never depends on colour.

## Design tooling (Impeccable)

The project uses [Impeccable](https://github.com/pbakaus/impeccable), installed into `.claude/` with
`npx impeccable install --providers=claude --scope=project`. In Claude Code (restart after install):
`/impeccable critique`, `/impeccable audit`, `/impeccable polish`, `/impeccable clarify <screen>`.
`npm run detect` runs the same deterministic rules without any AI. It currently reports zero findings
on the source and on every rendered page at desktop and phone width.

## Things that tripped us up (so they do not again)

- Tailwind's dev server remembers every class it has ever seen until restarted; restart it when the
  design detector reports styles you already removed.
- Zod 4 compiles validators with `new Function`, which the production Content-Security-Policy forbids;
  `src/zod-setup.ts` turns that off and must stay the first import in `main.tsx`.
- TanStack Table is pinned to v8 (v9 is a rewrite and shadcn's recipes target v8); TypeScript is 6.0
  because `typescript-eslint` does not support 7 yet.
