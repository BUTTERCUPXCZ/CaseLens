import AxeBuilder from '@axe-core/playwright'
import { expect, type Page } from '@playwright/test'

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
