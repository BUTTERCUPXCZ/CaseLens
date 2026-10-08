import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { WebSettingsPage } from '@/features/settings/WebSettings'

import { server } from '../mocks/server'
import { renderApp } from '../utils'

const API = `${window.location.origin}/api`
const MODELS = [
  { id: 'deepseek/deepseek-v4.1-flash', name: 'DeepSeek V4.1 Flash', free: false },
  { id: 'nvidia/nemotron-3-ultra-550b-a55b:free', name: 'Nemotron 3 Ultra (free, for testing)', free: true },
]
const nemotron = {
  provider: 'OpenRouter', model: 'Nemotron 3 Ultra (free, for testing)', model_id: MODELS[1]!.id, free: true, only_chosen: true, ready: true, models: MODELS,
}

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

  it('lets the model be picked from a list, and saves the choice', async () => {
    let sent: unknown = null
    server.use(
      http.get(`${API}/ai-info`, () => HttpResponse.json({ ...nemotron, model_id: MODELS[0]!.id, model: MODELS[0]!.name, free: false })),
      http.put(`${API}/ai-model`, async ({ request }) => {
        sent = await request.json()
        return HttpResponse.json(nemotron)
      }),
    )
    const user = userEvent.setup()
    await renderApp(<WebSettingsPage />)
    const picker = await screen.findByRole('combobox', { name: 'Model' })
    expect(picker).toHaveValue('deepseek/deepseek-v4.1-flash')
    await user.selectOptions(picker, 'nvidia/nemotron-3-ultra-550b-a55b:free')
    await waitFor(() => expect(sent).toEqual({ model: 'nvidia/nemotron-3-ultra-550b-a55b:free' }))
    expect(await screen.findByText('OpenRouter · Nemotron 3 Ultra (free, for testing)')).toBeInTheDocument()
  })

  it('says plainly when the site has no AI key yet', async () => {
    server.use(http.get(`${API}/ai-info`, () => HttpResponse.json({ ...nemotron, ready: false, free: false, model: 'DeepSeek V4.1 Flash' })))
    await renderApp(<WebSettingsPage />)
    expect(await screen.findByText(/No AI key is set for this site yet/)).toBeInTheDocument()
  })
})
