import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { GuideSteps } from '@/features/guide/GuideSteps'
import { citationStatus, guideCopy } from '@/lib/copy'

import { renderApp } from '../utils'

describe('the guide steps', () => {
  it('shows every step in order, each with a heading a screen reader can jump to', async () => {
    await renderApp(<GuideSteps steps={guideCopy.steps} />)
    const items = screen.getAllByRole('listitem').filter((li) => within(li).queryByRole('heading', { level: 3 }))
    expect(items).toHaveLength(guideCopy.steps.length)
    guideCopy.steps.forEach((step, i) => {
      expect(within(items[i]!).getByRole('heading', { level: 3 })).toHaveTextContent(step.title)
    })
  })

  it('shows the real result labels, so the guide cannot drift from the app', async () => {
    await renderApp(<GuideSteps steps={guideCopy.steps} />)
    for (const { label } of Object.values(citationStatus)) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it('shows the proofreader example with the wrong date crossed out and the Court’s date beside it', async () => {
    await renderApp(<GuideSteps steps={guideCopy.steps} />)
    expect(screen.getByText('April 2, 2010').tagName).toBe('DEL')
    expect(screen.getByText('April 2, 2009').tagName).toBe('INS')
  })
})

describe('the guide wording', () => {
  const everyLine = [guideCopy.promise, ...guideCopy.steps.flatMap((s) => [s.title, ...s.body]), ...guideCopy.goodToKnow, ...guideCopy.faq.flatMap((f) => [f.q, f.a])].join(' ')

  it('uses no system words', () => {
    expect(everyLine).not.toMatch(/\b(parse|parsing|ingest|pending|mismatch|API|backend|queue|database|RLS)\b/i)
  })

  it('states the upload limit the app really enforces', async () => {
    const { upload } = await import('@/lib/copy')
    expect(guideCopy.steps[0]!.body[0]).toContain(`${upload.maxBytes / (1024 * 1024)} MB`)
  })
})
