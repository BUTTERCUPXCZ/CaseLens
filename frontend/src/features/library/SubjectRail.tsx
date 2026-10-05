import type { SubjectFilter } from '@/api/queries'
import type { SubjectCount } from '@/api/types'
import { libraryCopy } from '@/lib/copy'

/** A native select, styled like the app's inputs (on a phone the rail becomes this). */
const SELECT_CLASS =
  'h-10 w-full rounded-lg border border-input bg-card px-3 text-base outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50'

const toValue = (filter: SubjectFilter) => (filter === undefined ? 'all' : String(filter))
const fromValue = (value: string): SubjectFilter => (value === 'all' ? undefined : value === 'none' ? 'none' : Number(value))

/** The filter on the left of the drawing: every subject with how many cases it has. On a phone it is a list to choose from. */
export function SubjectRail({
  counts,
  selected,
  onSelect,
}: {
  counts: SubjectCount[]
  selected: SubjectFilter
  onSelect: (filter: SubjectFilter) => void
}) {
  const total = counts.reduce((sum, subject) => sum + subject.count, 0)
  const entries: { value: string; name: string; count: number }[] = [
    { value: 'all', name: libraryCopy.allCases, count: total },
    ...counts
      .filter((subject) => subject.subject_id !== null || subject.count > 0) // "No subject yet" only when there are such cases
      .map((subject) => ({ value: subject.subject_id === null ? 'none' : String(subject.subject_id), name: subject.name, count: subject.count })),
  ]

  return (
    <>
      <div className="md:hidden">
        <label htmlFor="subject-filter" className="mb-1 block text-sm font-medium">
          {libraryCopy.railTitle}
        </label>
        <select id="subject-filter" value={toValue(selected)} onChange={(event) => onSelect(fromValue(event.target.value))} className={SELECT_CLASS}>
          {entries.map((entry) => (
            <option key={entry.value} value={entry.value}>
              {entry.name} ({entry.count})
            </option>
          ))}
        </select>
      </div>

      <nav aria-label={libraryCopy.railTitle} className="hidden md:block">
        <h2 className="mb-2 text-sm font-semibold text-muted-foreground">{libraryCopy.railTitle}</h2>
        <ul className="space-y-0.5">
          {entries.map((entry) => {
            const active = entry.value === toValue(selected)
            return (
              <li key={entry.value}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => onSelect(fromValue(entry.value))}
                  className={`flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-base transition-colors focus-visible:outline-2 focus-visible:outline-ring ${
                    active ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'
                  }`}
                >
                  <span>{entry.name}</span>
                  <span className={`tabular text-sm ${active ? 'text-primary-foreground/80' : 'text-muted-foreground'}`}>{entry.count}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </nav>
    </>
  )
}
