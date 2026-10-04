import { describe, expect, it } from 'vitest'

import type { Citation } from '@/api/types'
import { buildCompareRows } from '@/features/reviews/compareRows'
import { headline, summaryText } from '@/features/reviews/summary'

import needsALook from '../fixtures/api/upload-needs-a-look.json'
import uploads from '../fixtures/api/uploads.json'

// Real response for the sample reviewer: GR 180046 written as "April 2, 2010 / 538 SCRA 428".
const real = needsALook.citations[0] as Citation

describe('the real sample reviewer, row by row', () => {
  const rows = buildCompareRows(real)
  const row = (key: string) => rows.find((r) => r.key === key)!

  it('matches the G.R. number and the case name', () => {
    expect(row('gr_no')).toMatchObject({ wrote: '180046', record: '180046', verdict: 'same' })
    expect(row('title')).toMatchObject({
      wrote: 'Review Center v Ermita',
      record: 'Review Center Association of the Philippines v. Executive Secretary Eduardo Ermita et al.',
      verdict: 'same',
    })
  })

  it('shows the wrong date next to the right one: the red-pen row', () => {
    expect(row('date')).toMatchObject({
      label: 'Date decided',
      wrote: 'April 2, 2010',
      record: 'April 2, 2009',
      verdict: 'differs',
    })
  })

  it('never claims to have checked the page reference, and says why', () => {
    expect(row('reporter')).toMatchObject({ wrote: '538 SCRA 428', record: null, verdict: 'unchecked' })
    expect(row('reporter').note).toMatch(/Lawphil doesn't include it/)
  })

  it('lists the rows in a sensible reading order', () => {
    expect(rows.map((r) => r.key)).toEqual(['gr_no', 'title', 'date', 'reporter'])
  })
})

describe('citations without a record yet (synthetic variations of the real one)', () => {
  const withoutRecord: Citation = { ...real, status: 'pending', case: null, case_id: null, source_url: null, mismatches: {} }

  it('has nothing on the Court side and says nothing was checked', () => {
    const rows = buildCompareRows(withoutRecord)
    expect(rows.every((r) => r.record === null)).toBe(true)
    expect(rows.every((r) => r.verdict === 'unchecked')).toBe(true)
  })

  it('uses the year when that is all the student wrote', () => {
    const yearOnly: Citation = { ...withoutRecord, claimed: { ...withoutRecord.claimed, date: null, year: 2010, reporter: null, title: null } }
    expect(buildCompareRows(yearOnly).map((r) => [r.key, r.label, r.wrote])).toEqual([
      ['gr_no', 'G.R. number', '180046'],
      ['date', 'Year decided', '2010'],
    ])
  })

  it('compares only the year when the student wrote only a year', () => {
    const yearOnly: Citation = { ...real, claimed: { ...real.claimed, date: null, year: 2010 } }
    const date = buildCompareRows(yearOnly).find((r) => r.key === 'date')!
    expect(date).toMatchObject({ label: 'Year decided', wrote: '2010', record: '2009', verdict: 'differs' })
  })
})

describe('review summaries', () => {
  it('reads the real list from the backend', () => {
    const withLook = uploads.find((u) => u.needs_look === 1)!
    expect(summaryText(withLook)).toBe('1 case found: 1 needs a look')
    expect(headline(withLook)).toBe('needs-attention')
  })

  it('names each outcome in plain words (synthetic counts)', () => {
    expect(
      summaryText({ total: 6, matched: 2, needs_look: 2, not_found: 1, errors: 1, pending: 0 }),
    ).toBe("6 cases found: 2 match, 2 need a look, 1 couldn't be found, 1 couldn't be checked")
    expect(summaryText({ total: 1, matched: 1, needs_look: 0, not_found: 0, errors: 0, pending: 0 })).toBe('1 case found: 1 matches')
    expect(summaryText({ total: 0, matched: 0, needs_look: 0, not_found: 0, errors: 0, pending: 0 })).toBe('No cases found in this file')
    expect(headline({ total: 3, matched: 1, needs_look: 0, not_found: 0, errors: 0, pending: 2 })).toBe('checking')
    expect(headline({ total: 2, matched: 2, needs_look: 0, not_found: 0, errors: 0, pending: 0 })).toBe('all-clear')
  })
})
