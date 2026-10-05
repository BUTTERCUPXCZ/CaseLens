import type { Bulk } from '@/api/types'
import { reviewsCopy } from '@/lib/copy'

/** How an upload is named: by the case it gave ("Review Center … v. Ermita and 2 more"); before any case is found, by what was uploaded
 *  ("sample case.pdf, 180046 and 3 more"). */
export function reviewTitle(bulk: Bulk): string {
  if (bulk.cases.length > 0) {
    const rest = bulk.case_total - 1
    return bulk.cases[0]!.name + (rest > 0 ? reviewsCopy.andMore(rest) : '')
  }
  return uploadedLabel(bulk)
}

/** What the student uploaded or typed, as given ("sample case.pdf", "180046, banana and 1 more"). */
export function uploadedLabel(bulk: Bulk): string {
  if (bulk.labels.length === 0) return `${reviewsCopy.untitled} #${bulk.id}`
  const rest = bulk.counts.total - bulk.labels.length
  return bulk.labels.join(', ') + (rest > 0 ? reviewsCopy.andMore(rest) : '')
}
