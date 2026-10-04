import { plural } from '@/lib/format'

/** The counts a review has, however we got them (the list gives them directly; the detail
 *  page counts its citations). */
export interface ReviewCounts {
  total: number
  matched: number
  needs_look: number
  not_found: number
  errors: number
  pending: number
}

/** "3 cases found: 2 match, 1 needs a look". Only mentions what is non-zero. */
export function summaryText(counts: ReviewCounts): string {
  if (counts.total === 0) return 'No cases found in this file'

  const parts = [
    counts.matched > 0 ? `${counts.matched} ${counts.matched === 1 ? 'matches' : 'match'}` : null,
    counts.needs_look > 0 ? `${counts.needs_look} ${counts.needs_look === 1 ? 'needs' : 'need'} a look` : null,
    counts.not_found > 0 ? `${counts.not_found} couldn't be found` : null,
    counts.errors > 0 ? `${counts.errors} couldn't be checked` : null,
    counts.pending > 0 ? `${counts.pending} still checking` : null,
  ].filter(Boolean)

  return `${plural(counts.total, 'case')} found: ${parts.join(', ')}`
}

/** The most important thing about a review, for scanning a list. */
export function headline(counts: ReviewCounts): 'checking' | 'needs-attention' | 'all-clear' | 'empty' {
  if (counts.total === 0) return 'empty'
  if (counts.pending > 0) return 'checking'
  if (counts.needs_look + counts.not_found + counts.errors > 0) return 'needs-attention'
  return 'all-clear'
}
