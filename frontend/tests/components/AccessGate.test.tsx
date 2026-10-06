import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { AccessGate } from '@/components/AccessGate'

import { API, http, HttpResponse, server } from '../mocks/server'

const show = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AccessGate>
        <p>the app</p>
      </AccessGate>
    </QueryClientProvider>,
  )

describe('the access code page', () => {
  it('opens the app straight away when no code is set', async () => {
    server.use(http.get(`${API}/access`, () => HttpResponse.json({ required: false, granted: true })))
    show()
    expect(await screen.findByText('the app')).toBeInTheDocument()
  })

  it('asks for the code, says so when it is wrong, and opens the app when it is right', async () => {
    server.use(
      http.get(`${API}/access`, () => HttpResponse.json({ required: true, granted: false })),
      http.post(`${API}/access`, async ({ request }) => {
        const body = (await request.json()) as { code: string }
        return body.code === 'good'
          ? HttpResponse.json({ required: true, granted: true })
          : HttpResponse.json({ detail: 'That code is not right.' }, { status: 401 })
      }),
    )
    const user = userEvent.setup()
    show()

    await user.type(await screen.findByLabelText('Access code'), 'bad')
    await user.click(screen.getByRole('button', { name: 'Open CaseLens' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('That code is not right.')
    expect(screen.queryByText('the app')).not.toBeInTheDocument()

    await user.clear(screen.getByLabelText('Access code'))
    await user.type(screen.getByLabelText('Access code'), 'good')
    await user.click(screen.getByRole('button', { name: 'Open CaseLens' }))
    expect(await screen.findByText('the app')).toBeInTheDocument()
  })

  it('opens the app when the server cannot be reached, so the app shows its own error', async () => {
    server.use(http.get(`${API}/access`, () => HttpResponse.error()))
    show()
    expect(await screen.findByText('the app')).toBeInTheDocument()
  })
})

describe('while the server wakes up', () => {
  it('says so after a few seconds, so nobody thinks the site is broken', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    server.use(http.get(`${API}/access`, () => new Promise(() => undefined))) // the sleeping server has not answered yet
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AccessGate>
          <p>app</p>
        </AccessGate>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Opening CaseLens…')
    await act(async () => vi.advanceTimersByTime(3500))
    expect(screen.getByRole('status')).toHaveTextContent('Waking up the server, this can take up to a minute…')
    vi.useRealTimers()
  })
})
