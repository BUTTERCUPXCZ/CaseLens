import { Check, Minus, PenLine } from 'lucide-react'

import { type CompareRow, type Verdict } from './compareRows'

const VERDICT = {
  same: { Icon: Check, words: 'Same', className: 'text-match' },
  differs: { Icon: PenLine, words: 'Different', className: 'text-look' },
  unchecked: { Icon: Minus, words: "Can't be checked", className: 'text-muted-foreground' },
} as const satisfies Record<Verdict, { Icon: typeof Check; words: string; className: string }>

/** What the student wrote, set against what the Court's record says.
 *
 *  The signature move: a value that differs is marked the way a proofreader would. What the
 *  student wrote is struck through in red pen (<del>) and the Court's value stands beside it
 *  (<ins>). The words "Different" / "Same" carry the meaning too, so it never rests on colour. */
export function CompareTable({ rows, hasRecord }: { rows: CompareRow[]; hasRecord: boolean }) {
  return (
    <table className="w-full border-collapse text-base">
      <caption className="sr-only">What you wrote compared with the Court's record</caption>
      <thead className="sr-only sm:not-sr-only">
        <tr className="border-b border-border text-left text-sm text-muted-foreground">
          <th scope="col" className="w-36 py-2 pr-4 font-medium">
            Detail
          </th>
          <th scope="col" className="py-2 pr-4 font-medium">
            What you wrote
          </th>
          <th scope="col" className="py-2 pr-4 font-medium">
            The Court&rsquo;s record says
          </th>
          <th scope="col" className="w-40 py-2 font-medium">
            Result
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const verdict = VERDICT[row.verdict]
          return (
            <tr
              key={row.key}
              className="grid grid-cols-1 gap-y-1 border-b border-border py-3 last:border-b-0 sm:table-row sm:py-0"
            >
              <th scope="row" className="py-1 text-left text-sm font-medium text-muted-foreground sm:py-3 sm:pr-4 sm:align-top">
                {row.label}
              </th>

              <td className="py-1 sm:py-3 sm:pr-4 sm:align-top">
                <span className="mb-0.5 block text-sm text-muted-foreground sm:hidden">You wrote</span>
                {row.verdict === 'differs' ? (
                  <del className="tabular text-redpen decoration-2" aria-label={`You wrote ${row.wrote}, which is different`}>
                    {row.wrote}
                  </del>
                ) : (
                  <span className="tabular">{row.wrote}</span>
                )}
              </td>

              <td className="py-1 sm:py-3 sm:pr-4 sm:align-top">
                <span className="mb-0.5 block text-sm text-muted-foreground sm:hidden">The Court&rsquo;s record says</span>
                {row.record ? (
                  row.verdict === 'differs' ? (
                    <ins className="tabular rounded-sm bg-look-wash px-1 font-semibold no-underline">{row.record}</ins>
                  ) : (
                    <span className="tabular">{row.record}</span>
                  )
                ) : (
                  <span className="text-muted-foreground">{hasRecord ? 'Not on the Court’s page' : '—'}</span>
                )}
                {row.note ? <p className="mt-1 max-w-prose text-sm text-muted-foreground">{row.note}</p> : null}
              </td>

              <td className="py-1 sm:py-3 sm:align-top">
                <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${verdict.className}`}>
                  <verdict.Icon className="size-4" aria-hidden />
                  {verdict.words}
                </span>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
