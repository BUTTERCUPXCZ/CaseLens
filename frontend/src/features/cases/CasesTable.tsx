import { Link } from '@tanstack/react-router'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'

import type { CaseSummary } from '@/api/types'
import { dispositionLabel } from '@/lib/copy'
import { divisionName, formatDate, justiceName, shortCaseName } from '@/lib/format'

const column = createColumnHelper<CaseSummary>()

const columns = [
  column.accessor('title', {
    header: 'Case',
    cell: (info) => (
      <Link
        to="/cases/$caseId"
        params={{ caseId: String(info.row.original.id) }}
        className="font-serif text-lg leading-snug font-semibold text-primary underline-offset-4 hover:underline"
      >
        {shortCaseName(info.getValue())}
      </Link>
    ),
  }),
  column.accessor('gr_no', { header: 'G.R. No.', cell: (info) => <span className="tabular">{info.getValue()}</span> }),
  column.accessor('decision_date', { header: 'Decided', cell: (info) => <span className="tabular">{formatDate(info.getValue())}</span> }),
  column.display({
    id: 'who',
    header: 'Decided by',
    cell: (info) => {
      const { ponente, division } = info.row.original
      return (
        <>
          {ponente ? <span className="block">Justice {justiceName(ponente)}</span> : null}
          {division ? <span className="block text-sm text-muted-foreground">{divisionName(division)}</span> : null}
        </>
      )
    },
  }),
  column.accessor('disposition', { header: 'Ruling', cell: (info) => dispositionLabel[info.getValue()] }),
]

/** The library as a table on a laptop and as stacked entries on a phone. Paging and search are
 *  done by the server, so this only draws the page it was given. */
export function CasesTable({ cases }: { cases: CaseSummary[] }) {
  'use no memo' // TanStack Table returns functions that change identity; opt out of React Compiler memoization
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table; this component opts out of memoization above
  const table = useReactTable({ data: cases, columns, getCoreRowModel: getCoreRowModel(), manualPagination: true })

  return (
    <table className="w-full border-collapse text-base">
      <caption className="sr-only">Saved cases, newest decision first</caption>
      <thead className="sr-only md:not-sr-only">
        {table.getHeaderGroups().map((group) => (
          <tr key={group.id} className="border-b border-border text-left text-sm text-muted-foreground">
            {group.headers.map((header) => (
              <th key={header.id} scope="col" className="py-2 pr-4 font-medium">
                {flexRender(header.column.columnDef.header, header.getContext())}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id} className="grid grid-cols-2 gap-x-4 gap-y-1 border-b border-border py-4 md:table-row md:py-0">
            {row.getVisibleCells().map((cell, index) => (
              <td
                key={cell.id}
                className={`py-1 pr-4 md:py-4 md:align-top ${index === 0 ? 'col-span-2' : 'md:whitespace-nowrap'}`}
                data-label={String(cell.column.columnDef.header)}
              >
                <span className="mb-0.5 block text-xs text-muted-foreground md:hidden">
                  {index === 0 ? '' : String(cell.column.columnDef.header)}
                </span>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
