import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { WebSettingsPage } from '@/features/settings/WebSettings'

import { server } from '../mocks/server'
import { renderApp } from '../utils'

const API = `${window.location.origin}/api`
const nemotron = { provider: 'OpenRouter', model: 'Nemotron 3 Ultra (free, for testing)', free: true, only_chosen: true, ready: true }

describe('Settings on the website', () => {
  it('says which AI writes the digests, that it is the only one, and that it is free for testing', async () => {
    server.use(http.get(`${API}/ai-info`, () => HttpResponse.json(nemotron)))
    await renderApp(<WebSettingsPage />)
    expect(await screen.findByText('OpenRouter · Nemotron 3 Ultra (free, for testing)')).toBeInTheDocument()
    expect(screen.getByText(/no other AI takes over/)).toBeInTheDocument()
    expect(screen.getByText(/about 50 requests a day/)).toBeInTheDocument()
    expect(screen.getByText(/set by the person who runs the site/)).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument() // nothing to type: no key can be changed from the website
  })

  it('says plainly when the site has no AI key yet', async () => {
    server.use(http.get(`${API}/ai-info`, () => HttpResponse.json({ ...nemotron, ready: false, free: false, model: 'DeepSeek V4.1 Flash' })))
    await renderApp(<WebSettingsPage />)
    expect(await screen.findByText(/No AI key is set for this site yet/)).toBeInTheDocument()
  })
})
