import { Loader2 } from 'lucide-react'

import { useStartCatalogBuild } from '@/api/mutations'
import type { CatalogStatus } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { friendlyError, listProgress } from '@/lib/copy'

/** Shown only until Lawphil's list has been read in full: how far it has got, and what still works. */
export function ListProgress({ status }: { status: CatalogStatus }) {
  const start = useStartCatalogBuild()
  if (status.state === 'ready') return null

  const building = status.state === 'building'
  const title =
    status.state === 'partial' ? listProgress.partialTitle : building ? listProgress.buildingTitle : listProgress.emptyTitle

  return (
    <section aria-label="Progress of Lawphil's case list" className="mb-6 rounded-lg bg-muted px-5 py-4">
      <div className="flex items-start gap-3">
        {building ? <Loader2 className="mt-0.5 size-5 shrink-0 animate-spin text-primary" aria-hidden /> : null}
        <div className="min-w-0 flex-1" aria-live="polite">
          <h2 className="font-semibold">{title}</h2>
          {building ? (
            <p className="mt-1 text-base text-muted-foreground">
              {listProgress.buildingText(status.months_read, status.months_known, status.percent)}
            </p>
          ) : status.state === 'partial' ? (
            <p className="mt-1 text-base text-muted-foreground">{listProgress.partialText(status.percent)}</p>
          ) : null}
          {building && status.months_known > 0 ? (
            <Progress
              value={status.percent}
              className="mt-3"
              aria-label={`${status.months_read} of ${status.months_known} months read`}
            />
          ) : null}
          {!building ? (
            <Button className="mt-3" size="sm" disabled={start.isPending} onClick={() => start.mutate()}>
              {start.isPending ? listProgress.continuing : listProgress.continueAction}
            </Button>
          ) : null}
          {start.isError ? (
            <p role="alert" className="mt-2 text-sm text-problem">
              {friendlyError(start.error)}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  )
}
