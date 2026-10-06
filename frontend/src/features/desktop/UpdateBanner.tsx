import { listen } from '@tauri-apps/api/event'
import { useQuery } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'
import { useState } from 'react'

import { reviewsQuery } from '@/api/queries'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { updateCopy } from '@/lib/copy'

import { appUpdateQuery, installAppUpdate } from './appUpdate'

/** "CaseLens 1.2.0 is ready. Install and restart": the desktop app's update, one click. It waits while digests are being
 *  written, so an update never stops a bulk upload halfway. */
export function UpdateBanner() {
  const update = useQuery(appUpdateQuery())
  const uploads = useQuery({ ...reviewsQuery(0), enabled: Boolean(update.data) })
  const [later, setLater] = useState<string | null>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const [problem, setProblem] = useState(false)

  const next = update.data
  if (!next || later === next.version) return null
  const writing = uploads.data?.some((b) => !b.finished || b.counts.digests_pending > 0) ?? false

  const install = async () => {
    setProblem(false)
    setProgress(0)
    const stop = await listen<{ downloaded: number; total: number | null }>('update-progress', ({ payload }) => {
      if (payload.total) setProgress(Math.round((100 * payload.downloaded) / payload.total))
    })
    try {
      await installAppUpdate() // the app closes and opens the new version
    } catch {
      setProblem(true)
      setProgress(null)
    } finally {
      stop()
    }
  }

  return (
    <div role="status" className="border-b border-border bg-accent px-4 py-2.5 md:px-8">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2">
        <Download className="size-4 shrink-0 text-primary" aria-hidden />
        {progress !== null ? (
          <div className="min-w-48 flex-1">
            <p className="tabular mb-1 text-sm font-medium">{updateCopy.downloading(progress)}</p>
            <Progress value={progress} aria-label={updateCopy.downloading(progress)} className="h-1.5" />
          </div>
        ) : (
          <>
            <p className="min-w-0 flex-1 text-sm">
              <span className="font-medium">{updateCopy.ready(next.version)}</span>{' '}
              {problem ? <span className="text-problem">{updateCopy.failed}</span> : writing ? updateCopy.waitForDigests : updateCopy.keeps}
            </p>
            <Button size="sm" disabled={writing} onClick={() => void install()}>
              {writing ? <Loader2 data-icon="inline-start" className="animate-spin" aria-hidden /> : null}
              {writing ? updateCopy.afterDigests : updateCopy.install}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setLater(next.version)}>
              {updateCopy.later}
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
