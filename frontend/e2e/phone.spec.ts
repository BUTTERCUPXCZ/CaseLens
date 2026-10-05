import { expect, test } from '@playwright/test'

import { expectAccessible, expectNoHorizontalScroll } from './helpers'

// A real phone-sized screen (Pixel 7, 412 px wide). Students will look up cases on their phones.

test('the start page fits the phone and the menu opens', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Individual', level: 1 })).toBeVisible()
  await expectNoHorizontalScroll(page)

  await page.getByRole('button', { name: 'Open the menu' }).click()
  const nav = page.getByRole('navigation', { name: 'Main' })
  await expect(nav.getByRole('link', { name: 'Case library' })).toBeVisible()
  await nav.getByRole('link', { name: 'Case library' }).click()
  await expect(page).toHaveURL(/\/library/)
  await expectAccessible(page)
})

test('the case text is comfortable to read on a phone', async ({ page }) => {
  await page.goto('/library?tab=cases&q=Review%20Center')
  await page.getByRole('link', { name: /^Review Center Association/ }).click()
  await page.getByRole('link', { name: 'Read the full decision' }).click()
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

test('the guide fits the phone and nothing scrolls sideways', async ({ page }) => {
  await page.goto('/guide')
  await expect(page.getByRole('heading', { name: 'How to use CaseLens', level: 1 })).toBeVisible()
  await expectNoHorizontalScroll(page)
  await expectAccessible(page)
})


test('the library fits the phone: the subject list is a dropdown and each case is a card', async ({ page }) => {
  await page.goto('/library?tab=cases')
  await expect(page.getByRole('combobox', { name: 'Filter by subject' })).toBeVisible()
  await expectNoHorizontalScroll(page)
  await expectAccessible(page)
})

test('the upload screen and a review fit the phone; the assistant opens as a sheet', async ({ page }) => {
  await page.goto('/bulk')
  await expectNoHorizontalScroll(page)
  await expectAccessible(page)
  await page.getByRole('button', { name: 'Have G.R. numbers instead?' }).click()
  await page.getByLabel('G.R. numbers').fill('180046')
  await page.getByRole('button', { name: 'Generate case digests' }).click()
  await expect(page).toHaveURL(/\/reviews\/\d+/)
  await expect(page.getByRole('navigation', { name: 'Cases in this upload' }).getByRole('button').first()).toBeVisible({ timeout: 30_000 })
  await expectNoHorizontalScroll(page)
  await page.getByRole('button', { name: 'Ask the AI assistant' }).click()
  await expect(page.getByRole('dialog').getByLabel('Your question')).toBeVisible()
  await expectNoHorizontalScroll(page)
})
