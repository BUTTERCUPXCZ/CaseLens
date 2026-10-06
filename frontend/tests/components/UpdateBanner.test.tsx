import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import progress from '../fixtures/api/bulk-progress.json'
import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

// The desktop window, with the app's updater answering through Tauri's `invoke`.
vi.mock('@/lib/desktop', () => ({ inDesktopWindow: true }))
const invoke = vi.fn()
vi.mock('@tauri-apps/api/core', () => ({ invoke: (...args: unknown[]) => invoke(...args) }))
vi.mock('@tauri-apps/api/event', () => ({ listen: async () => () => undefined }))

const { UpdateBanner } = await import('@/features/desktop/UpdateBanner')

const finished = { ...progress, finished: true, counts: { ...progress.counts, digests_pending: 0 } }

describe('the update bar (desktop app)', () => {
  beforeEach(() => {
    invoke.mockReset()
    server.use(http.get(`${API}/bulk`, () => HttpResponse.json([finished])))
  })

  it('offers a found update and installs it on one click', async () => {
    invoke.mockImplementation(async (command: string) => (command === 'check_update' ? { version: '1.2.0', notes: null } : undefined))
    await renderApp(<UpdateBanner />)
    expect(await screen.findByText('CaseLens 1.2.0 is ready.')).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Install and restart' }))
    expect(invoke).toHaveBeenCalledWith('install_update')
  })

  it('waits while digests are still being written, so an update never stops a bulk upload', async () => {
    server.use(http.get(`${API}/bulk`, () => HttpResponse.json([{ ...progress, finished: false }])))
    invoke.mockResolvedValue({ version: '1.2.0', notes: null })
    await renderApp(<UpdateBanner />)
    expect(await screen.findByRole('button', { name: 'Waiting for the digests' })).toBeDisabled()
  })

  it('shows nothing when CaseLens is up to date', async () => {
    invoke.mockResolvedValue(null)
    const { container } = await renderApp(<UpdateBanner />)
    await vi.waitFor(() => expect(invoke).toHaveBeenCalledWith('check_update'))
    expect(container.querySelector('[role="status"]')).toBeNull()
  })
})
