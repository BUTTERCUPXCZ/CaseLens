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
    const bulk = { ...progress, labels: ['marcos.pdf', '180046', 'banana'] } as never
    expect(reviewTitle(bulk)).toBe('marcos.pdf, 180046, banana and 2 more')
    expect(reviewTitle({ ...progress, labels: [] } as never)).toBe('Upload #1')
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
