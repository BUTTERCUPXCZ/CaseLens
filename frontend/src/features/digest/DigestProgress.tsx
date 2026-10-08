import { useEffect, useState } from 'react'

import { Progress } from '@/components/ui/progress'
import { digestPageCopy } from '@/lib/copy'
import { type DigestStage, progressPercent } from '@/lib/digestProgress'

/** Seconds since the server's count, ticking here between polls so the bar and the timer move smoothly. The component is keyed on the
 *  server's answer, so a new answer starts the count again from it. */
function useTicks(): number {
  const [ticks, setTicks] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setTicks((n) => n + 1), 1000)
    return () => window.clearInterval(timer)
  }, [])
  return ticks
}

/** The step a digest is on, a bar that grows with it, and the time it has taken so far. `seconds`: on this step; `total`: since it was asked for. */
export function DigestProgress({ stage, seconds, total }: { stage: DigestStage; seconds: number; total: number }) {
  return <Ticking key={`${stage}|${seconds}|${total}`} stage={stage} onStep={seconds} total={total} />
}

function Ticking({ stage, onStep, total }: { stage: DigestStage; onStep: number; total: number }) {
  const ticks = useTicks()
  const percent = Math.round(progressPercent(stage, onStep + ticks))
  return (
    <div className="mt-6">
      <p className="text-lg">{digestPageCopy.stages[stage]}</p>
      <div className="mt-3 flex items-center gap-3">
        <Progress value={percent} aria-label={digestPageCopy.progressLabel} className="h-2 max-w-md" />
        <span className="tabular shrink-0 text-sm text-muted-foreground">{digestPageCopy.elapsed(total + ticks)}</span>
      </div>
      <p className="mt-3 text-base text-muted-foreground">{digestPageCopy.waitHelp}</p>
    </div>
  )
}
