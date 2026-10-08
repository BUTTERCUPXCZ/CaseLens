/** How far along a digest is, from the step it is on and how long it has been on it. The bar creeps forward inside each step's
 *  share and slows near its end, so it never claims "done" before the digest is, and never sits frozen during the long writer call. */
export type DigestStage = 'queued' | 'writing' | 'checking' | 'repairing'

const SHARE: Record<DigestStage, { start: number; end: number; typical: number }> = {
  queued: { start: 0, end: 5, typical: 30 },
  writing: { start: 5, end: 60, typical: 60 },
  checking: { start: 60, end: 85, typical: 20 },
  repairing: { start: 85, end: 97, typical: 20 },
}

export function progressPercent(stage: DigestStage, seconds: number): number {
  const { start, end, typical } = SHARE[stage]
  const done = Math.min(0.95, 1 - Math.exp(-Math.max(0, seconds) / typical)) // a slow AI stops short of the next step's start
  return start + (end - start) * done
}
