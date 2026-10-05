import { describe, expect, it } from 'vitest'

import { chunkFiles } from '@/features/bulk/chunkFiles'

const file = (name: string, size: number) => new File([new Uint8Array(size)], name)

describe('chunkFiles: files go a few at a time, under the web host’s request limit', () => {
  it('sends nothing for no files', () => {
    expect(chunkFiles([])).toEqual([])
  })

  it('keeps small files together, up to 10 per request, in the order chosen', () => {
    const files = Array.from({ length: 23 }, (_, i) => file(`f${i}.pdf`, 1000))
    const groups = chunkFiles(files)
    expect(groups.map((g) => g.length)).toEqual([10, 10, 3])
    expect(groups.flat().map((f) => f.name)).toEqual(files.map((f) => f.name))
  })

  it('starts a new request when the next file would pass about 3.5 MB', () => {
    const groups = chunkFiles([file('a', 2_000_000), file('b', 1_000_000), file('c', 1_000_000), file('d', 400_000)])
    expect(groups.map((g) => g.map((f) => f.name))).toEqual([['a', 'b'], ['c', 'd']])
  })

  it('sends a file that is too big for any group on its own, never dropping it', () => {
    const groups = chunkFiles([file('small', 100), file('huge', 4_900_000), file('small2', 100)])
    expect(groups.map((g) => g.map((f) => f.name))).toEqual([['small'], ['huge'], ['small2']])
  })
})
