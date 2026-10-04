import type { CitationStatus } from '@/api/types'
import { StatusBadge } from '@/features/reviews/StatusBadge'
import { guideCopy, type GuideExample, type GuideStep } from '@/lib/copy'

const LABEL_ORDER: CitationStatus[] = ['match', 'mismatch', 'not_found', 'error', 'pending']

function Example({ kind }: { kind: GuideExample }) {
  if (kind === 'redpen') {
    return (
      <p className="mt-3 max-w-prose rounded-lg bg-muted px-4 py-3 text-base">
        <del className="tabular text-redpen decoration-2">April 2, 2010</del>{' '}
        <ins className="tabular rounded-sm bg-look-wash px-1 font-semibold text-foreground no-underline">April 2, 2009</ins>
        <span className="mt-1 block text-sm text-muted-foreground">{guideCopy.redpenCaption}</span>
      </p>
    )
  }
  return (
    <div className="mt-3">
      <ul className="flex flex-wrap gap-2">
        {LABEL_ORDER.map((status) => (
          <li key={status}>
            <StatusBadge status={status} />
          </li>
        ))}
      </ul>
      <p className="mt-2 text-sm text-muted-foreground">{guideCopy.labelsCaption}</p>
    </div>
  )
}

/** The numbered steps. Each is a list item with its own heading, so a screen reader can jump between them. */
export function GuideSteps({ steps }: { steps: GuideStep[] }) {
  return (
    <ol className="space-y-8">
      {steps.map((step, index) => (
        <li key={step.title} className="flex gap-4">
          <span
            aria-hidden
            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-base font-semibold text-primary-foreground"
          >
            {index + 1}
          </span>
          <div className="min-w-0">
            <h3 className="text-lg font-semibold">
              <span className="sr-only">Step {index + 1}: </span>
              {step.title}
            </h3>
            {step.body.map((paragraph) => (
              <p key={paragraph} className="mt-2 max-w-prose text-base leading-relaxed">
                {paragraph}
              </p>
            ))}
            {step.example ? <Example kind={step.example} /> : null}
          </div>
        </li>
      ))}
    </ol>
  )
}
