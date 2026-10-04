import { expect, test } from '@playwright/test'

import { expectAccessible, OFFICIAL_URL, SAMPLE_PDF, uploadSampleAndWait } from './helpers'

test.describe.configure({ mode: 'serial' })

test('the start page offers one clear thing to do, and is accessible', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/CaseLens/)
  await expect(page.getByRole('heading', { name: 'Check a reviewer', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Drop your reviewer here' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Choose a file' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Main' }).getByRole('link')).toHaveText([
    'Check a reviewer',
    'My reviews',
    'Case library',
    'How to use it',
  ])
  await expectAccessible(page)
})

test('the sample reviewer: the wrong year is struck through beside the Court’s year', async ({ page }) => {
  await uploadSampleAndWait(page)

  // The signature move, on real data: what you wrote struck out, the Court's value beside it.
  await expect(page.locator('del', { hasText: 'April 2, 2010' })).toBeVisible()
  await expect(page.locator('ins', { hasText: 'April 2, 2009' })).toBeVisible()
  await expect(page.getByText('Different', { exact: true })).toBeVisible()

  // It never pretends to have checked what Lawphil does not contain.
  await expect(page.getByText('538 SCRA 428', { exact: true })).toBeVisible()
  await expect(page.getByText("Lawphil doesn't include it")).toBeVisible()

  // Every result links back to the official page.
  const lawphil = page.getByRole('link', { name: /Open on Lawphil/ })
  await expect(lawphil).toHaveAttribute('href', OFFICIAL_URL)
  await expect(lawphil).toHaveAttribute('target', '_blank')
  await expect(page.getByText('Informational only, not legal advice')).toBeVisible()

  await expectAccessible(page)
})

test('re-checking the same file is instant because the case is already saved', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type=file]').setInputFiles(SAMPLE_PDF)
  await page.waitForURL(/\/reviews\/\d+/)
  await expect(page.getByText('Needs a look', { exact: true }).first()).toBeVisible({ timeout: 10_000 })
})

test('the case page: summary, then the full text with working footnotes', async ({ page }) => {
  await uploadSampleAndWait(page)
  await page.getByRole('link', { name: 'Read the case' }).click()

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Review Center Association of the Philippines')
  await expect(page.getByText('Petition granted').first()).toBeVisible()
  await expect(page.getByText('G.R. No. 180046')).toBeVisible()
  await expect(page.getByText(/WHEREFORE, we GRANT the petition/)).toBeVisible() // the ruling, verbatim
  await expect(page.getByText('Justice Carpio').first()).toBeVisible()
  await expect(page.getByText('Republic Act No. 7722')).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('tab', { name: 'Read the full text' }).click()
  await expect(page).toHaveURL(/tab=text/)
  // 42 footnotes in the decision, plus 13 in Justice Brion's concurring opinion printed beneath it.
  await expect(page.getByRole('button', { name: /^Footnote \d+$/ })).toHaveCount(42 + 13, { timeout: 15_000 })
  await expect(page.getByRole('heading', { name: /Concurring opinion, Justice Brion/ })).toBeVisible()

  await page.getByRole('button', { name: 'Footnote 1', exact: true }).first().click()
  const popover = page.getByRole('dialog')
  await expect(popover).toContainText('Rollo, pp. 35-37')
  await expect(popover.getByRole('link', { name: /See this footnote on Lawphil/ })).toHaveAttribute('href', `${OFFICIAL_URL}#fnt1`)
  await page.keyboard.press('Escape')

  // The repaired apostrophe: the Court's text must not be damaged on its way in.
  await expect(page.getByText('OSG’s Technical Objections')).toBeVisible()
  await expect(page.locator('body')).not.toContainText('�')

  await page.getByRole('tab', { name: /Footnotes \(42\)/ }).click()
  await expect(page.getByRole('listitem').filter({ hasText: 'Rollo, pp. 35-37' })).toBeVisible()
})

test('the case library lists, finds, and says when nothing matches', async ({ page }) => {
  await page.goto('/cases')
  await expect(page.getByRole('link', { name: /Review Center Association of the Philippines/ })).toBeVisible()

  await page.getByLabel('Search your saved cases').fill('ermita')
  await expect(page).toHaveURL(/q=ermita/)
  await expect(page.getByRole('link', { name: /Review Center Association/ })).toBeVisible()

  await page.getByLabel('Search your saved cases').fill('zzzzqq')
  await expect(page.getByText('No saved case matches "zzzzqq"')).toBeVisible()
  await page.getByRole('button', { name: 'Clear the search' }).click()
  await expect(page.getByRole('link', { name: /Review Center Association/ })).toBeVisible()
  await expectAccessible(page)
})

test('searching by G.R. number finds the case on Lawphil\'s list and opens it', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Find a case by name or G.R. number').fill('G.R. No. 180046')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page).toHaveURL(/\/search/)
  await expect(page.getByText(/G\.R\. No\. 180046/).first()).toBeVisible()
  await page.getByRole('button', { name: 'Open this case' }).or(page.getByRole('link', { name: 'Read the case' })).first().click()
  await expect(page).toHaveURL(/\/cases\/\d+/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Review Center Association')
})

test('searching by case name lists matching decisions with their source', async ({ page }) => {
  await page.goto('/search?q=review%20center%20ermita')
  await expect(page.getByText(/1 decision on Lawphil's list matches/)).toBeVisible()
  await expect(page.getByRole('main').getByRole('link', { name: /Lawphil/ }).first()).toHaveAttribute('href', /lawphil\.net\/judjuris/)
  await expectAccessible(page)
})

test('a G.R. number typed into the address bar is kept', async ({ page }) => {
  await page.goto('/search?q=14744')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('14744')
})

test('mistakes get plain-language messages, not technical ones', async ({ page }) => {
  await page.goto('/')
  // A bad year
  await page.getByLabel('Find a case by name or G.R. number').fill('Ermita')
  await page.getByLabel('Year').fill('20')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page.getByText('Use a four-digit year, for example 2009.')).toBeVisible()
  await page.getByLabel('Find a case by name or G.R. number').fill('')
  await page.getByLabel('Year').fill('')

  // A file we cannot read
  await page.locator('input[type=file]').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('hello') })
  await expect(page.getByText(/We can read PDF and Word/)).toBeVisible()

  // A review that does not exist
  await page.goto('/reviews/99999999')
  await expect(page.getByRole('heading', { name: "We can't find that review" })).toBeVisible()
})

test('no browser errors or content-policy violations on any screen', async ({ page }) => {
  const problems: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(message.text())
  })
  page.on('pageerror', (error) => problems.push(error.message))

  for (const url of ['/', '/reviews', '/cases', '/search?q=180046']) {
    await page.goto(url)
    await page.waitForLoadState('networkidle')
  }
  await page.goto('/cases')
  await page.getByRole('link', { name: /Review Center Association/ }).click()
  await page.getByRole('tab', { name: 'Read the full text' }).click()
  await page.getByRole('button', { name: 'Footnote 1', exact: true }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()

  expect(problems).toEqual([])
})

test('the theme the student picks is remembered and applied before the page paints', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Switch to the dark theme/ }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)

  await page.reload()
  await expect(page.locator('html')).toHaveClass(/dark/)

  await page.getByRole('button', { name: /Switch to the light theme/ }).click()
  await expect(page.locator('html')).not.toHaveClass(/dark/)
})

test('the guide opens from the menu, is accessible, and the welcome card closes for good', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'New here? It takes four steps' })).toBeVisible()
  await page.getByRole('link', { name: 'Read the full guide' }).click()
  await expect(page).toHaveURL(/\/guide/)
  await expect(page.getByRole('heading', { name: 'How to use CaseLens', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Upload your reviewer', level: 3 })).toBeVisible()
  await expect(page.getByText('Matches the Court\'s record')).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Check a reviewer' }).click()
  await page.getByRole('button', { name: 'Got it' }).click()
  await expect(page.getByRole('heading', { name: 'New here? It takes four steps' })).toBeHidden()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Drop your reviewer here' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'New here? It takes four steps' })).toBeHidden()
})
