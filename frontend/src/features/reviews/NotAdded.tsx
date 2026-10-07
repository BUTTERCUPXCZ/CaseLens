import { useQuery } from '@tanstack/react-query'
import { RotateCw } from 'lucide-react'

import { useRetryBulk } from '@/api/mutations'
import { bulkItemsQuery } from '@/api/queries'
import type { Bulk, BulkItem, BulkItemStatus } from '@/api/types'
import { Button } from '@/components/ui/button'
import { bulkCopy } from '@/lib/copy'

const NOT_ADDED: BulkItemStatus[] = ['not_found', 'unreadable', 'failed']

function NotAddedStatus({ batchId, status, live }: { batchId: number; status: BulkItemStatus; live: boolean }) {
  const { data } = useQuery(bulkItemsQuery(batchId, status, 0, live))
  if (!data || data.items.length === 0) return null
  return (
    <>
      {data.items.map((item: BulkItem) => (
        <li key={item.id} className="py-2">
          <p className="text-base font-medium">{item.label}</p>
          <p className="text-sm text-muted-foreground">{item.message ?? bulkCopy.statusLabel[item.status]}</p>
        </li>
      ))}
    </>
  )
}

/** What could not be added from an upload (not found, unreadable, Lawphil did not answer), each with its reason, and a retry. */
export function NotAdded({ bulk }: { bulk: Bulk }) {
  const retry = useRetryBulk(bulk.id)
  const c = bulk.counts
  if (c.not_found + c.unreadable + c.failed === 0) return null
  return (
    <section aria-label={bulkCopy.notAddedTitle}>
      <h2 className="text-lg font-semibold">{bulkCopy.notAddedTitle}</h2>
      <ul className="mt-2 divide-y divide-border border-y border-border">
        {NOT_ADDED.map((status) => (
          <NotAddedStatus key={status} batchId={bulk.id} status={status} live={!bulk.finished} />
        ))}
      </ul>
      {c.failed > 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {/* the column is narrow: the label wraps inside the button instead of running into the digest beside it */}
          <Button variant="outline" className="h-auto w-full justify-start py-2 text-left whitespace-normal" disabled={retry.isPending} onClick={() => retry.mutate()}>
            <RotateCw data-icon="inline-start" aria-hidden /> {bulkCopy.retry}
          </Button>
          {retry.data ? <span role="status" className="text-sm text-muted-foreground">{bulkCopy.retried(retry.data.requeued)}</span> : null}
        </div>
      ) : null}
    </section>
  )
}
