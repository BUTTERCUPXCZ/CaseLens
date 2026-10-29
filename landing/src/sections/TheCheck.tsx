import { Check, X } from 'lucide-react'

import { checkCopy } from '@/copy'
import { digest } from '@/demo/sample'
import { stagger } from '@/lib/useReveal'
import { Cell, Chapter, NoteRef, RuledGrid } from '@/sections/Chapter'

const kept = digest[3].sentences[0]
const struck = digest[3].sentences[1]

/** What happens to one sentence before a student sees it, as a ruled flow; beside it, two real sentences of the sample
 *  going through it, one kept and one struck out. */
export function TheCheck() {
  return (
    <Chapter id="check" title={checkCopy.title} lead={checkCopy.lead}>
      <RuledGrid className="lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)]">
        <Cell className="lg:border-r">
        <ol className="relative">
          {checkCopy.stages.map((stage, i) => {
            const last = i === checkCopy.stages.length - 1
            return (
              <li key={stage.title} data-reveal style={stagger(i)} className="relative grid grid-cols-[2rem_minmax(0,1fr)] pb-9 last:pb-0">
                {/* The rule that runs through the steps, and its mark at each one. */}
                {!last ? <span aria-hidden data-reveal="draw-y" style={stagger(i + 1)} className="absolute top-3 bottom-0 left-[0.4375rem] w-px bg-border" /> : null}
                <span
                  aria-hidden
                  className={['relative mt-1.5 size-[0.875rem] rounded-[3px] border-2', last ? 'border-redpen bg-background' : 'border-primary bg-background'].join(' ')}
                />
                <div>
                  <h3 className="text-lg font-semibold">
                    {last ? <span className="line-through decoration-redpen decoration-2">{stage.title}</span> : stage.title}
                  </h3>
                  <p className="mt-1.5 max-w-[56ch] text-base leading-relaxed text-muted-foreground">{stage.body}</p>
                </div>
              </li>
            )
          })}
        </ol>
        </Cell>

        <Cell className="space-y-4 bg-accent/30">
          <Ledger
            order={2}
            verdict="kept"
            sentence={kept.text}
            cite={kept.cites[0]}
            steps={checkCopy.kept.steps}
          />
          <Ledger
            order={4}
            verdict="struck"
            sentence={struck.text}
            cite={struck.cites[0]}
            steps={checkCopy.struck.steps}
          />
        </Cell>

        <Cell className="py-12 text-center md:py-16 lg:col-span-2">
          <p data-reveal className="mx-auto max-w-[38ch] font-serif text-2xl leading-snug text-balance md:text-3xl">
            {checkCopy.resultLead} <span className="font-semibold">{checkCopy.result}</span>
            <NoteRef n={1} />
          </p>
          <p className="mt-4 text-base text-muted-foreground">{checkCopy.draftNote}</p>
        </Cell>
      </RuledGrid>
    </Chapter>
  )
}

/** One sentence's record through the checks. */
function Ledger({ order, verdict, sentence, cite, steps }: { order: number; verdict: 'kept' | 'struck'; sentence: string; cite: string; steps: string[] }) {
  const isKept = verdict === 'kept'
  return (
    <figure data-reveal style={stagger(order)} className="rounded-lg border border-border bg-card p-5">
      <blockquote className="text-base leading-relaxed">
        <span className={isKept ? undefined : 'text-muted-foreground line-through decoration-redpen decoration-2'}>{sentence}</span>{' '}
        <span className={['tabular inline-block rounded-sm border px-1 text-xs font-semibold', isKept ? 'border-primary/30 text-primary' : 'border-redpen/50 text-redpen'].join(' ')}>
          {cite}
        </span>
      </blockquote>
      <ul className="mt-3 space-y-1 border-t border-border pt-3 text-sm text-muted-foreground">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
      <figcaption className={['mt-3 flex items-center gap-1.5 text-sm font-semibold', isKept ? 'text-match' : 'text-redpen'].join(' ')}>
        {isKept ? <Check className="size-4" aria-hidden /> : <X className="size-4" aria-hidden />}
        {isKept ? checkCopy.kept.verdict : checkCopy.struck.verdict}
      </figcaption>
    </figure>
  )
}
