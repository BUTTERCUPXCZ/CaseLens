import type { HTMLAttributes, ReactNode } from 'react'

import { stagger } from '@/lib/useReveal'

/** One part of the page, in the hero's frame: it opens on a hairline that crosses the page's two rails (a node at each
 *  crossing), a centred heading and lead, then its content between the rails. */
export function Chapter({
  id,
  title,
  lead,
  children,
}: {
  id: string
  title: string
  lead?: ReactNode
  children: ReactNode
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="relative scroll-mt-4 pt-20 pb-24 md:pt-28 md:pb-32">
      <RailRule />
      <div className="rails">
        <header data-reveal className="mx-auto max-w-3xl px-4 text-center">
          <h2 id={`${id}-title`} className="font-serif text-3xl leading-tight font-semibold tracking-[-0.02em] text-balance md:text-5xl">
            {title}
          </h2>
          {lead ? <p className="mx-auto mt-5 max-w-[58ch] text-lg leading-relaxed text-pretty text-muted-foreground">{lead}</p> : null}
        </header>
        <div className="mt-14 md:mt-16">{children}</div>
      </div>
    </section>
  )
}

/** The hairline across the frame at the top of a part, with a node where it meets each rail. */
export function RailRule({ className = 'top-0' }: { className?: string }) {
  return (
    <div aria-hidden className={`absolute inset-x-0 ${className}`}>
      <div data-reveal="rule" className="h-px bg-border" />
      <span data-reveal style={stagger(6)} className="absolute top-0 rail-left size-[7px] -translate-x-[3px] -translate-y-[3px] rounded-[2px] border border-primary/25 bg-background" />
      <span data-reveal style={stagger(6)} className="absolute top-0 rail-right size-[7px] translate-x-[3px] -translate-y-[3px] rounded-[2px] border border-primary/25 bg-background" />
    </div>
  )
}

/** A hairline grid that fills the column exactly, so its outer edges are the rails: cells, not floating cards. */
export function RuledGrid({ className, children }: { className: string; children: ReactNode }) {
  return <div className={`grid border-t border-border ${className}`}>{children}</div>
}

/** One cell of a RuledGrid. */
export function Cell({ className = '', children, ...rest }: HTMLAttributes<HTMLDivElement> & { 'data-reveal'?: string | boolean }) {
  return (
    <div {...rest} className={`border-b border-border p-6 md:p-8 ${className}`}>
      {children}
    </div>
  )
}

/** A superscript note number linking to its note at the end, the way a decision links to its footnotes. */
export function NoteRef({ n }: { n: number }) {
  return (
    <sup className="ml-0.5">
      <a href={`#note-n${n}`} id={`ref-n${n}`} className="tabular text-[0.7em] font-semibold text-primary no-underline hover:underline">
        {n}
      </a>
    </sup>
  )
}
