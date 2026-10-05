import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Info, Loader2, MessageCircleQuestion } from 'lucide-react'
import { useEffect, useState, useSyncExternalStore } from 'react'
import { createPortal } from 'react-dom'

import { finishedReviewerDownloadUrl, reviewCasesDownloadUrl } from '@/api/endpoints'
import { finishedReviewerQuery, keys } from '@/api/queries'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { caseDownloadCopy, finishedCopy } from '@/lib/copy'
import { RIGHT_DOCK_ID } from '@/lib/dock'
import { toTitleCase } from '@/lib/format'
import { useWideScreen } from '@/hooks/useWideScreen'

import { AskAboutCase } from './AskAboutCase'
import { boxAnchor } from './anchors'
import { DigestBox } from './DigestBox'

/** A title or heading of the student's reviewer, made to stand out so the document can be scanned. */
function ReviewerHeading({ level, text }: { level: 1 | 2 | 3; text: string }) {
  if (level === 1) return <h2 className="mt-10 mb-3 max-w-3xl scroll-mt-24 text-2xl leading-snug font-semibold first:mt-0">{text}</h2>
  if (level === 2) return <h3 className="mt-8 mb-2 max-w-3xl scroll-mt-24 text-xl leading-snug font-semibold">{text}</h3>
  return <h4 className="mt-6 mb-1 max-w-3xl scroll-mt-24 text-lg leading-snug font-semibold">{text}</h4>
}

type View = 'boxes' | 'full'

/** Shown while the question panel is closed, wherever the student has scrolled to: a tab on the right edge of the window on a
 *  laptop (where the panel docks), a floating button at the bottom right on a small screen. */
function ReopenAskPanel({ onOpen }: { onOpen: () => void }) {
  return createPortal(
    <button
      type="button"
      aria-label={finishedCopy.askOpen}
      onClick={onOpen}
      className="fixed right-4 bottom-4 z-30 flex items-center gap-2 rounded-full bg-primary px-4 py-3 text-base font-medium text-primary-foreground shadow-lg hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring lg:top-1/2 lg:right-0 lg:bottom-auto lg:-translate-y-1/2 lg:flex-col lg:rounded-r-none lg:rounded-l-xl lg:px-2.5 lg:py-4"
    >
      <MessageCircleQuestion className="size-5" aria-hidden />
      <span className="lg:[writing-mode:vertical-rl]">{finishedCopy.askToggle}</span>
    </button>,
    document.body,
  )
}

/** The dock element in the page layout, once the layout has been drawn (it is not there during the very first render). */
function useDock(): HTMLElement | null {
  return useSyncExternalStore(
    () => () => undefined,
    () => document.getElementById(RIGHT_DOCK_ID),
    () => null,
  )
}

const EXCERPT_CHARS = 140

/** Where each digest sits in the student's reviewer: the nearest heading above it and the start of the citing paragraph. */
function whereBoxesSit(blocks: { text: string; heading_level?: number | null; boxes: { digest_id: number }[] }[]) {
  const where = new Map<number, { heading: string | null; excerpt: string }>()
  let heading: string | null = null
  for (const block of blocks) {
    if (block.heading_level) heading = block.text.trim()
    if (block.boxes.length === 0) continue
    const text = block.text.trim().replace(/\s+/g, ' ')
    const excerpt = text.length > EXCERPT_CHARS ? `${text.slice(0, EXCERPT_CHARS).trimEnd()}…` : text
    for (const box of block.boxes) where.set(box.digest_id, { heading: block.heading_level ? null : heading, excerpt })
  }
  return where
}

/** The student's reviewer with a digest box after each paragraph that cites a case. By default only the boxes are shown
 *  (the reviewer's full text makes a long page); a switch brings the text back. The Word download always has everything. */
export function FinishedReviewer({ uploadId, checking, initialView = 'boxes' }: { uploadId: number; checking: boolean; initialView?: View }) {
  const [view, setView] = useState<View>(initialView)
  const wide = useWideScreen()
  const [askOpen, setAskOpen] = useState(wide) // open at first on a laptop; closed on a phone, where it would push the digests down
  const dock = useDock()
  const queryClient = useQueryClient()
  const { data, error, refetch } = useQuery(finishedReviewerQuery(uploadId))

  // While we are still finding the cases, more boxes can appear: ask again until the check is done, and once more when it ends.
  useEffect(() => {
    if (checking) {
      const timer = window.setInterval(() => void queryClient.invalidateQueries({ queryKey: keys.finishedReviewer(uploadId) }), 3000)
      return () => window.clearInterval(timer)
    }
    void queryClient.invalidateQueries({ queryKey: keys.finishedReviewer(uploadId) })
    return undefined
  }, [checking, queryClient, uploadId])

  if (error) return <ErrorState error={error} onRetry={() => void refetch()} title="The finished reviewer didn't open" />
  if (!data) {
    return (
      <div aria-busy="true" aria-label="Opening your finished reviewer" className="space-y-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  const boxCount = data.blocks.reduce((n, block) => n + block.boxes.length, 0) + data.unplaced.length
  const rebuilt = data.source !== 'docx'
  const allBoxes = [...data.blocks.flatMap((block) => block.boxes), ...data.unplaced]
  const readyCount = allBoxes.filter((box) => box.ready).length
  const where = whereBoxesSit(data.blocks)

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <p className="font-semibold">{boxCount > 0 ? finishedCopy.progress(readyCount, boxCount) : finishedCopy.tabFinished}</p>
          <p className="max-w-xl text-sm text-muted-foreground">{finishedCopy.intro}</p>
          {boxCount > 0 ? <p className="mt-1 max-w-xl text-sm text-muted-foreground">{caseDownloadCopy.help}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {boxCount > 0 ? (
            <Button variant={askOpen ? 'secondary' : 'outline'} aria-pressed={askOpen} onClick={() => setAskOpen(!askOpen)}>
              <MessageCircleQuestion data-icon="inline-start" aria-hidden />
              {finishedCopy.askToggle}
            </Button>
          ) : null}
          <Button asChild variant="outline" disabled={boxCount === 0}>
            <a href={reviewCasesDownloadUrl(uploadId)} download>
              <Download data-icon="inline-start" aria-hidden />
              {caseDownloadCopy.all}
            </a>
          </Button>
          <Button asChild disabled={boxCount === 0}>
            <a href={finishedReviewerDownloadUrl(uploadId)} download>
              <Download data-icon="inline-start" aria-hidden />
              {finishedCopy.download}
            </a>
          </Button>
        </div>
      </div>
      {/* The question panel. On a laptop it is docked to the right edge of the window, full height, beside the digests (it is
          placed into the dock the page layout provides). On a small screen there is no room for a side dock, so it sits
          above the digests. */}
      {boxCount > 0 && !askOpen ? <ReopenAskPanel onOpen={() => setAskOpen(true)} /> : null}
      {boxCount > 0 && askOpen
        ? wide && dock
          ? createPortal(<AskAboutCase boxes={allBoxes} docked onClose={() => setAskOpen(false)} />, dock)
          : (
            <div className="mb-6">
              <AskAboutCase boxes={allBoxes} onClose={() => setAskOpen(false)} />
            </div>
            )
        : null}
      {boxCount > 0 ? (
        <div role="group" aria-label={finishedCopy.viewLabel} className="mb-6 flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{finishedCopy.viewLabel}:</span>
          {(['boxes', 'full'] as const).map((option) => (
            <Button key={option} size="sm" variant={view === option ? 'default' : 'outline'} aria-pressed={view === option} onClick={() => setView(option)}>
              {option === 'boxes' ? finishedCopy.viewBoxes : finishedCopy.viewFull}
            </Button>
          ))}
        </div>
      ) : null}
      {data.own_digests > 0 ? (
        <aside aria-label={finishedCopy.ownDigestsTitle} className="mb-6 flex items-start gap-3 rounded-lg bg-look-wash px-5 py-4">
          <Info className="mt-0.5 size-5 shrink-0" aria-hidden />
          <div>
            <p className="font-semibold">{finishedCopy.ownDigestsTitle}</p>
            <p className="text-base">{finishedCopy.ownDigests(data.own_digests)}</p>
          </div>
        </aside>
      ) : null}
      {rebuilt ? <p className="mb-4 text-sm text-muted-foreground">{finishedCopy.downloadPdfNote}</p> : null}

      <div aria-live="polite">
        {checking && boxCount === 0 ? (
          <p className="mb-4 flex items-center gap-2 rounded-lg bg-muted px-5 py-4 text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden /> {finishedCopy.waitingForCases}
          </p>
        ) : null}
        {!data.all_ready && boxCount > 0 ? (
          <p className="mb-4 flex items-center gap-2 rounded-lg bg-muted px-5 py-3 text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden /> {finishedCopy.writing}
          </p>
        ) : null}
      </div>

      {boxCount === 0 && !checking ? (
        <EmptyState icon={Download} title="No case boxes yet">
          {finishedCopy.noBoxes}
        </EmptyState>
      ) : (
        <div>
          {allBoxes.length > 1 ? (
            <nav aria-label={finishedCopy.jumpTitle} className="mb-6">
              <p className="mb-2 text-sm font-medium">{finishedCopy.jumpTitle}</p>
              <ul className="flex flex-wrap gap-2">
                {allBoxes.map((box) => (
                  <li key={box.digest_id}>
                    <a href={`#${boxAnchor(box.digest_id)}`} className="inline-block rounded-full border border-border px-3 py-1 text-sm hover:bg-accent">
                      {toTitleCase(box.heading.split(',')[0] ?? '').slice(0, 44)}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ) : null}
          {view === 'boxes' ? (
            <div>
              {allBoxes.map((box) => {
                const at = where.get(box.digest_id)
                return (
                  <div key={box.digest_id}>
                    <p className="mt-6 max-w-3xl text-sm text-muted-foreground">
                      {at ? finishedCopy.whereIn(at.heading, at.excerpt) : finishedCopy.whereUnplaced}
                    </p>
                    <DigestBox box={box} />
                  </div>
                )
              })}
            </div>
          ) : (
            <div>
              {data.blocks.map((block) => (
                <div key={block.index}>
                  {block.text.trim() === '' ? null : block.heading_level ? (
                    <ReviewerHeading level={block.heading_level as 1 | 2 | 3} text={block.text} />
                  ) : (
                    <p className="my-3 max-w-3xl text-base leading-relaxed">{block.text}</p>
                  )}
                  {block.boxes.map((box) => (
                    <DigestBox key={box.digest_id} box={box} />
                  ))}
                </div>
              ))}
              {data.unplaced.length > 0 ? (
                <section className="mt-8">
                  <h2 className="text-lg font-semibold">{finishedCopy.unplacedTitle}</h2>
                  <p className="text-sm text-muted-foreground">{finishedCopy.unplacedHelp}</p>
                  {data.unplaced.map((box) => (
                    <DigestBox key={box.digest_id} box={box} />
                  ))}
                </section>
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
