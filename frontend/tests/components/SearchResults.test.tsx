import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { SearchResults } from '@/features/search/SearchResults'

import caseDetail from '../fixtures/api/case-180046.json'
import ermita from '../fixtures/api/catalog-search-ermita.json'
import empty from '../fixtures/api/catalog-search-empty.json'
import joint from '../fixtures/api/catalog-search-joint.json'
import noExact from '../fixtures/api/catalog-search-no-exact.json'
import people from '../fixtures/api/catalog-search-people.json'
import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

const OFFICIAL_URL = 'https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html'
const show = (q: string, year?: number, page = 0) =>
  renderApp(<SearchResults q={q} year={year} page={page} onPage={() => {}} />)
const respond = (body: object) => server.use(http.get(`${API}/catalog/search`, () => HttpResponse.json(body as Record<string, unknown>)))

describe('results from Lawphil’s own list (real responses)', () => {
  it('shows a decision as Lawphil lists it, with its number, date and a way to open it', async () => {
    await show('review center ermita')

    expect(await screen.findByText(/1 decision on Lawphil's list matches "review center ermita"/)).toBeInTheDocument()
    // the title is Lawphil's own text, typos included ("Associations", "Secretatry")
    expect(
      screen.getByText('Review Center Associations of the Philippines vs. Executive Secretatry Eduardo Ermita, et al.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/G\.R\. No\. 180046/)).toBeInTheDocument()
    expect(screen.getByText(/April 2, 2009/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open this case' })).toBeEnabled()
    const lawphil = screen.getByRole('link', { name: /Lawphil/ })
    expect(lawphil).toHaveAttribute('href', OFFICIAL_URL)
    expect(lawphil).toHaveAttribute('target', '_blank')
  })

  it('opening a case saves it and goes to its page', async () => {
    const user = userEvent.setup()
    let sent: unknown
    server.use(
      http.post(`${API}/cases/fetch`, async ({ request }) => {
        sent = await request.json()
        return HttpResponse.json(caseDetail)
      }),
    )
    const { router } = await show('review center ermita')

    await user.click(await screen.findByRole('button', { name: 'Open this case' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/cases/1')) // id 1 is in the real case response
    expect(sent).toEqual({ url: OFFICIAL_URL })
  })

  it('says what happened when opening fails, in plain words', async () => {
    const user = userEvent.setup()
    server.use(http.post(`${API}/cases/fetch`, () => HttpResponse.json({ detail: 'x failed after 4 attempts' }, { status: 502 })))
    await show('review center ermita')

    await user.click(await screen.findByRole('button', { name: 'Open this case' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("Lawphil isn't responding right now")
  })

  it('a case already in the library is read, not fetched again (synthetic: the real row marked as saved)', async () => {
    respond({ ...ermita, items: [{ ...ermita.items[0], in_library: true, case_id: 1 }] })
    await show('review center ermita')

    expect(await screen.findByText('In your library')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Read the case' })).toHaveAttribute('href', '/cases/1')
    expect(screen.queryByRole('button', { name: 'Open this case' })).toBeNull()
  })

  it('a joint decision says what it was decided together with', async () => {
    respond(joint)
    await show('212045')
    expect(await screen.findByText('Decided together with G.R. No. 212045')).toBeInTheDocument()
    expect(screen.getByText(/G\.R\. No\. 211972/)).toBeInTheDocument()
  })

  it('a number with no exact match says so before showing the numbers that start the same way', async () => {
    respond(noExact)
    await show('14744')
    expect(await screen.findByText("No decision numbered 14744 is on Lawphil's list. These numbers start the same way:")).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Open this case' })).toHaveLength(3)
  })

  it('an exact number does not show that warning', async () => {
    respond({ ...ermita, understood_as: 'number' })
    await show('180046')
    await screen.findByRole('button', { name: 'Open this case' })
    expect(screen.queryByText(/No decision numbered/)).toBeNull()
  })

  it('big result sets are paged and the total is honest', async () => {
    respond(people)
    await show('people philippines')
    expect(await screen.findByText(/10,073 decisions on Lawphil's list match/)).toBeInTheDocument()
    expect(screen.getByText(/Showing 1–20 of 10,073|Showing 1–5 of 10,073/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Earlier/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Later/ })).toBeEnabled()
  })
})

describe('no results', () => {
  it('names the search and says what to try (real empty response)', async () => {
    respond(empty)
    await show('zzzzqqqq')
    expect(await screen.findByText(`No decision on Lawphil's list matches "zzzzqqqq".`)).toBeInTheDocument()
    expect(screen.getByText(/write 'Commission on Elections' rather than 'Comelec'/)).toBeInTheDocument()
  })

  it('an old G.R. number explains the 1987 start and offers a year lookup and the paste-a-link way out', async () => {
    respond({ ...empty, understood_as: 'number', items: [] }) // synthetic: the real empty response, read as a number
    await show('14744', 1958)

    expect(await screen.findByText("G.R. No. 14744 isn't on Lawphil's list.")).toBeInTheDocument()
    expect(screen.getByText(/starts in 1987/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Look it up with the year 1958/ })).toHaveAttribute('href', expect.stringContaining('/lookup'))
    expect(screen.getByLabelText(/Paste the case’s Lawphil link/)).toBeInTheDocument()
  })

  it('while the list is still being read, an empty answer does not claim the case does not exist', async () => {
    respond({ ...empty, catalog: { state: 'building', entries: 0, months_read: 0, months_known: 0, percent: 0 } })
    await show('ermita')
    expect(await screen.findByText("Lawphil's case list isn't ready yet, so searches can't find anything for now.")).toBeInTheDocument()
    expect(screen.queryByText(/No decision on Lawphil's list matches/)).toBeNull()
  })
})

describe('progress of Lawphil’s list (synthetic variations of the real response)', () => {
  const withCatalog = (catalog: object) => respond({ ...ermita, catalog })

  it('shows how far the one-time read has got and that search already works', async () => {
    withCatalog({ state: 'building', entries: 15000, months_read: 212, months_known: 464, percent: 46 })
    await show('ermita')

    expect(await screen.findByText("Getting Lawphil's case list ready")).toBeInTheDocument()
    expect(screen.getByText(/212 of 464 months read \(46%\)/)).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: '212 of 464 months read' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open this case' })).toBeEnabled() // results still usable
  })

  it('offers to carry on when the read stopped part way, and asks the server to', async () => {
    const user = userEvent.setup()
    let started = false
    server.use(
      http.post(`${API}/catalog/build`, () => {
        started = true
        return HttpResponse.json({ started: true, catalog: { state: 'building', entries: 0, months_read: 0, months_known: 0, percent: 0 } })
      }),
    )
    withCatalog({ state: 'partial', entries: 20098, months_read: 264, months_known: 464, percent: 56 })
    await show('ermita')

    expect(await screen.findByText("Lawphil's case list is only partly read")).toBeInTheDocument()
    expect(screen.getByText(/stopped at 56%/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Carry on reading' }))
    await waitFor(() => expect(started).toBe(true))
  })

  it('shows nothing once the list is complete (the real response)', async () => {
    await show('review center ermita')
    await screen.findByRole('button', { name: 'Open this case' })
    expect(screen.queryByText(/case list/i)).toBeNull()
  })
})

describe('problems', () => {
  it('a failed search says what to do', async () => {
    server.use(http.get(`${API}/catalog/search`, () => HttpResponse.json({ detail: 'boom' }, { status: 500 })))
    await show('ermita')
    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText("The search didn't work")).toBeInTheDocument()
    expect(within(alert).getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
