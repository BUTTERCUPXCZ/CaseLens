# CaseLens landing page

The public front page for CaseLens: what it does, the app at work on a real decision (an interactive replica, no server), and a
search box that opens the case in the app. A separate Vite + React + shadcn/ui project; nothing here is shared with `frontend/`
at build time.

```bash
npm install
npm run dev          # http://localhost:5180
npm test             # the replica's steps (Vitest)
npm run build && npx playwright test   # accessibility, widths, search, replica (uses the Chrome on this machine)
```

- `VITE_APP_URL`: where "Open CaseLens" and the search go (default `https://caselens.vercel.app`).
- Wording lives in `src/copy.ts`. Every claim traces to `README.md`, `docs/TECHNICAL_DOC.md` or the code; no testimonials,
  prices or user counts.
- Design tokens are copied from `frontend/src/index.css` (marked at the top of `src/index.css`): change a token there, change it here.
- The replica's sample is G.R. No. 180046, read from `backend/tests/fixtures/gr_180046_2009.html` with the app's own parser
  (`src/demo/sample.ts`).
- Deploy as its own Vercel project with root `landing/` (`vercel.json` sets the same security headers as the app).
