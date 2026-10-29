import { ArrowRight, Loader2, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { demoCopy } from '@/copy'
import { sampleCase } from '@/demo/sample'

const TYPE_FROM = 300
const PER_CHAR = 170
const HIT_AT = 1600
const SUBJECT_AT = 2200
const OPEN_AT = 3000

/** The app's Individual page: the G.R. number types itself, the catalog finds the exact decision, and the case opens. */
export function FindScene({ t, onOpen }: { t: number; onOpen: () => void }) {
  const typed = sampleCase.query.slice(0, Math.max(0, Math.floor((t - TYPE_FROM) / PER_CHAR)))
  const showHit = t >= HIT_AT
  const opening = t >= OPEN_AT

  return (
    <div>
      <h3 className="text-xl font-semibold tracking-tight @2xl:text-2xl">{demoCopy.find.title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{demoCopy.find.help}</p>

      <p className="mt-5 text-sm font-medium" id="replica-field-label">
        {demoCopy.find.field}
      </p>
      <div
        role="textbox"
        aria-readonly="true"
        aria-labelledby="replica-field-label"
        className="mt-1.5 flex h-10 items-center gap-2 rounded-lg border border-input bg-card px-3 text-base"
      >
        <Search className="size-4 text-muted-foreground" aria-hidden />
        <span className="tabular">{typed}</span>
        {!showHit ? <span className="caret -ml-1.5 h-5 w-px bg-primary" aria-hidden /> : null}
      </div>

      <div className={showHit ? 'replica-in mt-3' : 'invisible mt-3'} aria-hidden={!showHit}>
        <div className="rounded-lg border border-border bg-card p-3 @2xl:p-4">
          <p className="font-serif text-base leading-snug font-semibold">{sampleCase.fullTitle}</p>
          <p className="tabular mt-1 text-sm text-muted-foreground">
            {sampleCase.number} · {sampleCase.decided} · {demoCopy.find.hitSource}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="text-sm text-muted-foreground">{demoCopy.find.subject}</span>
            <span
              className={[
                'rounded-full border px-2.5 py-0.5 text-sm transition-colors duration-300',
                t >= SUBJECT_AT ? 'border-primary bg-accent text-accent-foreground' : 'border-border text-muted-foreground',
              ].join(' ')}
            >
              {sampleCase.subject}
            </span>
          </div>
          <Button size="sm" className="mt-4" onClick={onOpen} tabIndex={showHit ? 0 : -1} data-pressed={opening || undefined}>
            {opening ? <Loader2 className="animate-spin" aria-hidden /> : null}
            {demoCopy.find.open}
            {opening ? null : <ArrowRight aria-hidden />}
          </Button>
        </div>
      </div>
    </div>
  )
}
