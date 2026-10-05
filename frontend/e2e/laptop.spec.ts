import { expect, test } from '@playwright/test'

import { expectAccessible, OFFICIAL_URL } from './helpers'

test.describe.configure({ mode: 'serial' })

test('the start page is Individual, the first line of the client’s sketch, and is accessible', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/individual/)
  await expect(page).toHaveTitle(/CaseLens/)
  await expect(page.getByRole('heading', { name: 'Individual', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: '1. Which case?' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '2. What subject?' })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Find it on Lawphil' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('tab', { name: 'Upload the file' })).toBeVisible()
  await expect(page.getByRole('group', { name: 'Subject Tags (optional)' }).getByRole('button')).toHaveCount(11)
  await expect(page.getByLabel('Topic scope')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Open the case' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Main' }).getByRole('link')).toHaveText([
    'Individual',
    'Bulk',
    'Case library',
    'How to use it',
  ])
  await expectAccessible(page)
})

test('the case page: summary, then the full text with working footnotes', async ({ page }) => {
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Review Center Association/ }).click()

  await expect(page.getByRole('heading', { level: 1 })).toContainText('Review Center Association of the Philippines')
  await expect(page.getByText('Petition granted').first()).toBeVisible()
  await expect(page.getByText('G.R. No. 180046')).toBeVisible()
  await expect(page.getByText(/WHEREFORE, we GRANT the petition/)).toBeVisible() // the ruling, verbatim
  await expect(page.getByText('Justice Carpio').first()).toBeVisible()
  await expect(page.getByText('Republic Act No. 7722')).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('link', { name: 'Read the full decision' }).click()
  await expect(page).toHaveURL(/\/cases\/\d+\/decision/)
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

  await page.getByRole('button', { name: 'Back to the case' }).click()
  await page.getByRole('tab', { name: /Footnotes \(42\)/ }).click()
  await expect(page.getByRole('listitem').filter({ hasText: 'Rollo, pp. 35-37' })).toBeVisible()
})

test('the case library lists, finds, and says when nothing matches', async ({ page }) => {
  await page.goto('/cases') // the old address
  await expect(page).toHaveURL(/\/library/)
  await page.getByRole('tab', { name: 'All cases' }).click()
  await expect(page.getByRole('table').getByRole('row').nth(1)).toBeVisible()

  await page.getByLabel('Filter your saved cases').fill('ermita')
  await expect(page).toHaveURL(/q=ermita/)
  await expect(page.getByRole('link', { name: /^Review Center Association/ })).toBeVisible()

  await page.getByLabel('Filter your saved cases').fill('zzzzqq')
  await expect(page.getByText('No saved case matches “zzzzqq”')).toBeVisible()
  await page.getByRole('button', { name: 'Clear the search' }).click()
  await expect(page.getByRole('table').getByRole('row').nth(1)).toBeVisible()
  await expectAccessible(page)
})

test('searching by G.R. number finds the case on Lawphil\'s list and opens it', async ({ page }) => {
  await page.goto('/library?tab=cases')
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
  await page.goto('/library?tab=cases')
  // A bad year
  await page.getByLabel('Find a case by name or G.R. number').fill('Ermita')
  await page.getByLabel('Year').fill('20')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page.getByText('Use a four-digit year, for example 2009.')).toBeVisible()
  await page.getByLabel('Find a case by name or G.R. number').fill('')
  await page.getByLabel('Year').fill('')
})

test('no browser errors or content-policy violations on any screen', async ({ page }) => {
  const problems: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(message.text())
  })
  page.on('pageerror', (error) => problems.push(error.message))

  for (const url of ['/library', '/guide', '/search?q=180046']) {
    await page.goto(url)
    await page.waitForLoadState('networkidle')
  }
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Review Center Association/ }).click()
  await page.getByRole('link', { name: 'Read the full decision' }).click()
  await page.getByRole('button', { name: 'Footnote 1', exact: true }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()

  expect(problems).toEqual([])
})

test('the theme the student picks is remembered and applied before the page paints', async ({ page }) => {
  await page.goto('/library?tab=cases')
  await page.getByRole('button', { name: /Switch to the dark theme/ }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)

  await page.reload()
  await expect(page.locator('html')).toHaveClass(/dark/)

  await page.getByRole('button', { name: /Switch to the light theme/ }).click()
  await expect(page.locator('html')).not.toHaveClass(/dark/)
})

test('the guide opens from the menu, is accessible, and the welcome card closes for good', async ({ page }) => {
  await page.goto('/individual')
  await expect(page.getByRole('heading', { name: 'New here? It takes four steps' })).toBeVisible()
  await page.getByRole('link', { name: 'Read the full guide' }).click()
  await expect(page).toHaveURL(/\/guide/)
  await expect(page.getByRole('heading', { name: 'How to use CaseLens', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'One case: Individual', level: 3 })).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Individual' }).click()
  await page.getByRole('button', { name: 'Got it' }).click()
  await expect(page.getByRole('heading', { name: 'New here? It takes four steps' })).toBeHidden()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Individual', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'New here? It takes four steps' })).toBeHidden()
})

test('the full decision is on its own page, an old text link still works, and there is a way back', async ({ page }) => {
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Review Center Association/ }).click()
  await expect(page.getByRole('tab', { name: 'Read the full text' })).toHaveCount(0) // no longer a tab on the case page
  await page.getByRole('link', { name: 'Read the full decision' }).click()
  await expect(page).toHaveURL(/\/cases\/\d+\/decision/)
  await expect(page.getByText(/WHEREFORE, we GRANT the petition/)).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('button', { name: 'Back to the case' }).click()
  await expect(page).toHaveURL(/\/cases\/\d+$/)

  const id = page.url().match(/\/cases\/(\d+)/)![1]
  await page.goto(`/cases/${id}?tab=text`)
  await expect(page).toHaveURL(/\/cases\/\d+\/decision/)
})

test('the full case downloads as a Word file from the case page', async ({ page }) => {
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Review Center Association/ }).click()
  const [one] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('link', { name: 'Download full case (Word)' }).click(),
  ])
  expect(one.suggestedFilename()).toBe('GR-180046-full-case.docx')
  const stream = await one.createReadStream()
  const first = await new Promise<Buffer>((resolve) => stream.once('data', resolve))
  expect(first.subarray(0, 2).toString()).toBe('PK') // a .docx is a zip file
})


test('the library is the client’s drawing: a subject rail, three columns, and one row per case', async ({ page }) => {
  await page.goto('/library?tab=cases')
  await expect(page.getByRole('heading', { name: 'Case library', level: 1 })).toBeVisible()
  await expect(page.getByRole('columnheader')).toHaveText(['Case', 'G.R. No., date and ponente', 'View / Download'])
  const rail = page.getByRole('navigation', { name: 'Filter by subject' })
  await expect(rail.getByRole('button', { name: /^All cases/ })).toBeVisible()
  await expect(rail.getByRole('button', { name: /^Constitutional Law/ })).toBeVisible()
  await expect(rail.getByRole('button', { name: /^Litigation/ })).toBeVisible() // the client's tag list
  await expectAccessible(page)

  // choosing a subject keeps only its cases, and the address says so (a link can be shared)
  await rail.getByRole('button', { name: /^Constitutional Law/ }).click()
  await expect(page).toHaveURL(/subject=\d+/)
  await expect(rail.getByRole('button', { name: /^Constitutional Law/ })).toHaveAttribute('aria-pressed', 'true')
})

test('upload with tags and a topic scope: the student lands on the review, one row per case, and the assistant is on the right', async ({ page }) => {
  await page.goto('/bulk')
  await page.getByRole('button', { name: 'Have G.R. numbers instead?' }).click()
  await page.getByLabel('G.R. numbers').fill('180046\nbanana\nG.R. No. 180046')
  await page.getByRole('button', { name: 'Constitutional Law' }).click()
  await expect(page.getByText('1 subject selected')).toBeVisible()
  await page.getByLabel('Topic scope').fill('Delegation of legislative power')
  await expect(page.getByText('31/300')).toBeVisible()
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Generate case digests' }).click()

  await expect(page).toHaveURL(/\/reviews\/\d+/)
  await expect(page.getByText('Topic scope: Delegation of legislative power')).toBeVisible()
  const cases = page.getByRole('navigation', { name: 'Cases in this upload' })
  await expect(cases.getByRole('button', { name: /Review Center Association/ })).toHaveCount(1, { timeout: 30_000 }) // the repeat is not a second row
  await expect(page.getByRole('region', { name: 'Not added' }).getByText('This is not a G.R. number, so it was skipped.')).toBeVisible()
  await expect(page.getByRole('region', { name: 'AI assistant' })).toBeVisible() // docked on the right at laptop width
  await expect(page.getByLabel('Your question')).toBeVisible()
  await expectAccessible(page)

  await page.getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'My uploads' }).click()
  await expect(page).toHaveURL(/\/library\?tab=uploads/)
  await expect(page.getByRole('tab', { name: 'My uploads' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('list', { name: 'My uploads' }).getByText('Topic scope: Delegation of legislative power').first()).toBeVisible()
  await expectAccessible(page)
  await page.goto('/reviews')
  await expect(page).toHaveURL(/\/library\?tab=uploads/) // the old address still works
})

test('the library files the uploaded case under its tag', async ({ page }) => {
  await page.goto('/library?tab=cases')
  await page.getByRole('navigation', { name: 'Filter by subject' }).getByRole('button', { name: /^Constitutional Law/ }).click()
  await expect(page.getByRole('link', { name: /^Review Center Association/ })).toBeVisible()
})

test('the case digest page asks for the digest and says it is being written', async ({ page }) => {
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Read the digest of Review Center Association/ }).click()
  await expect(page).toHaveURL(/\/cases\/\d+\/digest/)
  await expect(page.getByRole('link', { name: 'Back to the case' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Case digest', level: 1 })).toBeAttached()
  await expect(page.getByText('Writing the digest…').or(page.getByRole('article', { name: 'Case digest' }))).toBeVisible()
})

test('the library search also finds decisions on Lawphil that are not saved yet, and saves one when opened', async ({ page }) => {
  await page.goto('/library?q=Corona')
  const lawphil = page.getByRole('region', { name: 'Also on Lawphil, not saved yet' })
  await expect(lawphil).toBeVisible()
  await expect(lawphil.getByRole('button', { name: 'Open this case' }).first()).toBeVisible()
  await expectAccessible(page)
})

test('a case page has a Back button that returns to where the student was', async ({ page }) => {
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Review Center Association/ }).click()
  await expect(page).toHaveURL(/\/cases\/\d+$/)
  await page.getByRole('button', { name: 'Back' }).click()
  await expect(page).toHaveURL(/\/library\?.*q=Review/) // the same search, as the student left it

  await page.goto('/cases/1') // opened straight from a link
  await expect(page.getByRole('link', { name: 'Back to the Case library' })).toBeVisible()
})

test('an upload’s page has a Back button too', async ({ page }) => {
  await page.goto('/library?tab=uploads')
  await page.getByRole('list', { name: 'My uploads' }).getByRole('link', { name: /^Open / }).first().click()
  await expect(page).toHaveURL(/\/reviews\/\d+/)
  await page.getByRole('button', { name: 'Back' }).click()
  await expect(page).toHaveURL(/\/library\?tab=uploads/)
})

test('the Lawphil search is in the Case library only, and the results page lets the student search again or go back', async ({ page }) => {
  await page.goto('/bulk')
  await expect(page.getByRole('search', { name: 'Search Lawphil' })).toHaveCount(0)
  await page.goto('/library')
  const lawphil = page.getByRole('region', { name: 'Find any decision on Lawphil' })
  await lawphil.getByLabel('Find a case by name or G.R. number').fill('Ermita')
  await lawphil.getByRole('button', { name: 'Search' }).click()
  await expect(page).toHaveURL(/\/search\?q=Ermita/)
  await expect(page.getByLabel('Find a case by name or G.R. number')).toHaveValue('Ermita') // the search stays in the box
  await page.getByRole('button', { name: 'Back' }).click()
  await expect(page).toHaveURL(/\/library/)
  await expectAccessible(page)
})

test('Back after reading the full decision returns to the library, not to the decision again', async ({ page }) => {
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Review Center Association/ }).click()
  await page.getByRole('link', { name: 'Read the full decision' }).click()
  await expect(page).toHaveURL(/\/decision/)
  await page.getByRole('button', { name: 'Back to the case' }).click()
  await expect(page).toHaveURL(/\/cases\/\d+$/)
  await page.getByRole('button', { name: 'Back', exact: true }).click()
  await expect(page).toHaveURL(/\/library\?.*q=Review/) // no loop back to the decision

  await page.goto('/cases/1/decision') // opened straight from a link
  await expect(page.getByRole('link', { name: 'Back to the case' })).toHaveAttribute('href', '/cases/1')
})

test('the All cases tab says it lists saved cases only, and where to find the others', async ({ page }) => {
  await page.goto('/library?tab=cases')
  await expect(page.getByRole('heading', { name: 'Saved cases', level: 2 })).toBeVisible()
  await expect(page.getByText(/Only the cases already saved in CaseLens are listed here/)).toBeVisible()
})


test('Individual: find one case, say its subject, open it, and read its full decision first', async ({ page }) => {
  await page.goto('/individual')
  await page.getByLabel('Find a case by name or G.R. number').fill('180046')
  await page.getByRole('button', { name: 'Search' }).click()
  await page.getByRole('button', { name: /^Choose Review Center/ }).first().click()
  await expect(page.getByText(/^Your case: Review Center/)).toBeVisible()
  await page.getByRole('button', { name: 'Constitutional Law' }).click()
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Open the case' }).click()

  await expect(page).toHaveURL(/\/reviews\/\d+/)
  const read = page.getByRole('link', { name: 'Read the full decision' })
  await expect(read).toBeVisible({ timeout: 30_000 })
  await read.click()
  await expect(page).toHaveURL(/\/decision/)

  await page.goto('/library?tab=uploads')
  await expect(page.getByRole('list', { name: 'My uploads' }).getByText('Individual').first()).toBeVisible()
  await page.goto('/upload?tab=search')
  await expect(page).toHaveURL(/\/individual/) // the old address
})
