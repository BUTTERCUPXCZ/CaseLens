import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { GuideSteps } from '@/features/guide/GuideSteps'
import { guideCopy } from '@/lib/copy'

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
})

describe('the guide steps for the case library', () => {
  it('walks through the screens in order: Individual, Bulk, label, find it under My uploads, ask, download', async () => {
    await renderApp(<GuideSteps steps={guideCopy.librarySteps} />)
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent?.replace(/^Step \d+: /, ''))).toEqual([
      'One case: Individual',
      'Many cases: Bulk',
      'Label it: Subject Tags and Topic scope',
      'Find it in the Case library, under My uploads',
      'Ask the AI assistant',
      'Download it',
    ])
  })

  it('says the student labels the case and the app never guesses a subject', () => {
    expect(guideCopy.librarySteps[2]!.body.join(' ')).toContain('the app never guesses a subject')
  })

  it('says what an upload promises: one case per file, repeats once, cited cases not added', () => {
    const bulk = guideCopy.librarySteps[1]!.body.join(' ')
    expect(bulk).toContain('Each file or number is one case')
    expect(bulk).toContain('shown once')
    expect(bulk).toContain('only mentions are not added')
  })

  it('names the three download options of the drawing', () => {
    const download = guideCopy.librarySteps[5]!.body.join(' ')
    for (const option of ['Facts and Doctrine', 'Doctrine, Facts, Issue, Ruling', 'Full case digest']) expect(download).toContain(option)
  })
})

describe('the guide wording', () => {
  const everyLine = [guideCopy.promise, ...guideCopy.librarySteps.flatMap((s) => [s.title, ...s.body]), ...guideCopy.steps.flatMap((s) => [s.title, ...s.body]), ...guideCopy.goodToKnow, ...guideCopy.faq.flatMap((f) => [f.q, f.a])].join(' ')

  it('uses no system words', () => {
    expect(everyLine).not.toMatch(/\b(parse|parsing|ingest|pending|mismatch|API|backend|queue|database|RLS)\b/i)
  })
})
