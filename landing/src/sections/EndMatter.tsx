import { ArrowRight, Monitor, Scale } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { closeCopy, footerCopy, heroCopy, notes, siteCopy } from '@/copy'
import { appLink, DESKTOP_URL } from '@/lib/links'
import { stagger } from '@/lib/useReveal'

/** The page closes on a panel like the hero's, in the app's ink-blue, with the one thing left to do. */
export function Close() {
  return (
    <section aria-labelledby="close-title" className="relative overflow-hidden rounded-2xl bg-sidebar py-20 text-center text-sidebar-foreground rails md:py-28">
      <div aria-hidden className="absolute inset-y-0 rail-left w-px bg-sidebar-border" />
      <div aria-hidden className="absolute inset-y-0 rail-right w-px bg-sidebar-border" />
      <h2 id="close-title" data-reveal className="relative mx-auto max-w-[20ch] px-4 font-serif text-4xl leading-tight font-semibold tracking-[-0.02em] md:text-5xl">
        {closeCopy.title}
      </h2>
      <p data-reveal style={stagger(1)} className="relative mt-4 px-4 text-lg text-sidebar-muted">{closeCopy.lead}</p>
      <div data-reveal style={stagger(2)} className="relative mt-9 flex flex-wrap items-center justify-center gap-3 px-4">
        <Button asChild size="lg" className="bg-gilt text-sidebar-primary-foreground hover:bg-gilt/90">
          <a href={appLink('/individual')}>
            {siteCopy.openApp}
            <ArrowRight aria-hidden />
          </a>
        </Button>
        <Button
          asChild
          size="lg"
          variant="outline"
          className="border-sidebar-border bg-transparent text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
        >
          <a href={DESKTOP_URL}>
            <Monitor aria-hidden />
            {heroCopy.desktop}
          </a>
        </Button>
      </div>
    </section>
  )
}

/** The notes the page's superscripts point to, then the sources. */
export function Notes() {
  return (
    <section id="notes" aria-labelledby="notes-title" className="scroll-mt-4 rails pt-16 pb-10">
      <div className="px-6 md:px-8">
      <h2 id="notes-title" className="text-sm font-semibold text-muted-foreground">
        {footerCopy.notesTitle}
      </h2>
      <ol className="mt-4 max-w-[75ch] space-y-3 text-sm leading-relaxed text-muted-foreground">
        {notes.map((note, i) => (
          <li key={note.id} id={`note-${note.id}`} className="grid scroll-mt-24 grid-cols-[1.5rem_minmax(0,1fr)] target:text-foreground">
            <span className="tabular font-semibold text-primary">{i + 1}</span>
            <span>
              {note.text}{' '}
              <a href={`#ref-${note.id}`} className="font-medium whitespace-nowrap text-primary underline-offset-4 hover:underline">
                {footerCopy.back}
                <span className="sr-only">{footerCopy.backLabel(i + 1)}</span>
              </a>
            </span>
          </li>
        ))}
      </ol>

      <div className="mt-14 border-t border-border pt-10">
        <h2 className="text-sm font-semibold text-muted-foreground">{footerCopy.sourcesTitle}</h2>
        <p className="mt-3 max-w-[75ch] text-sm leading-relaxed text-muted-foreground">{footerCopy.sources}</p>
      </div>

      <footer className="mt-14 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border pt-6 text-sm text-muted-foreground">
        <Scale className="size-4 text-primary" aria-hidden />
        <span className="font-semibold text-foreground">{siteCopy.name}</span>
        <span>{footerCopy.made}</span>
      </footer>
      </div>
    </section>
  )
}
