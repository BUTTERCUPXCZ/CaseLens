import { useForm } from '@tanstack/react-form'
import { useNavigate } from '@tanstack/react-router'
import { Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { findCaseSchema } from '@/features/search/grNumber'
import { searchCopy } from '@/lib/copy'

/** In the Case library (and on the results page): type a case name or a G.R. number (and a year if you like) to find any decision on Lawphil. */
export function GrSearch({ initialQ = '', initialYear }: { initialQ?: string; initialYear?: number } = {}) {
  const navigate = useNavigate()
  const form = useForm({
    defaultValues: { q: initialQ, year: initialYear ? String(initialYear) : '' },
    validators: { onSubmit: findCaseSchema },
    onSubmit: ({ value }) => {
      void navigate({
        to: '/search',
        search: { q: value.q.trim(), year: value.year ? Number(value.year) : undefined, page: undefined },
      })
    },
  })

  return (
    <form
      role="search"
      aria-label="Search Lawphil"
      className="flex w-full max-w-2xl items-start gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
    >
      <form.Field name="q">
        {(field) => {
          const error = field.state.meta.errors[0]
          const message = typeof error === 'string' ? error : error?.message
          return (
            <div className="min-w-0 flex-1">
              <label htmlFor="case-search" className="mb-1 block text-sm font-medium">
                {searchCopy.boxLabel}
              </label>
              <Input
                id="case-search"
                type="search"
                placeholder={searchCopy.boxPlaceholder}
                autoComplete="off"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                aria-invalid={message ? true : undefined}
                aria-describedby={message ? 'case-search-error' : undefined}
              />
              {message ? (
                <p id="case-search-error" role="alert" className="mt-1 text-sm text-problem">
                  {message}
                </p>
              ) : null}
            </div>
          )
        }}
      </form.Field>

      <form.Field name="year">
        {(field) => {
          const error = field.state.meta.errors[0]
          const message = typeof error === 'string' ? error : error?.message
          return (
            <div className="w-24 shrink-0">
              <label htmlFor="year-search" className="mb-1 block text-sm font-medium">
                {searchCopy.yearLabel}
              </label>
              <Input
                id="year-search"
                placeholder={searchCopy.yearPlaceholder}
                inputMode="numeric"
                maxLength={4}
                autoComplete="off"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                aria-invalid={message ? true : undefined}
                aria-describedby={message ? 'year-search-error' : undefined}
              />
              {message ? (
                <p id="year-search-error" role="alert" className="mt-1 text-sm text-problem">
                  {message}
                </p>
              ) : null}
            </div>
          )
        }}
      </form.Field>

      <Button type="submit" className="mt-6 shrink-0">
        <Search data-icon="inline-start" aria-hidden />
        Search
      </Button>
    </form>
  )
}
