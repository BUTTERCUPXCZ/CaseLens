import type { Citation } from '@/api/types'
import { reporterNote } from '@/lib/copy'
import { formatDate, shortCaseName } from '@/lib/format'

/** same: matches the Court's record. differs: the student's value is different (shown struck,
 *  with the Court's value beside it). unchecked: we cannot say either way. */
export type Verdict = 'same' | 'differs' | 'unchecked'

export interface CompareRow {
  key: 'gr_no' | 'title' | 'date' | 'reporter'
  label: string
  wrote: string
  record: string | null
  verdict: Verdict
  note?: string
}

/** One row per thing the student actually wrote about the case, set against what the Court's
 *  record says. Without a record (still checking, not found, error) the right-hand side is empty. */
export function buildCompareRows(citation: Citation): CompareRow[] {
  const { claimed, mismatches } = citation
  const official = citation.case
  const verdictFor = (differs: boolean): Verdict => (!official ? 'unchecked' : differs ? 'differs' : 'same')

  const rows: CompareRow[] = [
    {
      key: 'gr_no',
      label: 'G.R. number',
      wrote: citation.gr_no,
      record: official ? String(official.gr_no) : null,
      verdict: verdictFor('gr_no' in mismatches),
    },
  ]

  if (claimed.title) {
    rows.push({
      key: 'title',
      label: 'Case name',
      wrote: claimed.title,
      record: official ? shortCaseName(official.title) : null,
      verdict: verdictFor('title' in mismatches),
    })
  }

  const dateDiffers = 'year' in mismatches || 'date' in mismatches
  if (claimed.date) {
    rows.push({
      key: 'date',
      label: 'Date decided',
      wrote: formatDate(claimed.date),
      record: official ? formatDate(official.decision_date) : null,
      verdict: verdictFor(dateDiffers),
    })
  } else if (claimed.year) {
    rows.push({
      key: 'date',
      label: 'Year decided',
      wrote: String(claimed.year),
      record: official?.decision_date ? official.decision_date.slice(0, 4) : null,
      verdict: verdictFor(dateDiffers),
    })
  }

  if (claimed.reporter) {
    rows.push({
      key: 'reporter',
      label: 'Page reference',
      wrote: claimed.reporter,
      record: null,
      verdict: 'unchecked',
      note: reporterNote,
    })
  }

  return rows
}
