import { Link } from '@tanstack/react-router'
import { X } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { welcomeCopy } from '@/lib/copy'

const KEY = 'caselens:welcome-dismissed'

/** Storage can be blocked (a private window, site data turned off): then the card simply shows again next visit. */
function wasDismissed(): boolean {
  try {
    return window.localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

function remember(): void {
  try {
    window.localStorage.setItem(KEY, '1')
  } catch {
    // Nothing to do: the card is closed for this visit anyway.
  }
}

/** Four short steps for a new student, with a link to the full guide. Closes for good with "Got it". */
export function WelcomeCard() {
  const [open, setOpen] = useState(() => !wasDismissed())
  if (!open) return null

  function close() {
    remember()
    setOpen(false)
  }

  return (
    <section aria-labelledby="welcome-title" className="mb-8 rounded-lg bg-muted px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <h2 id="welcome-title" className="text-lg font-semibold">
          {welcomeCopy.title}
        </h2>
        <Button variant="ghost" size="icon" aria-label={welcomeCopy.dismissLabel} onClick={close}>
          <X aria-hidden />
        </Button>
      </div>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-base">
        {welcomeCopy.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button asChild variant="outline">
          <Link to="/guide">{welcomeCopy.guide}</Link>
        </Button>
        <Button onClick={close}>{welcomeCopy.dismiss}</Button>
      </div>
    </section>
  )
}
