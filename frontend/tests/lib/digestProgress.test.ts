import { describe, expect, it } from 'vitest'

import { type DigestStage, progressPercent } from '@/lib/digestProgress'

describe('how far along a digest is', () => {
  it('starts each step at its own share: waiting 0%, writing 5%, checking 60%, fixing 85%', () => {
    expect([progressPercent('queued', 0), progressPercent('writing', 0), progressPercent('checking', 0), progressPercent('repairing', 0)]).toEqual([0, 5, 60, 85])
  })

  it('grows with the time on a step but never reaches the next step, however long the AI takes', () => {
    const next: Record<DigestStage, number> = { queued: 5, writing: 60, checking: 85, repairing: 100 }
    for (const stage of Object.keys(next) as DigestStage[]) {
      const early = progressPercent(stage, 10)
      const late = progressPercent(stage, 3600)
      expect(late).toBeGreaterThan(early)
      expect(late).toBeLessThan(next[stage])
    }
    expect(progressPercent('repairing', 99999)).toBeLessThanOrEqual(97) // never 100% before the digest is there
  })

  it('treats a negative count (a clock hiccup) as zero', () => {
    expect(progressPercent('writing', -5)).toBe(5)
  })
})
