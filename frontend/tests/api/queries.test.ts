import type { Query } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'

import { MAX_SEARCH_POLLS, POLL_MS, searchQuery, uploadQuery } from '@/api/queries'
import type { SearchResult, Upload } from '@/api/types'

// A stand-in for TanStack's query object: the polling rules only read its state.
const asQuery = <T,>(data: T | undefined, dataUpdateCount = 1) =>
  ({ state: { data, dataUpdateCount } }) as unknown as Query<T>
const interval = (options: { refetchInterval?: unknown }, query: unknown) =>
  (options.refetchInterval as (q: unknown) => number | false)(query)

describe('a review is polled only while it is still being checked', () => {
  const poll = (data: Partial<Upload> | undefined) => interval(uploadQuery(2), asQuery(data))

  it('keeps asking every few seconds while processing', () => expect(poll({ status: 'processing' })).toBe(POLL_MS))
  it('stops when done', () => expect(poll({ status: 'done' })).toBe(false))
  it('does not poll before the first answer arrives', () => expect(poll(undefined)).toBe(false))
})

describe('a G.R. search keeps asking while the backend looks on Lawphil, then gives up', () => {
  const poll = (status: SearchResult['status'] | undefined, count = 1) =>
    interval(searchQuery('180046', 2009), asQuery(status ? ({ status, cases: [] } as SearchResult) : undefined, count))

  it('asks again while pending', () => expect(poll('pending')).toBe(POLL_MS))
  it('stops when the case is found', () => expect(poll('found')).toBe(false))
  it('stops when a year is needed (asking again changes nothing)', () => expect(poll('needs_year')).toBe(false))
  it('gives up after about two minutes of waiting', () => {
    expect(poll('pending', MAX_SEARCH_POLLS - 1)).toBe(POLL_MS)
    expect(poll('pending', MAX_SEARCH_POLLS)).toBe(false)
    expect(MAX_SEARCH_POLLS * POLL_MS).toBe(120_000)
  })
})
