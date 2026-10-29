import { siteCopy } from '@/copy'
import { useCurrentChapter } from '@/lib/useCurrentChapter'
import { useReveal } from '@/lib/useReveal'
import { Close, Notes } from '@/sections/EndMatter'
import { Downloads } from '@/sections/Downloads'
import { HowItWorks } from '@/sections/HowItWorks'
import { Library } from '@/sections/Library'
import { Limits } from '@/sections/Limits'
import { TheCheck } from '@/sections/TheCheck'
import { TitlePage } from '@/sections/TitlePage'

/** The landing page: the hero panel (with the page's one navbar), then each part on the same column as the hero's rails. */
export function App() {
  const current = useCurrentChapter()
  useReveal()
  return (
    <>
      <a
        href="#title-heading"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        {siteCopy.skip}
      </a>
      <main id="main" className="page-frame">
        <div className="relative">
          {/* The two guide rails, running the full height of the page at the hero's margins. */}
          <div aria-hidden className="pointer-events-none absolute inset-y-0 rail-left w-px bg-border" />
          <div aria-hidden className="pointer-events-none absolute inset-y-0 rail-right w-px bg-border" />
          <TitlePage current={current} />
          <HowItWorks />
          <TheCheck />
          <Library />
          <Downloads />
          <Limits />
          <Close />
          <Notes />
        </div>
      </main>
    </>
  )
}
