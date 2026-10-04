import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { WelcomeCard } from '@/features/guide/WelcomeCard'
import { welcomeCopy } from '@/lib/copy'

import { renderApp } from '../utils'

afterEach(() => {
  window.localStorage.clear()
  vi.restoreAllMocks()
})

describe('the welcome card', () => {
  it('shows the four steps and a link to the guide to a new visitor', async () => {
    await renderApp(<WelcomeCard />)
    expect(await screen.findByRole('heading', { name: welcomeCopy.title })).toBeInTheDocument()
    for (const step of welcomeCopy.steps) expect(screen.getByText(step)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: welcomeCopy.guide })).toHaveAttribute('href', '/guide')
  })

  it('closes with "Got it" and stays closed on the next visit', async () => {
    const user = userEvent.setup()
    const first = await renderApp(<WelcomeCard />)
    await user.click(await screen.findByRole('button', { name: welcomeCopy.dismiss }))
    expect(screen.queryByRole('heading', { name: welcomeCopy.title })).not.toBeInTheDocument()
    first.unmount?.()

    await renderApp(<WelcomeCard />)
    expect(screen.queryByRole('heading', { name: welcomeCopy.title })).not.toBeInTheDocument()
  })

  it('still shows and closes when the browser blocks storage', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const user = userEvent.setup()
    await renderApp(<WelcomeCard />)
    await user.click(await screen.findByRole('button', { name: welcomeCopy.dismissLabel }))
    expect(screen.queryByRole('heading', { name: welcomeCopy.title })).not.toBeInTheDocument()
  })
})
