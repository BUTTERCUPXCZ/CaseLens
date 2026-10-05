import type { GuideStep } from '@/lib/copy'

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
          </div>
        </li>
      ))}
    </ol>
  )
}
