import { Link, useNavigate } from '@tanstack/react-router'

import type { CaseSummary } from '@/api/types'
import { libraryCopy } from '@/lib/copy'
import { formatDate, justiceName, shortCaseName } from '@/lib/format'

import { DownloadMenu } from './DownloadMenu'

const numbersLine = (numbers: string[], grNo: string) => (numbers.length > 1 ? `G.R. Nos. ${numbers.join(', ')}` : `G.R. No. ${numbers[0] ?? grNo}`)

/** The table of the drawing: Case | G.R. No. + date and ponente | View / Download. One row per main case. On a phone each row is a card. */
export function LibraryTable({ cases, caption = 'Saved cases, newest decision first' }: { cases: CaseSummary[]; caption?: string }) {
  const navigate = useNavigate()
  const openDigest = (id: number) => void navigate({ to: '/cases/$caseId/digest', params: { caseId: String(id) } })

  return (
    <table className="w-full border-collapse text-base">
      <caption className="sr-only">{caption}</caption>
      <thead className="sr-only md:not-sr-only">
        <tr className="border-b border-border text-left text-sm text-muted-foreground">
          <th scope="col" className="py-2 pr-4 font-medium">{libraryCopy.columnCase}</th>
          <th scope="col" className="py-2 pr-4 font-medium">{libraryCopy.columnNumber}</th>
          <th scope="col" className="py-2 font-medium">{libraryCopy.columnActions}</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((item) => {
          const name = shortCaseName(item.title)
          return (
            <tr key={item.id} className="grid gap-y-2 border-b border-border py-4 md:table-row md:py-0">
              <td className="md:py-4 md:pr-4 md:align-top">
                <Link
                  to="/cases/$caseId"
                  params={{ caseId: String(item.id) }}
                  className="font-serif text-lg leading-snug font-semibold text-primary underline-offset-4 hover:underline"
                >
                  {name}
                </Link>
                {item.subjects.length > 0 ? (
                  <ul className="mt-1.5 flex flex-wrap gap-1" aria-label="Subject tags">
                    {item.subjects.map((s) => (
                      <li key={s.id} className="rounded-full border border-border px-2 py-0.5 text-xs">
                        {s.name}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm text-muted-foreground">{libraryCopy.noSubjectYet}</p>
                )}
              </td>
              <td className="tabular text-base md:py-4 md:pr-4 md:align-top">
                <span className="block">{numbersLine(item.numbers, item.gr_no)}</span>
                <span className="block text-sm text-muted-foreground">
                  {formatDate(item.decision_date)}
                  {item.ponente ? ` · ${libraryCopy.ponente(justiceName(item.ponente))}` : ''}
                </span>
              </td>
              <td className="md:py-4 md:align-top">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  <Link to="/cases/$caseId/digest" params={{ caseId: String(item.id) }} className="text-primary underline-offset-4 hover:underline">
                    {libraryCopy.caseDigest}{' '}
                    <span className="sr-only">of {name}</span>
                  </Link>
                  <Link to="/cases/$caseId/decision" params={{ caseId: String(item.id) }} className="text-primary underline-offset-4 hover:underline">
                    {libraryCopy.fullText}{' '}
                    <span className="sr-only">of {name}</span>
                  </Link>
                  <DownloadMenu caseId={item.id} caseName={name} digestReady={item.digest_ready} onNeedDigest={() => openDigest(item.id)} />
                </div>
                {item.digest_state === 'pending' ? (
                  <p role="status" className="mt-2 text-sm text-muted-foreground">{libraryCopy.digestWriting}</p>
                ) : item.digest_state === 'failed' ? (
                  <p className="mt-2 text-sm text-look">{libraryCopy.digestFailed}</p>
                ) : null}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
