import AxeBuilder from '@axe-core/playwright'
import { expect, type Page } from '@playwright/test'
import path from 'node:path'

/** The real reviewer the client gave us: cites GR 180046 as April 2, 2010 (the Court says 2009). */
export const SAMPLE_PDF = path.resolve(import.meta.dirname, '../../backend/tests/fixtures/sample_case.pdf')
export const OFFICIAL_URL = 'https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html'

/** Fail on anything a screen reader or keyboard user would really trip over. */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  const serious = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(serious.map((v) => `${v.id}: ${v.help} (${v.nodes.length} place${v.nodes.length === 1 ? '' : 's'})`)).toEqual([])
}

/** No sideways scrolling: the page must fit the screen. */
export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(1)
}

/** Upload the sample reviewer and wait until the app has finished checking it. */
export async function uploadSampleAndWait(page: Page) {
  await page.goto('/')
  await page.locator('input[type=file]').setInputFiles(SAMPLE_PDF)
  await page.waitForURL(/\/reviews\/\d+/)
  await expect(page.getByText('Needs a look', { exact: true }).first()).toBeVisible({ timeout: 150_000 })
}

/** A plain reviewer (no digests yet) citing three decisions: Ermita (GR 180046), Tagaro (173931) and David (148263). */
export const REVIEWER_DOCX = path.resolve(import.meta.dirname, 'fixtures/reviewer.docx')
