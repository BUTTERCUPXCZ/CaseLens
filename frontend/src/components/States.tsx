import type { LucideIcon } from 'lucide-react'
import { AlertCircle } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { friendlyError } from '@/lib/copy'

/** Nothing here yet: say what this place is for and what to do first. */
export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-input px-6 py-12 text-center">
      <Icon className="mb-4 size-8 text-muted-foreground" aria-hidden />
      <h2 className="text-lg font-semibold">{title}</h2>
      {children ? <p className="mt-2 max-w-md text-base text-muted-foreground">{children}</p> : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  )
}

/** Something failed: say it in plain words and offer the way forward. */
export function ErrorState({ error, onRetry, title = "Something didn't load" }: {
  error: unknown
  onRetry?: () => void
  title?: string
}) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-lg bg-problem-wash px-5 py-4 text-problem">
      <div className="flex items-center gap-2 font-semibold">
        <AlertCircle className="size-5 shrink-0" aria-hidden />
        {title}
      </div>
      <p className="text-base">{friendlyError(error)}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  )
}
