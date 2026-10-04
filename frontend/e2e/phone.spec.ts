import { expect, test } from '@playwright/test'

import { expectAccessible, expectNoHorizontalScroll, uploadSampleAndWait } from './helpers'

// A real phone-sized screen (Pixel 7, 412 px wide). Students will check reviewers on their phones.

test('the start page fits the phone and the menu opens', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Drop your reviewer here' })).toBeVisible()
  await expectNoHorizontalScroll(page)

  await page.getByRole('button', { name: 'Open the menu' }).click()
  const nav = page.getByRole('navigation', { name: 'Main' })
  await expect(nav.getByRole('link', { name: 'Case library' })).toBeVisible()
  await nav.getByRole('link', { name: 'Case library' }).click()
  await expect(page).toHaveURL(/\/cases/)
  await expectAccessible(page)
})

test('the comparison reads top to bottom on a phone, and nothing scrolls sideways', async ({ page }) => {
  await uploadSampleAndWait(page)
  await expectNoHorizontalScroll(page)

  // Stacked: each row labels its two values instead of using a wide table.
  await expect(page.getByText('You wrote').first()).toBeVisible()
  await expect(page.getByText('The Court’s record says').first()).toBeVisible()
  await expect(page.locator('del', { hasText: 'April 2, 2010' })).toBeVisible()
  await expect(page.locator('ins', { hasText: 'April 2, 2009' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Read the case' })).toBeVisible()
  await expectAccessible(page)
})

test('the case text is comfortable to read on a phone', async ({ page }) => {
  await page.goto('/cases')
  await page.getByRole('link', { name: /Review Center Association/ }).click()
  await page.getByRole('tab', { name: 'Read the full text' }).click()
  await expectNoHorizontalScroll(page)

  const marker = page.getByRole('button', { name: 'Footnote 1', exact: true }).first()
  await marker.scrollIntoViewIfNeeded()
  await marker.tap()
  await expect(page.getByRole('dialog')).toContainText('Rollo, pp. 35-37')
  await expectNoHorizontalScroll(page)
})

test('search results fit the phone and are accessible', async ({ page }) => {
  await page.goto('/search?q=people%20philippines')
  await expect(page.getByText(/decisions on Lawphil's list match/)).toBeVisible()
  await expectNoHorizontalScroll(page)
  await expectAccessible(page)
})

test('the finished reviewer fits the phone and stays usable', async ({ page }) => {
  await page.goto('/reviews')
  await page.getByRole('link', { name: /reviewer\.docx|my-reviewer\.docx/ }).first().click()
  await page.getByRole('tab', { name: 'Finished reviewer' }).click()
  await expect(page.getByRole('article').first()).toBeVisible({ timeout: 60_000 })
  await expectNoHorizontalScroll(page)
  await expectAccessible(page)
})
