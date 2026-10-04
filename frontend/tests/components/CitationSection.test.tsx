import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Citation } from '@/api/types'
import { CitationSection } from '@/features/reviews/CitationSection'

import needsALook from '../fixtures/api/upload-needs-a-look.json'
import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

const OFFICIAL_URL = 'https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html'

// The real response for the sample reviewer.
const real = needsALook.citations[0] as Citation
const show = (citation: Citation) => renderApp(<CitationSection citation={citation} uploadId={2} />)

describe('a citation that needs a look (the real sample reviewer)', () => {
  it('strikes the wrong date and shows the Court’s date beside it', async () => {
    await show(real)

    expect(await screen.findByText('Needs a look')).toBeInTheDocument()
    expect(screen.getByText('April 2, 2010').tagName).toBe('DEL')
    expect(screen.getByText('April 2, 2009').tagName).toBe('INS')
    expect(screen.getByText('Different')).toBeInTheDocument() // the meaning is in words, not only colour
  })

  it('shows the case by its readable name, and links to the case and to Lawphil', async () => {
    await show(real)

    expect(
      await screen.findByRole('heading', { name: 'Review Center Association of the Philippines v. Executive Secretary Eduardo Ermita et al.' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Read the case' })).toHaveAttribute('href', '/cases/1')
    const lawphil = screen.getByRole('link', { name: /Open on Lawphil/ })
    expect(lawphil).toHaveAttribute('href', OFFICIAL_URL)
    expect(lawphil).toHaveAttribute('target', '_blank')
    expect(lawphil).toHaveAttribute('rel', expect.stringContaining('noopener'))
  })

  it('says the page reference cannot be checked instead of guessing', async () => {
    await show(real)
    expect(await screen.findByText('538 SCRA 428')).toBeInTheDocument()
    expect(screen.getByText("Can't be checked")).toBeInTheDocument()
    expect(screen.getByText(/Lawphil doesn't include it/)).toBeInTheDocument()
  })
})

describe('the other four states (variations of the real citation; synthetic)', () => {
  const variant = (overrides: Partial<Citation>): Citation => ({ ...real, ...overrides })

  it('a match has no struck values and says so', async () => {
    await show(variant({ status: 'match', mismatches: {}, claimed: { ...real.claimed, date: '2009-04-02', year: 2009 } }))
    expect(await screen.findByText("Matches the Court's record")).toBeInTheDocument()
    expect(document.querySelector('del')).toBeNull()
    expect(screen.queryByText('Different')).toBeNull()
  })

  it('a citation still being checked shows progress and no actions', async () => {
    await show(variant({ status: 'pending', case: null, case_id: null, source_url: null, mismatches: {} }))
    expect(await screen.findByText('Checking…')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Read the case' })).toBeNull()
    expect(screen.queryByRole('link', { name: /Open on Lawphil/ })).toBeNull()
  })

  it('a source outage is explained without blaming the student', async () => {
    await show(variant({ status: 'error', case: null, case_id: null, source_url: null, mismatches: {}, message: 'https://lawphil.net failed after 4 attempts' }))
    expect(await screen.findByText("Couldn't check right now")).toBeInTheDocument()
    expect(screen.getByText(/Nothing is wrong with your file/)).toBeInTheDocument()
    expect(screen.queryByText(/failed after 4 attempts/)).toBeNull() // no technical text
  })

  const notFound = variant({
    status: 'not_found',
    case: null,
    case_id: null,
    source_url: null,
    mismatches: {},
    // the backend's real wording when the year is missing
    message: 'G.R. No. 180046 is not stored yet and no year was given to search for it. Add the year, or paste the Lawphil URL.',
  })

  it('a case that could not be found explains why and offers to paste the Lawphil link', async () => {
    await show(notFound)
    expect(await screen.findByText("Couldn't find this case")).toBeInTheDocument()
    expect(screen.getByText(/You didn't write the year/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Paste the case’s Lawphil link/)).toBeInTheDocument()
  })

  it('refuses a link that is not a Lawphil case page, in plain words', async () => {
    const user = userEvent.setup()
    await show(notFound)

    await user.type(await screen.findByLabelText(/Paste the case’s Lawphil link/), 'https://example.com/case.html')
    await user.click(screen.getByRole('button', { name: 'Check this case' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("That doesn't look like a Lawphil case link")
  })

  it('sends a good link to the backend and shows a plain error if the backend refuses it', async () => {
    const user = userEvent.setup()
    let sentBody: unknown
    server.use(
      http.post(`${API}/uploads/2/citations/${real.id}/attach`, async ({ request }) => {
        sentBody = await request.json()
        return HttpResponse.json({ detail: 'Not an official Lawphil case URL: x' }, { status: 400 })
      }),
    )
    await show(notFound)

    await user.type(await screen.findByLabelText(/Paste the case’s Lawphil link/), OFFICIAL_URL)
    await user.click(screen.getByRole('button', { name: 'Check this case' }))

    expect(await screen.findByText(/doesn't look like a Lawphil case link/)).toBeInTheDocument()
    expect(sentBody).toEqual({ url: OFFICIAL_URL })
  })
})

describe('structure', () => {
  it('has one labelled region per citation', async () => {
    await show(real)
    const article = await screen.findByRole('article')
    expect(within(article).getByRole('table')).toBeInTheDocument()
    expect(within(article).getAllByRole('row').length).toBeGreaterThanOrEqual(4)
  })
})
