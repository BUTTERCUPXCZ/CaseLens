import { ArrowDown, ArrowRight } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { heroCopy, type ChapterId } from '@/copy'
import { AppReplica } from '@/demo/AppReplica'
import { appLink } from '@/lib/links'
import { stagger } from '@/lib/useReveal'
import { Navbar } from '@/sections/Navbar'

/** The hero: a framed panel inset from the window, its nav and content held between two guide rails, the headline and the
 *  search centred, and the app itself at work below, rising out of the panel's lower edge. */
export function TitlePage({ current }: { current: ChapterId }) {
  return (
    <section id="title" aria-labelledby="title-heading" className="relative bg-background pt-3 pb-20 md:pb-28">
      <HeroPanel />
      <div className="relative rails">
        <Navbar current={current} />

        <div className="mx-auto flex max-w-4xl flex-col items-center pt-14 text-center md:pt-20">
          <h1
            id="title-heading"
            data-reveal
            className="max-w-[20ch] font-serif text-[2.5rem] leading-[1.05] font-semibold tracking-[-0.025em] sm:text-6xl xl:text-[4.25rem]"
          >
            {heroCopy.title}
          </h1>
          <p data-reveal style={stagger(1)} className="mt-6 max-w-[50ch] text-lg leading-relaxed text-pretty text-foreground/75">{heroCopy.lead}</p>
          <CaseSearch />
          <a
            href="#check"
            data-reveal
            style={stagger(3)}
            className="mt-5 inline-flex items-center gap-1.5 text-base font-medium text-primary underline-offset-4 hover:underline"
          >
            {heroCopy.seeHow}
            <ArrowDown className="size-4" aria-hidden />
          </a>
        </div>

        <div data-reveal style={stagger(4)} className="mt-12 md:mt-16">
          <AppReplica />
        </div>
      </div>
    </section>
  )
}

/** The panel behind the hero: a pale ink-blue wash, the two rails, the rule under the nav with a node where it crosses each
 *  rail, and a field of dots in each margin. It ends halfway down the app, so the app sits on the panel's edge. */
function HeroPanel() {
  return (
    <div
      aria-hidden
      className="absolute inset-x-0 top-3 bottom-[35rem] overflow-hidden rounded-2xl border border-primary/10 bg-[linear-gradient(to_bottom,var(--accent),color-mix(in_oklch,var(--accent)_45%,var(--background)))] @container sm:bottom-[31rem] md:bottom-[33rem]"
    >
      <div className="absolute inset-y-0 rail-left w-px bg-primary/12" />
      <div className="absolute inset-y-0 rail-right w-px bg-primary/12" />
      <div className="absolute inset-x-0 top-16 h-px bg-primary/12" />
      <span className="absolute top-16 rail-left size-[7px] -translate-x-[3px] -translate-y-[3px] rounded-[2px] border border-primary/25 bg-card" />
      <span className="absolute top-16 rail-right size-[7px] translate-x-[3px] -translate-y-[3px] rounded-[2px] border border-primary/25 bg-card" />
      <div className="hero-dots absolute top-16 left-0 hidden h-80 w-[9.8%] lg:block" />
      <div className="hero-dots absolute top-16 right-0 hidden h-80 w-[9.8%] lg:block" />
    </div>
  )
}

/** A real form: it sends the words to the app's search (/search?q=), and works without JavaScript too. */
function CaseSearch() {
  const [problem, setProblem] = useState(false)
  const action = appLink('/search')

  function submit(event: FormEvent<HTMLFormElement>) {
    const q = String(new FormData(event.currentTarget).get('q') ?? '').trim()
    if (q === '') {
      event.preventDefault()
      setProblem(true)
    }
  }

  return (
    <form data-reveal style={stagger(2)} action={action} method="get" noValidate onSubmit={submit} className="mt-8 w-full max-w-lg text-left" role="search">
      <label htmlFor="case-search" className="text-base font-medium">
        {heroCopy.searchLabel}
      </label>
      <div className="mt-2 flex gap-2">
        <Input
          id="case-search"
          name="q"
          type="search"
          autoComplete="off"
          placeholder={heroCopy.searchPlaceholder}
          aria-invalid={problem || undefined}
          aria-describedby="case-search-help"
          onChange={() => problem && setProblem(false)}
          className="h-12 flex-1 bg-card text-base md:text-base"
        />
        <Button type="submit" size="lg" className="h-12 px-6">
          {heroCopy.searchButton}
          <ArrowRight aria-hidden />
        </Button>
      </div>
      <p id="case-search-help" className={['mt-2 text-sm', problem ? 'font-medium text-problem' : 'text-muted-foreground'].join(' ')} aria-live="polite">
        {problem ? heroCopy.searchEmpty : heroCopy.searchHelp}
      </p>
    </form>
  )
}
