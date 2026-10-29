import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

/** Fail on anything a screen reader or keyboard user would really trip over. */
async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(serious.map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(' | ')})`)).toEqual([])
}

async function overflow(page: Page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
}

test('the page has no serious accessibility problems, light and dark', async ({ page }) => {
  // Checked as it rests: the reveal animation's half-faded moments are not what anyone reads.
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Switch to the dark theme' }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await expectAccessible(page)
})

test('every part that animates in ends up shown, even when a link jumps past it', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('html')).toHaveClass(/js-reveal/)
  await page.locator('#how').scrollIntoViewIfNeeded()
  await expect(page.locator('#how [data-reveal]').first()).toHaveAttribute('data-revealed', '')
  await page.goto('/#limits')
  await page.evaluate(() => window.scrollBy(0, 1))
  await expect(page.locator('#check [data-reveal]').first()).toHaveAttribute('data-revealed', '')
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await expect(page.locator('[data-reveal]:not([data-revealed])')).toHaveCount(0)
})

test('with reduced motion nothing waits to appear', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await expect(page.locator('html')).not.toHaveClass(/js-reveal/)
  await expect(page.locator('#downloads h2')).toHaveCSS('opacity', '1')
})

test('light is the default, and the dark choice is remembered', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/')
  await expect(page.locator('html')).not.toHaveClass(/dark/)
  await page.getByRole('button', { name: 'Switch to the dark theme' }).click()
  await page.reload()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await page.getByRole('button', { name: 'Switch to the light theme' }).click()
  await expect(page.locator('html')).not.toHaveClass(/dark/)
})

test('nothing scrolls sideways at common widths', async ({ page }, info) => {
  test.skip(info.project.name !== 'laptop', 'widths are set here')
  for (const width of [320, 390, 768, 1024, 1280, 1600]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    expect(await overflow(page), `at ${width}px`).toBeLessThanOrEqual(1)
  }
})

test('the search opens the case in the app', async ({ page }) => {
  await page.route('**/search?**', (route) => route.fulfill({ body: 'app', contentType: 'text/plain' }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Open', exact: true }).click()
  await expect(page.getByText('Type a case name or a G.R. number first.')).toBeVisible()
  await page.getByRole('searchbox', { name: 'Case name or G.R. No.' }).fill('180046')
  await Promise.all([page.waitForURL(/\/search\?q=180046$/), page.getByRole('searchbox', { name: 'Case name or G.R. No.' }).press('Enter')])
})

test('each step of the sample can be opened, and a sentence shows its paragraph', async ({ page }) => {
  await page.goto('/')
  const steps = page.getByRole('list', { name: 'Steps of the sample' })
  await steps.getByRole('button', { name: /Read the digest/ }).click()
  await expect(steps.getByRole('button', { name: /Read the digest/ })).toHaveAttribute('aria-current', 'step')
  await expect(page).toHaveURL(/#demo-digest$/)
  await page.getByRole('button', { name: /never be regulated/ }).click()
  await expect(page.getByText('Struck out. Dropped: paragraph 103 does not say this.').filter({ visible: true })).toBeVisible()
  await steps.getByRole('button', { name: /Download/ }).click()
  await page.getByRole('button', { name: /Full case digest/ }).click()
  await expect(page.getByText('Word file, ready for your reviewer')).toBeVisible()
  await page.goBack()
  await expect(steps.getByRole('button', { name: /Read the digest/ })).toHaveAttribute('aria-current', 'step')
})

test('with reduced motion the sample waits, open on the digest', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  const steps = page.getByRole('list', { name: 'Steps of the sample' })
  await expect(steps.getByRole('button', { name: /Read the digest/ })).toHaveAttribute('aria-current', 'step')
  await expect(page.getByRole('button', { name: 'Play', exact: true })).toBeVisible()
})

test('the sample plays by itself and stops at the end', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('figure', { name: /CaseLens at work/ }).scrollIntoViewIfNeeded()
  const steps = page.getByRole('list', { name: 'Steps of the sample' })
  await expect(steps.getByRole('button', { name: /Write and check/ })).toHaveAttribute('aria-current', 'step', { timeout: 10_000 })
  await expect(page.getByRole('button', { name: 'Play again' })).toBeVisible({ timeout: 30_000 })
})

/** Screenshots for the design review: CAPTURE=1 npx playwright test -g capture */
test('capture', async ({ page }, info) => {
  test.skip(!process.env.CAPTURE, 'only when asked')
  const dir = '.impeccable/review'
  const name = info.project.name === 'laptop' ? 'desktop' : 'mobile'
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await page.screenshot({ path: `${dir}/${name}.png`, fullPage: true })
  await page.screenshot({ path: `${dir}/${name}-first.png` })
  const steps = page.getByRole('list', { name: 'Steps of the sample' })
  for (const step of ['Find the case', 'Write and check', 'Read the digest', 'Download']) {
    await steps.getByRole('button', { name: new RegExp(step) }).click()
    await page.waitForTimeout(500)
    await page.getByRole('figure', { name: /CaseLens at work/ }).screenshot({ path: `${dir}/${name}-scene-${step.split(' ')[0].toLowerCase()}.png` })
  }
  await page.getByRole('button', { name: 'Switch to the dark theme' }).click()
  await page.screenshot({ path: `${dir}/${name}-dark.png`, fullPage: true })
})
