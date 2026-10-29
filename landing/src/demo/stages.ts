import { demoCopy } from '@/copy'
import { DURATION } from '@/demo/useDemo'

export type Stage = keyof typeof demoCopy.write.stages

/** The same steps and bar shares as the app (frontend/src/lib/digestProgress.ts), on the demo's shorter clock. */
const STAGES: { stage: Stage; until: number; from: number; to: number }[] = [
  { stage: 'queued', until: 600, from: 0, to: 5 },
  { stage: 'writing', until: 3300, from: 5, to: 60 },
  { stage: 'checking', until: 4800, from: 60, to: 85 },
  { stage: 'repairing', until: DURATION.write, from: 85, to: 100 },
]

export function stageAt(t: number): { stage: Stage; percent: number } {
  let start = 0
  for (const step of STAGES) {
    if (t < step.until) return { stage: step.stage, percent: step.from + ((step.to - step.from) * (t - start)) / (step.until - start) }
    start = step.until
  }
  return { stage: 'repairing', percent: 100 }
}
