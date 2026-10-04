import { useForm } from '@tanstack/react-form'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { friendlyError } from '@/lib/copy'

import { lawphilLinkSchema } from './lawphilLink'

/** One text box for the case's own Lawphil link. The caller decides what happens with it. */
export function LawphilLinkForm({
  id,
  submitLabel,
  pendingLabel,
  pending,
  error,
  onSubmit,
}: {
  id: string
  submitLabel: string
  pendingLabel: string
  pending: boolean
  error: unknown
  onSubmit: (url: string) => Promise<unknown>
}) {
  const form = useForm({
    defaultValues: { url: '' },
    validators: { onSubmit: lawphilLinkSchema },
    onSubmit: async ({ value }) => {
      try {
        await onSubmit(value.url.trim())
      } catch {
        // The failure is already on screen through the `error` prop; nothing more to do here.
      }
    },
  })

  return (
    <form
      className="mt-4"
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
    >
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
        Paste the case&rsquo;s Lawphil link
      </label>
      <form.Field name="url">
        {(field) => {
          const problem = field.state.meta.errors[0]
          const message = typeof problem === 'string' ? problem : problem?.message
          return (
            <div className="flex flex-wrap items-start gap-2">
              <div className="min-w-64 flex-1">
                <Input
                  id={id}
                  type="url"
                  inputMode="url"
                  placeholder="https://lawphil.net/judjuris/…"
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                  aria-invalid={message ? true : undefined}
                  aria-describedby={message ? `${id}-error` : undefined}
                />
                {message ? (
                  <p id={`${id}-error`} role="alert" className="mt-1 text-sm text-problem">
                    {message}
                  </p>
                ) : null}
              </div>
              <Button type="submit" disabled={pending}>
                {pending ? pendingLabel : submitLabel}
              </Button>
            </div>
          )
        }}
      </form.Field>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-problem">
          {friendlyError(error)}
        </p>
      ) : null}
    </form>
  )
}
