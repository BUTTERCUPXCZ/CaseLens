import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { GrSearch } from '@/components/GrSearch'
import { isValidYear, parseGrNumber } from '@/features/search/grNumber'

import { renderApp } from '../utils'

const BOX = 'Find a case by name or G.R. number'

describe('the search box in the header', () => {
  it('goes to the results with the words and the year', async () => {
    const user = userEvent.setup()
    const { router } = await renderApp(<GrSearch />)

    await user.type(await screen.findByLabelText(BOX), 'review center ermita')
    await user.type(screen.getByLabelText('Year'), '2009')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/search'))
    expect(router.state.location.search).toEqual({ q: 'review center ermita', year: 2009, page: undefined })
  })

  it('takes a G.R. number as typed, and works without a year', async () => {
    const user = userEvent.setup()
    const { router } = await renderApp(<GrSearch />)
    await user.type(await screen.findByLabelText(BOX), 'G.R. No. 180046')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/search'))
    expect(router.state.location.search).toEqual({ q: 'G.R. No. 180046', year: undefined, page: undefined })
  })

  it.each([
    ['', '', 'Type a case name or a G.R. number, for example Ermita or 180046.'],
    ['   ', '', 'Type a case name or a G.R. number, for example Ermita or 180046.'],
    ['ermita', '20x9', 'Use a four-digit year, for example 2009.'],
    ['ermita', '1800', 'Use a four-digit year, for example 2009.'],
  ])('refuses text %j with year %j: "%s"', async (q, year, message) => {
    const user = userEvent.setup()
    const { router } = await renderApp(<GrSearch />)
    const box = await screen.findByLabelText(BOX)
    if (q) await user.type(box, q)
    if (year) await user.type(screen.getByLabelText('Year'), year)

    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/') // did not navigate
  })
})

describe('parseGrNumber (used to tell a typed number from words)', () => {
  it.each([
    ['180046', '180046'],
    ['G.R. No. 180046', '180046'],
    ['gr no 180046', '180046'],
    ['  180046  ', '180046'],
    ['L-12345', 'L-12345'],
    ['l12345', 'L-12345'],
    ['G.R. No. L-10854', 'L-10854'],
  ])('%j -> %j', (typed, expected) => expect(parseGrNumber(typed)).toBe(expected))

  it.each(['', '12', 'abc', 'ermita', '12345678', 'G.R. No.', '180046x'])('treats %j as words, not a number', (typed) =>
    expect(parseGrNumber(typed)).toBeNull(),
  )

  it('accepts only sensible years', () => {
    const now = new Date(2026, 9, 3)
    expect(isValidYear('2009', now)).toBe(true)
    expect(isValidYear('1900', now)).toBe(true)
    expect(isValidYear('2027', now)).toBe(false)
    expect(isValidYear('209', now)).toBe(false)
  })
})
