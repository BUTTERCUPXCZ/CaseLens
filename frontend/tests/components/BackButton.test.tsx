import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BackButton } from '@/components/BackButton'

import { renderApp } from '../utils'

describe('the Back button', () => {
  it('offers the Case library when the page was opened straight from a link (nothing to go back to)', async () => {
    await renderApp(<BackButton />)
    expect(screen.getByRole('link', { name: 'Back to the Case library' })).toHaveAttribute('href', '/library?tab=cases')
  })
})

describe('the Back button on an upload’s page', () => {
  it('offers My uploads when there is nothing to go back to', async () => {
    await renderApp(<BackButton fallback="uploads" />)
    expect(screen.getByRole('link', { name: 'Back to My uploads' })).toHaveAttribute('href', '/library?tab=uploads')
  })
})
