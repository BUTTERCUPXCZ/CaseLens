import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useMemo, useState } from 'react'

import { caseQuery } from '@/api/queries'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { digestActions, friendlyDigestError } from '@/lib/copy'

import { withMarkers } from './withMarkers'

const MAX_PARAGRAPHS = 40 // the same limit the server enforces

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  caseId: number
  fieldLabel: string
  /** The paragraphs of the decision a student may pick from (the body, up to the end of the ruling). */
  firstAllowed: number
  lastAllowed: number
  busy: boolean
  error: unknown
  onPick: (first: number, last: number) => void
}

/** The decision, paragraph by paragraph. The student clicks the first paragraph, then the last one;
 *  the server copies the Court's exact words for that range. */
export function PassagePicker({ open, onOpenChange, caseId, fieldLabel, firstAllowed, lastAllowed, busy, error, onPick }: Props) {
  const { data: decision, error: loadError } = useQuery({ ...caseQuery(caseId), enabled: open })
  const [range, setRange] = useState<{ first: number; last: number } | null>(null)
  const [anchor, setAnchor] = useState<number | null>(null)

  const paragraphs = useMemo(() => {
    const all = decision?.full_text.split('\n') ?? []
    return all.map((text, index) => ({ index, text })).filter((p) => p.index >= firstAllowed && p.index <= lastAllowed && p.text.trim() !== '')
  }, [decision, firstAllowed, lastAllowed])

  const choose = (index: number) => {
    if (anchor === null || (range && range.first !== range.last)) {
      setAnchor(index)
      setRange({ first: index, last: index })
    } else {
      setRange({ first: Math.min(anchor, index), last: Math.max(anchor, index) })
    }
  }
  const count = range ? range.last - range.first + 1 : 0
  const tooMany = count > MAX_PARAGRAPHS

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90dvh] flex-col sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            {digestActions.pickTitle}: {fieldLabel}
          </DialogTitle>
          <DialogDescription>{digestActions.pickHelp}</DialogDescription>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border border-border">
          {!decision && !loadError ? (
            <p className="flex items-center gap-2 p-4 text-muted-foreground" role="status">
              <Loader2 className="size-4 animate-spin" aria-hidden /> Opening the decision…
            </p>
          ) : null}
          {loadError ? <p role="alert" className="p-4 text-problem">{friendlyDigestError(loadError)}</p> : null}
          <ol>
            {paragraphs.map(({ index, text }) => {
              const picked = range !== null && index >= range.first && index <= range.last
              return (
                <li key={index} className="border-b border-border last:border-b-0">
                  <button
                    type="button"
                    aria-pressed={picked}
                    onClick={() => choose(index)}
                    className={`flex w-full gap-3 px-3 py-2 text-left text-base leading-relaxed hover:bg-accent/60 focus-visible:bg-accent/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring ${picked ? 'bg-accent' : ''}`}
                  >
                    <span className="w-9 shrink-0 text-right text-sm tabular-nums text-muted-foreground" aria-label={`Paragraph ${index}`}>
                      {index}
                    </span>
                    <span>{withMarkers(text)}</span>
                  </button>
                </li>
              )
            })}
          </ol>
        </div>

        {error ? <p role="alert" className="text-sm text-problem">{friendlyDigestError(error)}</p> : null}
        {tooMany ? <p role="alert" className="text-sm text-problem">Pick at most {MAX_PARAGRAPHS} paragraphs at a time.</p> : null}

        <DialogFooter className="items-center sm:justify-between">
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {range ? (count === 1 ? `Paragraph ${range.first}` : `Paragraphs ${range.first} to ${range.last}`) : 'Nothing picked yet'}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setRange(null)
                setAnchor(null)
              }}
              disabled={!range}
            >
              {digestActions.pickClear}
            </Button>
            <Button disabled={!range || tooMany || busy} onClick={() => range && onPick(range.first, range.last)}>
              {busy ? digestActions.saving : digestActions.pickUse(count || 1)}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
