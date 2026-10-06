import { describe, expect, it } from 'vitest'

import { ApiError } from '@/api/client'
import type { Citation } from '@/api/types'
import { citationStatus, describeMismatch, explainCitation, fieldName, friendlyError } from '@/lib/copy'

import needsALook from '../fixtures/api/upload-needs-a-look.json'

// The real response for the sample reviewer (GR 180046, "April 2, 2010" vs the Court's 2009).
const citation = needsALook.citations[0] as Citation

describe('the real citation from the sample reviewer', () => {
  it('is worded the way the design promises', () => {
    expect(citationStatus[citation.status].label).toBe('Needs a look')
    expect(fieldName('year')).toBe('Year decided')
    expect(describeMismatch(citation.mismatches.year)).toBe(
      "You wrote 2010. The Court's record says 2009.",
    )
  })
})

describe('explainCitation', () => {
  it('explains a missing year in plain words, using the real backend message', () => {
    const text = explainCitation(
      'not_found',
      'G.R. No. 180046 is not stored yet and no year was given to search for it. Add the year, or paste the Lawphil URL.',
    )
    expect(text).toMatch(/didn't write the year/)
    expect(text).toMatch(/paste the case's Lawphil link/)
  })

  it('never blames the student for a source outage', () => {
    expect(explainCitation('error', 'https://lawphil.net failed after 4 attempts')).toMatch(/Nothing is wrong with your file/)
  })

  it('has nothing to add for a match', () => {
    expect(explainCitation('match', null)).toBeNull()
  })
})

describe('friendlyError', () => {
  const cases: [number, string | null, RegExp][] = [
    [0, null, /can't reach CaseLens/],
    [415, 'Unsupported file type: notes.txt', /PDF and Word/],
    [413, 'File is larger than 5 MB.', /larger than 5 MB/],
    [422, 'PDF has no extractable text (scanned image PDFs are not supported).', /looks like a scan/],
    [422, "Not a valid G.R. number: '12'", /digits only/],
    [400, 'Not an official Lawphil case URL: https://evil.example/a.html', /Lawphil case link/],
    [502, 'https://lawphil.net failed after 4 attempts', /isn't responding/],
    [404, 'Case 9 does not exist.', /couldn't find that/],
    [400, 'Individual is for one case. This has more than one: use Bulk for several cases.', /use Bulk to digest all the cases/],
  ]

  it.each(cases)('status %i reads as a sentence the student can act on', (status, detail, expected) => {
    expect(friendlyError(new ApiError(status, detail))).toMatch(expected)
  })

  it('never shows raw technical text', () => {
    const message = friendlyError(new ApiError(500, 'Traceback (most recent call last): sqlalchemy.exc'))
    expect(message).not.toMatch(/Traceback|sqlalchemy/)
  })

  it('copes with something that is not an ApiError', () => {
    expect(friendlyError(new Error('boom'))).toMatch(/try again/i)
  })
})
