import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { AssistantPanel } from '@/features/assistant/AssistantPanel'
import { reviewTitle } from '@/features/reviews/reviewTitle'

import progress from '../fixtures/api/bulk-progress.json'
import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

const question = (over: Record<string, unknown>) => ({
  id: 1, case_id: 1, batch_id: 3, question: 'What did the Court decide?', state: 'ready', sentences: [], error: null, created_at: '2026-10-05T09:00:00Z', ...over,
})

describe('naming a review', () => {
  it('uses the first files or numbers given, and says how many more there are', () => {
    const bulk = { ...progress, labels: ['marcos.pdf', '180046', 'banana'], cases: [] } as never
    expect(reviewTitle(bulk)).toBe('marcos.pdf, 180046, banana and 2 more') // no case found yet: what was uploaded
    expect(reviewTitle({ ...progress, labels: [], cases: [] } as never)).toBe('Upload #1')
    const found = { ...progress, cases: [{ name: 'Marcos v. Manglapus', gr_no: '88211' }, { name: 'Review Center v. Ermita', gr_no: '180046' }], case_total: 3 } as never
    expect(reviewTitle(found)).toBe('Marcos v. Manglapus and 2 more') // once found: by its cases
  })
})

describe('the AI assistant panel (synthetic answers in the real shape)', () => {
  it('shows each question with its checked answer, the paragraphs it rests on, and that it is a draft', async () => {
    server.use(
      http.get(`${API}/cases/:id/questions`, () =>
        HttpResponse.json([question({ sentences: [{ text: 'The Court granted the petition.', cites: ['P120', 'P121'] }] })]),
      ),
    )
    await renderApp(<AssistantPanel caseId={1} caseName="Review Center v. Ermita" batchId={3} />)
    const panel = screen.getByRole('region', { name: 'AI assistant' })
    expect(within(panel).getByText('About Review Center v. Ermita')).toBeInTheDocument()
    expect(await within(panel).findByText('The Court granted the petition.')).toBeInTheDocument()
    expect(within(panel).getByText('Based on decision paragraphs 120, 121')).toBeInTheDocument()
    expect(within(panel).getByText('Drafted from the decision. Check it.')).toBeInTheDocument()
  })

  it('says plainly when the decision does not say enough, and when it could not answer', async () => {
    server.use(
      http.get(`${API}/cases/:id/questions`, () =>
        HttpResponse.json([question({ id: 1 }), question({ id: 2, question: 'Second?', state: 'failed', error: 'The writing service did not answer. Ask again in a moment.' })]),
      ),
    )
    await renderApp(<AssistantPanel caseId={1} caseName="X" batchId={3} />)
    expect(await screen.findByText(/does not say enough to answer this/)).toBeInTheDocument()
    expect(screen.getByText(/did not answer\. Ask again/)).toBeInTheDocument()
  })

  it('sends the question with its review, shows it as being answered, and clears the box', async () => {
    const user = userEvent.setup()
    let sent: unknown
    let asked = false
    server.use(
      http.get(`${API}/cases/:id/questions`, () => HttpResponse.json(asked ? [question({ state: 'pending', question: 'Why?' })] : [])),
      http.post(`${API}/cases/:id/questions`, async ({ request }) => {
        sent = await request.json()
        asked = true
        return HttpResponse.json(question({ state: 'pending', question: 'Why?' }), { status: 202 })
      }),
    )
    await renderApp(<AssistantPanel caseId={1} caseName="X" batchId={3} />)
    expect(await screen.findByText(/Ask anything about this case/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled()
    await user.type(screen.getByLabelText('Your question'), 'Why?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    await waitFor(() => expect(sent).toEqual({ question: 'Why?', batch_id: 3 }))
    expect(await screen.findByText('Writing the answer…')).toBeInTheDocument()
    expect(screen.getByLabelText('Your question')).toHaveValue('')
  })

  it('waits for a case to be chosen', async () => {
    await renderApp(<AssistantPanel caseId={null} caseName={null} batchId={3} />)
    expect(screen.getByText('Choose a case to ask about it.')).toBeInTheDocument()
    expect(screen.getByLabelText('Your question')).toBeDisabled()
  })
})

describe('"My uploads" in the Case library', () => {
  const upload = (over: Record<string, unknown>) => ({ ...progress, labels: ['sample case.pdf'], topic_scope: '', cases: [], case_total: 0, ...over })

  it('names each upload by its cases, with their G.R. numbers, and says what was uploaded', async () => {
    const { UploadList } = await import('@/features/reviews/UploadList')
    server.use(
      http.get(`${API}/bulk`, () =>
        HttpResponse.json([
          upload({ id: 9, labels: ['sample case.pdf'], cases: [{ name: 'Review Center v. Ermita', gr_no: '180046' }], case_total: 1 }),
          upload({ id: 8, labels: ['88211', '180046'], cases: [{ name: 'Marcos v. Manglapus', gr_no: '88211' }, { name: 'Review Center v. Ermita', gr_no: '180046' }], case_total: 2 }),
        ]),
      ),
    )
    await renderApp(<UploadList />)
    const list = await screen.findByRole('list', { name: 'My uploads' })
    expect(within(list).getByRole('link', { name: 'Review Center v. Ermita' })).toHaveAttribute('href', '/reviews/9')
    expect(within(list).getByText('G.R. No. 180046')).toBeInTheDocument()
    expect(within(list).getByText(/Uploaded: sample case\.pdf/)).toBeInTheDocument()
    const two = within(list).getByRole('list', { name: 'Cases in Marcos v. Manglapus and 1 more' })
    expect(within(two).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Marcos v. Manglapus · G.R. No. 88211', 'Review Center v. Ermita · G.R. No. 180046'])
  })

  it('names each upload, says how it is doing in plain words, and has one clear way in', async () => {
    const { UploadList } = await import('@/features/reviews/UploadList')
    server.use(
      http.get(`${API}/bulk`, () =>
        HttpResponse.json([
          upload({ id: 7, finished: false, counts: { ...progress.counts, queued: 1, found: 0 } }),
          upload({ id: 6, labels: ['marcos.docx'], topic_scope: 'Presidential Powers', counts: { ...progress.counts, total: 1, found: 1, duplicate: 0, not_found: 0, unreadable: 0, digests_ready: 1, digests_pending: 0 } }),
        ]),
      ),
    )
    await renderApp(<UploadList />)
    const list = await screen.findByRole('list', { name: 'My uploads' })
    expect(within(list).getByText('Getting the cases…')).toBeInTheDocument()
    expect(within(list).getByText('Ready')).toBeInTheDocument()
    expect(within(list).getByText(/Topic scope: Presidential Powers/)).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: 'Open marcos.docx' })).toHaveAttribute('href', '/reviews/6')
  })

  it('says what to do when nothing was uploaded yet', async () => {
    const { UploadList } = await import('@/features/reviews/UploadList')
    server.use(http.get(`${API}/bulk`, () => HttpResponse.json([])))
    await renderApp(<UploadList />)
    expect(await screen.findByText('Nothing uploaded yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Individual' })).toHaveAttribute('href', '/individual')
  })

  it('asks before deleting, and keeps the cases', async () => {
    const user = userEvent.setup()
    let deleted = false
    const { UploadList } = await import('@/features/reviews/UploadList')
    server.use(
      http.get(`${API}/bulk`, () => HttpResponse.json(deleted ? [] : [upload({ id: 6 })])),
      http.delete(`${API}/bulk/:id`, () => ((deleted = true), new HttpResponse(null, { status: 204 }))),
    )
    await renderApp(<UploadList />)
    await user.click(await screen.findByRole('button', { name: /^Delete sample case\.pdf/ }))
    expect(screen.getByRole('dialog')).toHaveTextContent('The cases and their digests stay in the Case library.')
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(await screen.findByText('Nothing uploaded yet')).toBeInTheDocument()
  })
})

describe('the state of an upload in words', () => {
  it('goes from getting the cases, to writing the digests, to ready, and says when something could not be added', async () => {
    const { uploadState } = await import('@/features/reviews/uploadState')
    const base = { ...progress } as never as import('@/api/types').Bulk
    const c = progress.counts
    expect(uploadState({ ...base, finished: false }).label).toBe('Getting the cases…')
    expect(uploadState({ ...base, counts: { ...c, digests_pending: 2, digests_ready: 0 } }).label).toBe('Writing the digests (0 of 2 ready)…')
    expect(uploadState({ ...base, counts: { ...c, digests_pending: 0, digests_ready: 2 } }).label).toBe('Ready · 2 items could not be added')
    expect(uploadState({ ...base, counts: { ...c, digests_pending: 0, digests_ready: 2, not_found: 0, unreadable: 0 } }).label).toBe('Ready')
    expect(uploadState({ ...base, counts: { ...c, found: 0, digests_pending: 0 } }).label).toBe('No case was found')
  })
})
