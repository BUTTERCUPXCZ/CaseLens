import { defineConfig, devices } from '@playwright/test'

/** End-to-end tests drive the real app against the real backend (docker compose up) and the
 *  real Lawphil, using the real sample reviewer. They use the Chrome already on this machine. */
export default defineConfig({
  testDir: './e2e',
  timeout: 180_000, // a first lookup of a case on Lawphil takes about a minute
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    channel: 'chrome',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'laptop', testMatch: /(laptop|digest)\.spec\.ts/, use: { viewport: { width: 1280, height: 800 } } },
    { name: 'phone', testMatch: /phone\.spec\.ts/, use: { ...devices['Pixel 7'], channel: 'chrome' } },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: true, timeout: 60_000 },
})
