import { Check, Search } from 'lucide-react'
import type { ReactNode } from 'react'

import { howCopy } from '@/copy'
import { sampleCase } from '@/demo/sample'
import { stagger } from '@/lib/useReveal'
import { Chapter } from '@/sections/Chapter'

/** The lines between the cells: two to a row on a tablet, four on a laptop. */
const DIVIDERS = ['md:border-r', 'md:border-r-0 xl:border-r', 'md:border-r', '']

/** Four steps in a ruled row, each with the piece of the app it happens in. The order is the information, so they keep numbers. */
export function HowItWorks() {
  const pictures: ReactNode[] = [<GiveIt key="give" />, <Sources key="sources" />, <Checked key="checked" />, <Sheets key="sheets" />]
  return (
    <Chapter id="how" title={howCopy.title} lead={howCopy.lead}>
      {/* A RuledGrid and its Cells, as a list: the grid is the <ol> and each cell an <li>. */}
      <ol className="grid border-t border-border md:grid-cols-2 xl:grid-cols-4">
          {howCopy.steps.map((step, i) => (
            <li key={step.title} data-reveal style={stagger(i)} className={`flex flex-col border-b border-border p-6 md:p-8 ${DIVIDERS[i]}`}>
                <div aria-hidden className="flex h-32 items-center justify-center rounded-lg border border-border bg-accent/40 p-4">
                  {pictures[i]}
                </div>
                <p className="tabular mt-6 font-serif text-lg text-primary" aria-hidden>
                  {String(i + 1).padStart(2, '0')}
                </p>
                <h3 className="mt-1 text-lg font-semibold">
                  <span className="sr-only">Step {i + 1}: </span>
                  {step.title}
                </h3>
                <p className="mt-2 text-base leading-relaxed text-muted-foreground">{step.body}</p>
            </li>
          ))}
      </ol>
    </Chapter>
  )
}

function GiveIt() {
  return (
    <div className="w-full max-w-[13rem] space-y-2">
      <div className="flex h-9 items-center gap-2 rounded-md border border-input bg-card px-2.5 text-sm">
        <Search className="size-3.5 text-muted-foreground" />
        <span className="tabular">{sampleCase.query}</span>
      </div>
      <span className="inline-block rounded-full border border-primary bg-card px-2.5 py-0.5 text-xs">{sampleCase.subject}</span>
    </div>
  )
}

function Sources() {
  return (
    <ul className="w-full max-w-[13rem] space-y-1.5 text-xs">
      {howCopy.sources.map((source) => (
        <li key={source.name} className="flex items-center justify-between gap-2 rounded-md border border-border bg-card px-2.5 py-2">
          <span className="font-medium">{source.name}</span>
          <span className="text-right text-muted-foreground">{source.when}</span>
        </li>
      ))}
    </ul>
  )
}

function Checked() {
  return (
    <div className="w-full max-w-[13rem] rounded-md border border-border bg-card p-2.5 text-xs leading-relaxed">
      <p>
        {howCopy.checkedSample}{' '}
        <span className="tabular rounded-sm border border-primary/30 px-1 font-semibold text-primary">P103</span>
      </p>
      <p className="mt-1.5 flex items-center gap-1 font-semibold text-match">
        <Check className="size-3.5" />
        {howCopy.supported}
      </p>
    </div>
  )
}

function Sheets() {
  return (
    <div className="flex items-end gap-2.5">
      {[2, 4, 7].map((lines) => (
        <div key={lines} className="flex aspect-[1/1.294] w-12 flex-col gap-1 rounded-[3px] border border-border bg-card p-1.5">
          {Array.from({ length: lines }, (_, i) => (
            <div key={i} className="h-px bg-border" />
          ))}
        </div>
      ))}
    </div>
  )
}
