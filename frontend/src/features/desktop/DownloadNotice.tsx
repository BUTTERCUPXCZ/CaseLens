import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'
import { CircleAlert, CircleCheck, FolderOpen, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { downloadCopy } from '@/lib/copy'

/** What the desktop app says when a download is done (see desktop/src-tauri/src/downloads.rs). */
type Finished = { name: string; path: string | null; success: boolean }

const SHOWN_MS = 12_000

/** The desktop window has no browser download bar, so a saved file would go unnoticed: this says where it went and offers to open it. */
export function DownloadNotice() {
  const [last, setLast] = useState<Finished | null>(null)
  const [problem, setProblem] = useState<string | null>(null)

  useEffect(() => {
    const stop = listen<Finished>('download-finished', ({ payload }) => {
      setProblem(null)
      setLast(payload)
    })
    return () => void stop.then((unlisten) => unlisten()).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!last) return
    const timer = setTimeout(() => setLast(null), SHOWN_MS)
    return () => clearTimeout(timer)
  }, [last])

  if (!last) return null
  const run = (command: 'open_download' | 'reveal_download') =>
    invoke(command, { path: last.path }).catch((error: unknown) => setProblem(typeof error === 'string' ? error : downloadCopy.openFailed))

  return (
    <div role="status" className="fixed right-6 bottom-6 z-50 w-[min(26rem,calc(100vw-3rem))] rounded-lg border border-border bg-card px-4 py-3 shadow-lg">
      <div className="flex items-start gap-3">
        {last.success ? <CircleCheck className="mt-0.5 size-5 shrink-0 text-match" aria-hidden /> : <CircleAlert className="mt-0.5 size-5 shrink-0 text-problem" aria-hidden />}
        <div className="min-w-0 flex-1">
          <p className="text-base font-medium">{last.success ? downloadCopy.saved : downloadCopy.failed}</p>
          {last.success && last.name ? <p className="truncate text-sm text-muted-foreground">{last.name}</p> : null}
          {last.success && last.path ? (
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="sm" onClick={() => void run('open_download')}>
                {downloadCopy.open}
              </Button>
              <Button size="sm" variant="outline" onClick={() => void run('reveal_download')}>
                <FolderOpen data-icon="inline-start" aria-hidden />
                {downloadCopy.showInFolder}
              </Button>
            </div>
          ) : null}
          {problem ? <p className="mt-2 text-sm text-problem">{problem}</p> : null}
        </div>
        <Button size="icon" variant="ghost" className="-mt-1 -mr-2 size-8" aria-label={downloadCopy.close} onClick={() => setLast(null)}>
          <X aria-hidden />
        </Button>
      </div>
    </div>
  )
}
