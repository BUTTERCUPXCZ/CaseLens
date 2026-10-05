import type { Bulk } from '@/api/types'
import { reviewsCopy } from '@/lib/copy'

/** How an upload is named in "My reviews": its first files or numbers ("marcos.pdf, 180046 and 3 more"). */
export function reviewTitle(bulk: Bulk): string {
  if (bulk.labels.length === 0) return `${reviewsCopy.untitled} #${bulk.id}`
  const rest = bulk.counts.total - bulk.labels.length
  return bulk.labels.join(', ') + (rest > 0 ? reviewsCopy.andMore(rest) : '')
}
