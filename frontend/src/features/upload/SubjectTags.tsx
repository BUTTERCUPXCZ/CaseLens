import { useQuery } from '@tanstack/react-query'
import { Check } from 'lucide-react'

import { subjectListQuery } from '@/api/queries'
import { Skeleton } from '@/components/ui/skeleton'
import { uploadCopy } from '@/lib/copy'

/** The client's chips: the student labels the case with one or more subjects (nothing is guessed for them). */
export function SubjectTags({
  value,
  onChange,
  disabled,
  id = 'subject-tags',
  help = uploadCopy.tagsHelp,
}: {
  value: number[]
  onChange: (next: number[]) => void
  disabled?: boolean
  id?: string
  help?: string
}) {
  const { data: subjects } = useQuery(subjectListQuery())
  const toggle = (subjectId: number) => onChange(value.includes(subjectId) ? value.filter((v) => v !== subjectId) : [...value, subjectId])

  return (
    <div role="group" aria-labelledby={`${id}-label`} aria-describedby={`${id}-help`}>
      <p id={`${id}-label`} className="mb-2 text-sm font-medium">
        {uploadCopy.tagsLabel}
      </p>
      {subjects ? (
        <ul className="flex flex-wrap gap-2">
          {subjects.map((subject) => {
            const on = value.includes(subject.id)
            return (
              <li key={subject.id}>
                <button
                  type="button"
                  aria-pressed={on}
                  disabled={disabled}
                  onClick={() => toggle(subject.id)}
                  className={[
                    'inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:opacity-50',
                    on ? 'border-primary bg-primary text-primary-foreground' : 'border-input bg-card text-foreground hover:bg-accent',
                  ].join(' ')}
                >
                  {on ? <Check className="size-3.5" aria-hidden /> : null}
                  {subject.name}
                </button>
              </li>
            )
          })}
        </ul>
      ) : (
        <Skeleton className="h-20 w-full" aria-label="Loading the subjects" />
      )}
      <p className="mt-2 text-sm font-medium" aria-live="polite">
        {uploadCopy.tagsCount(value.length)}
      </p>
      <p id={`${id}-help`} className="text-sm text-muted-foreground">
        {help}
      </p>
    </div>
  )
}
