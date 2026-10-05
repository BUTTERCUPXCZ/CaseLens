import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { UploadSummary } from '@/api/types'
import { ReviewList } from '@/features/reviews/ReviewList'

import uploads from '../fixtures/api/uploads.json'
import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

const first = (uploads as UploadSummary[])[0]!

describe('deleting a review from the list', () => {
  it('asks first, says what stays, and does nothing until the student confirms', async () => {
    let deleted = 0
    server.use(http.delete(`${API}/uploads/:id`, () => { deleted += 1; return new HttpResponse(null, { status: 204 }) }))
    const user = userEvent.setup()
    await renderApp(<ReviewList limit={5} emptyMessage="none" />)

    await user.click(await screen.findByRole('button', { name: `Delete ${first.filename}` }))

    expect(await screen.findByRole('dialog')).toHaveTextContent('The cases stay in the Case library')
    expect(deleted).toBe(0)
    await user.click(screen.getByRole('button', { name: 'Keep it' }))
    expect(deleted).toBe(0)
  })

  it('deletes the chosen review and refreshes the list', async () => {
    const asked: string[] = []
    let remaining = uploads as UploadSummary[]
    server.use(
      http.get(`${API}/uploads`, () => HttpResponse.json(remaining)),
      http.delete(`${API}/uploads/:id`, ({ params }) => {
        asked.push(String(params.id))
        remaining = remaining.filter((u) => String(u.id) !== params.id)
        return new HttpResponse(null, { status: 204 })
      }),
    )
    const user = userEvent.setup()
    await renderApp(<ReviewList limit={5} emptyMessage="none" />)

    const before = (await screen.findAllByRole('button', { name: /^Delete / })).length
    await user.click(screen.getByRole('button', { name: `Delete ${first.filename}` }))
    await user.click(await screen.findByRole('button', { name: 'Delete' }))

    expect(asked).toEqual([String(first.id)])
    await waitFor(() => expect(screen.getAllByRole('button', { name: /^Delete / })).toHaveLength(before - 1))
  })

  it('shows a plain message and keeps the review when the server says no', async () => {
    server.use(http.delete(`${API}/uploads/:id`, () => HttpResponse.json({ detail: 'x' }, { status: 503 })))
    const user = userEvent.setup()
    await renderApp(<ReviewList limit={5} emptyMessage="none" />)

    await user.click(await screen.findByRole('button', { name: `Delete ${first.filename}` }))
    await user.click(await screen.findByRole('button', { name: 'Delete' }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getAllByText(first.filename).length).toBeGreaterThan(0)
  })
})
