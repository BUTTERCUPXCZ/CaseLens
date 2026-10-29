import type { CSSProperties } from 'react'

import { downloadsCopy } from '@/copy'
import { stagger } from '@/lib/useReveal'
import { Cell, Chapter, RuledGrid } from '@/sections/Chapter'

/** How many pages each file runs to, drawn as that many sheets in a small stack. */
const STACK = [1, 2, 6]

/** The three Word files as paper: one digest, three lengths. */
export function Downloads() {
  return (
    <Chapter id="downloads" title={downloadsCopy.title} lead={downloadsCopy.lead}>
      <RuledGrid className="sm:grid-cols-3">
        {downloadsCopy.sheets.map((sheet, i) => (
          <Cell key={sheet.title} data-reveal style={stagger(i)} className={i < 2 ? 'sm:border-r' : ''}>
            <div className="flex justify-center rounded-lg bg-accent/30 px-6 pt-8 pb-10">
            <div className="relative aspect-[1/1.294] w-full max-w-[12.5rem]">
              {/* The pages behind the first, each a little lower and to the right. */}
              {Array.from({ length: STACK[i] - 1 }, (_, back) => STACK[i] - 1 - back).map((depth) => (
                <div
                  key={depth}
                  aria-hidden
                  className="fan-page absolute inset-0 rounded-sm border border-border bg-card"
                  style={{ '--d': depth } as CSSProperties}
                />
              ))}
              <div className="absolute inset-0 overflow-hidden rounded-sm border border-border bg-card p-5 shadow-[0_10px_24px_-18px_color-mix(in_oklch,var(--foreground)_40%,transparent)]">
                <p className="font-serif text-xs leading-tight font-semibold">Review Center v. Ermita</p>
                <p className="tabular mt-0.5 text-[0.65rem] text-muted-foreground">G.R. No. 180046, April 2, 2009</p>
                <div className="mt-4 space-y-2.5" aria-hidden>
                  {sheet.lines.slice(0, 6).map((line) => (
                    <div key={line}>
                      <p className="text-[0.65rem] font-semibold">{line}</p>
                      <div className="mt-1 h-px bg-border" />
                      <div className="mt-1 h-px w-4/5 bg-border" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
            </div>
            <h3 className="mt-6 text-lg font-semibold">{sheet.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{sheet.note}</p>
            <p className="sr-only">Sections: {sheet.lines.join(', ')}.</p>
          </Cell>
        ))}
        <Cell className="text-center sm:col-span-3">
          <p className="mx-auto max-w-[62ch] text-base leading-relaxed text-muted-foreground">{downloadsCopy.fullCase}</p>
        </Cell>
      </RuledGrid>
    </Chapter>
  )
}
