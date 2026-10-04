import { createFileRoute, Link } from '@tanstack/react-router'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { GuideSteps } from '@/features/guide/GuideSteps'
import { guideCopy } from '@/lib/copy'

export const Route = createFileRoute('/guide')({
  component: Guide,
})

function Guide() {
  return (
    <>
      <PageHeader title={guideCopy.title} description={guideCopy.description} />
      <p className="mb-10 max-w-prose text-base leading-relaxed">{guideCopy.promise}</p>

      <section aria-labelledby="steps-title">
        <h2 id="steps-title" className="mb-6 text-xl font-semibold">
          {guideCopy.stepsTitle}
        </h2>
        <GuideSteps steps={guideCopy.steps} />
      </section>

      <section aria-labelledby="good-title" className="mt-12">
        <h2 id="good-title" className="mb-3 text-xl font-semibold">
          {guideCopy.goodToKnowTitle}
        </h2>
        <ul className="max-w-prose list-disc space-y-2 pl-5 text-base leading-relaxed">
          {guideCopy.goodToKnow.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="faq-title" className="mt-12">
        <h2 id="faq-title" className="mb-3 text-xl font-semibold">
          {guideCopy.faqTitle}
        </h2>
        <dl className="max-w-prose space-y-5">
          {guideCopy.faq.map((item) => (
            <div key={item.q}>
              <dt className="font-semibold">{item.q}</dt>
              <dd className="mt-1 text-base leading-relaxed text-muted-foreground">{item.a}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="mt-12">
        <Button asChild size="lg">
          <Link to="/">{guideCopy.start}</Link>
        </Button>
      </div>
    </>
  )
}
