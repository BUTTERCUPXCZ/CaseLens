import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'

import { expectAccessible, expectNoHorizontalScroll, REVIEWER_DOCX } from './helpers'

// The whole promise of the app, end to end on the real stack: upload a reviewer, get it back with a digest box
// under each case it cites, change what you want, and download it as a Word file.
test('upload a reviewer, edit the finished version, download it as Word', async ({ page }, testInfo) => {
  test.setTimeout(240_000)
  await page.goto('/')
  await page.locator('input[type=file]').setInputFiles(REVIEWER_DOCX)
  await page.waitForURL(/\/reviews\/\d+/)

  await page.getByRole('tab', { name: 'Finished reviewer' }).click()
  const ermita = page.getByRole('article', { name: /Review Center/ })
  await expect(ermita).toBeVisible({ timeout: 120_000 })
  // by default only the boxes are shown, each saying where it sits in the reviewer
  await expect(page.getByText(/In your reviewer, under “I\. Legislative power Section 1:”/)).toBeVisible()
  // with the reviewer text switched on, the box sits right after the paragraph that cites the case
  await page.getByRole('button', { name: 'With my reviewer text' }).click()
  const order = await page.evaluate(() => {
    const text = (s: string) => [...document.querySelectorAll('p')].find((p) => p.textContent?.includes(s))
    const box = document.querySelector('article')
    const cites = text('See Review Center v Ermita')
    const next = text('Explanation: Legislative power')
    return Boolean(cites && box && next && cites.compareDocumentPosition(box) & 4 && box.compareDocumentPosition(next) & 4)
  })
  expect(order).toBe(true)

  // the Court's own text is there at once; the written answers arrive by themselves
  await expect(ermita.getByRole('region', { name: 'Ruling' })).toContainText('WHEREFORE, we GRANT the petition')
  const topic = ermita.getByRole('region', { name: 'Topic explained' })
  await expect(topic.getByText('Drafted from the decision. Check it.')).toBeVisible({ timeout: 120_000 })

  // pick the Court's paragraph for the Doctrine
  await ermita.getByRole('button', { name: 'Pick paragraphs for Doctrine' }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: /The President has no inherent or delegated legislative power/ }).click()
  await dialog.getByRole('button', { name: 'Use this paragraph' }).click()
  await expect(ermita.getByRole('region', { name: 'Doctrine' })).toContainText('The President has no inherent or delegated legislative power')
  await expect(ermita.getByRole('region', { name: 'Doctrine' }).getByText('Paragraphs you picked')).toBeVisible()

  // rewrite the explanation in the student's own words
  await topic.getByRole('button', { name: 'Edit Topic explained' }).click()
  await topic.getByRole('textbox', { name: 'Edit Topic explained' }).fill('My own explanation of the topic.')
  await topic.getByRole('button', { name: 'Save' }).click()
  await expect(topic.getByText('Written by you')).toBeVisible()
  await expectAccessible(page)
  await expectNoHorizontalScroll(page)
  await page.screenshot({ path: testInfo.outputPath('finished-reviewer.png'), fullPage: false })

  // the Word file has the student's text, the box, and their edits
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name: /Download as Word/ }).click()])
  expect(download.suggestedFilename()).toBe('reviewer-with-digests.docx')
  const file = testInfo.outputPath('finished.docx')
  await download.saveAs(file)
  const xml = execFileSync('unzip', ['-p', file, 'word/document.xml'], { maxBuffer: 50 * 1024 * 1024 }).toString()
  expect(xml).toContain('Constitutional Law Reviewer') // the student's own text, untouched
  expect(xml).toContain('My own explanation of the topic.') // their edit
  expect(xml).toContain('The President has no inherent or delegated legislative power') // the picked Court paragraph, word for word
  expect(xml).toContain('Digest 1: Facts, Issue, Ruling and Doctrine')
  expect(xml).toContain('<w:tbl>')
})

// The question panel belongs to the Finished reviewer tab of one review. It must not show anywhere else.
test('the question panel appears only on the Finished reviewer tab', async ({ page }) => {
  const fixture = (name: string) => JSON.parse(readFileSync(`tests/fixtures/api/${name}.json`, 'utf8'))
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url()).pathname.replace('/api', '')
    const json = (body: unknown) => route.fulfill({ json: body })
    if (url === '/uploads/3') return json({ ...fixture('upload-needs-a-look'), id: 3 })
    if (url === '/uploads/3/document') return json(fixture('finished-reviewer'))
    if (url.startsWith('/digests/')) return json({ ...fixture('digest-ermita'), id: Number(url.split('/')[2]) })
    return route.fallback()
  })
  const panel = page.getByRole('region', { name: 'Ask your own question' })

  await page.goto('/reviews/3?view=finished')
  await expect(page.getByRole('article').first()).toBeVisible()
  await expect(panel).toBeVisible() // here, and only here

  await page.getByRole('tab', { name: 'Check results' }).click()
  await expect(panel).toHaveCount(0)

  for (const url of ['/', '/reviews', '/cases', '/search?q=180046', '/reviews/3']) {
    await page.goto(url)
    await page.waitForLoadState('networkidle')
    await expect(panel).toHaveCount(0)
  }
})
