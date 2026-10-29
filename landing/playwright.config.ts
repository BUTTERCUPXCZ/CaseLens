import { defineConfig, devices } from '@playwright/test'

/** Browser checks of the built landing page (npm run build first), in the Chrome already on this machine. */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5181',
    channel: 'chrome',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'laptop', use: { viewport: { width: 1440, height: 900 } } },
    { name: 'phone', use: { ...devices['Pixel 7'], channel: 'chrome' } },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : { command: 'npm run preview', url: 'http://localhost:5181', reuseExistingServer: true, timeout: 60_000 },
})
