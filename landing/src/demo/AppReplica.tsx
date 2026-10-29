import { BookOpen, FileSearch, Layers, Library, Menu, Pause, Play, RotateCcw, Scale, Settings } from 'lucide-react'
import { useRef, useState } from 'react'

import { demoCopy } from '@/copy'
import { appLink } from '@/lib/links'
import { DigestScene } from '@/demo/scenes/DigestScene'
import { DownloadScene } from '@/demo/scenes/DownloadScene'
import { FindScene } from '@/demo/scenes/FindScene'
import { WriteScene } from '@/demo/scenes/WriteScene'
import { DURATION, SCENES, useDemo, type Scene } from '@/demo/useDemo'

const NAV_ICONS = [FileSearch, Layers, Library, BookOpen, Settings]

/** Which sidebar item the app shows as current, and the address it would be at, for each scene. */
const SCENE_PLACE: Record<Scene, { nav: number; path: string }> = {
  find: { nav: 0, path: '/individual' },
  write: { nav: 2, path: '/cases/1/digest' },
  digest: { nav: 2, path: '/cases/1/digest' },
  download: { nav: 2, path: '/cases/1/digest' },
}

/** A working miniature of the CaseLens window playing its real flow on a real decision. The look is the app's own (its sidebar,
 *  its page header, its digest); it runs on sample data with no server. */
export function AppReplica() {
  const frame = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState(false)
  const [focusInside, setFocusInside] = useState(false)
  const demo = useDemo(frame, hover || focusInside)
  const place = SCENE_PLACE[demo.scene]
  const step = SCENES.indexOf(demo.scene)
  const host = new URL(appLink('/')).host

  return (
    <figure aria-label={demoCopy.label} className="m-0">
      <div
        ref={frame}
        onPointerEnter={() => setHover(true)}
        onPointerLeave={() => setHover(false)}
        onFocus={() => setFocusInside(true)}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setFocusInside(false)
        }}
        className="@container overflow-hidden rounded-xl border border-border bg-background shadow-[0_24px_48px_-28px_color-mix(in_oklch,var(--foreground)_45%,transparent)]"
      >
        {/* The address strip says this is the web app, at the page each scene is on. */}
        <div className="flex items-center gap-2 border-b border-border bg-muted px-3 py-1.5 text-xs text-muted-foreground">
          <span className="truncate tabular" aria-hidden>
            {host}
            <span className="text-foreground/70">{place.path}</span>
          </span>
        </div>

        <div className="flex h-[34rem] @2xl:h-[36rem]">
          {/* The app's ink-blue sidebar; on a phone-width frame, the app's own phone header instead. */}
          <nav aria-label={demoCopy.navLabel} className="hidden w-48 shrink-0 flex-col bg-sidebar px-3 py-4 text-sidebar-foreground @2xl:flex">
            <p className="flex items-center gap-2 px-1 text-base font-semibold tracking-tight">
              <Scale className="size-5 text-gilt" aria-hidden />
              CaseLens
            </p>
            <ul className="mt-5 space-y-0.5">
              {demoCopy.nav.map((label, i) => {
                const Icon = NAV_ICONS[i]
                const current = i === place.nav
                return (
                  <li
                    key={label}
                    aria-current={current ? 'page' : undefined}
                    className={[
                      'flex items-center gap-2.5 rounded-md px-2 py-2 text-sm',
                      current ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground' : 'text-sidebar-foreground/85',
                    ].join(' ')}
                  >
                    <Icon className={['size-4', current ? 'text-gilt' : ''].join(' ')} aria-hidden />
                    {label}
                  </li>
                )
              })}
            </ul>
          </nav>

          <div className="flex min-w-0 flex-1 flex-col">
            <div className="flex items-center gap-2.5 border-b border-border px-4 py-2.5 @2xl:hidden" aria-hidden>
              <Menu className="size-4.5" />
              <Scale className="size-4.5 text-primary" />
              <span className="text-base font-semibold">CaseLens</span>
            </div>
            <div
              tabIndex={0}
              role="region"
              aria-label={demoCopy.chapters[step].label}
              className="min-h-0 flex-1 overflow-y-auto px-4 py-5 @2xl:px-7 @2xl:py-6"
            >
              <div key={demo.scene} className="replica-in">
                {demo.scene === 'find' ? <FindScene t={demo.t} onOpen={() => demo.go('write')} /> : null}
                {demo.scene === 'write' ? <WriteScene t={demo.t} /> : null}
                {demo.scene === 'digest' ? <DigestScene t={demo.t} playing={demo.playing} /> : null}
                {demo.scene === 'download' ? <DownloadScene t={demo.t} /> : null}
              </div>
            </div>
          </div>
        </div>
      </div>

      <ChapterStrip demo={demo} step={step} />
      <figcaption className="mt-3 max-w-prose text-sm text-muted-foreground">
        {demoCopy.sampleNote}
        <sup>
          <a href="#note-n2" id="ref-n2" className="ml-0.5 font-semibold text-primary">
            2
          </a>
        </sup>
      </figcaption>
    </figure>
  )
}

function ChapterStrip({ demo, step }: { demo: ReturnType<typeof useDemo>; step: number }) {
  const Toggle = demo.finished ? RotateCcw : demo.playing ? Pause : Play
  const toggleLabel = demo.finished ? demoCopy.replay : demo.playing ? demoCopy.pause : demoCopy.play
  const progress = demo.t / DURATION[demo.scene]

  return (
    <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-stretch">
      <button
        type="button"
        onClick={demo.toggle}
        className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 text-sm font-medium transition-colors hover:bg-muted"
      >
        <Toggle className="size-4" aria-hidden />
        {toggleLabel}
      </button>
      <ol aria-label={demoCopy.chaptersLabel} className="grid flex-1 grid-cols-2 gap-2 sm:grid-cols-4">
        {demoCopy.chapters.map((chapter, i) => {
          const current = i === step
          return (
            <li key={chapter.id}>
              <button
                id={`demo-${chapter.id}`}
                type="button"
                aria-current={current ? 'step' : undefined}
                onClick={() => demo.go(chapter.id as Scene)}
                className={[
                  'relative flex h-11 w-full items-center gap-2 overflow-hidden rounded-lg border px-3 text-left text-sm transition-colors',
                  current ? 'border-primary bg-accent font-medium text-accent-foreground' : 'border-border hover:bg-muted',
                ].join(' ')}
              >
                <span className="tabular text-muted-foreground">{i + 1}</span>
                <span className="truncate">{chapter.label}</span>
                {/* How far the current step has played. */}
                {current ? (
                  <span
                    aria-hidden
                    className="absolute inset-x-0 bottom-0 h-0.5 origin-left bg-primary"
                    style={{ transform: `scaleX(${progress})` }}
                  />
                ) : null}
              </button>
            </li>
          )
        })}
      </ol>
      <p className="sr-only" aria-live="polite">
        {demoCopy.announce(step + 1, demoCopy.chapters[step].label)}
      </p>
    </div>
  )
}
