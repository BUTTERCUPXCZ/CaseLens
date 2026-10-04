import { ClipboardPaste, ListChecks, Loader2, Pencil, RotateCcw, Sparkles } from 'lucide-react'
import { useState } from 'react'

import { useDigestEdits } from '@/api/mutations'
import type { Digest, DigestField } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { digestActions, friendlyDigestError, originLabel } from '@/lib/copy'

import { PassagePicker } from './PassagePicker'
import { paragraphsOf, withMarkers } from './withMarkers'

type Mode = 'view' | 'write' | 'paste'

const CLAMP_AFTER = 700 // characters: longer Court text starts folded, with "Show more"

/** "P12" is paragraph 12 of the decision; the student's own pasted text and reviewer note are named plainly. */
function sourcesOf(field: DigestField): string | null {
  const paragraphs = field.cites.filter((c) => c.startsWith('P')).map((c) => c.slice(1))
  const extras = [field.cites.includes('S1') ? 'the text you pasted' : null, field.cites.includes('R1') ? 'your reviewer’s note' : null].filter(
    (x): x is string => x !== null,
  )
  const parts = [paragraphs.length > 0 ? digestActions.basedOn(paragraphs) : null, ...extras.map((e) => `Also based on ${e}`)].filter(Boolean)
  return parts.length > 0 ? parts.join('. ') : null
}

/** One field of a digest. A drafted explanation is a short list of points in a tinted panel so it is never mistaken
 *  for the Court's words; the Court's own text is plain reading text. */
export function DigestFieldView({ digest, field }: { digest: Digest; field: DigestField }) {
  const edits = useDigestEdits(digest.id)
  const [mode, setMode] = useState<Mode>('view')
  const [draft, setDraft] = useState('')
  const [picking, setPicking] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const verbatim = field.kind === 'verbatim'
  const drafted = field.origin === 'ai_drafted'
  const origin = originLabel[field.origin]
  const sources = sourcesOf(field)
  const canPick = verbatim && digest.pickable_first !== null && digest.pickable_last !== null
  const failure = edits.write.error ?? edits.paste.error ?? edits.pick.error ?? edits.reset.error ?? edits.again.error
  const parts = paragraphsOf(field.text)
  const long = field.text.length > CLAMP_AFTER
  const saving = edits.write.isPending || edits.paste.isPending
  const titleId = `field-${digest.id}-${field.key}`

  const open = (next: Mode) => {
    setDraft(next === 'write' ? field.text : '')
    setMode(next)
  }
  const save = () => {
    const done = { onSuccess: () => setMode('view') }
    if (mode === 'paste') edits.paste.mutate({ key: field.key, text: draft }, done)
    else edits.write.mutate({ key: field.key, text: draft }, done)
  }

  return (
    <section aria-labelledby={titleId} className="py-5 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h5 id={titleId} className="text-xl font-semibold">
          {field.label}
        </h5>
        {origin ? (
          <Badge variant={drafted ? 'secondary' : 'outline'} className="font-normal">
            {drafted ? <Sparkles aria-hidden /> : null}
            {origin}
          </Badge>
        ) : null}
      </div>

      {mode === 'view' ? (
        <>
          {field.state === 'pending' ? (
            <p role="status" className="mt-2 flex items-center gap-2 text-muted-foreground">
              <Loader2 className="size-4 animate-spin" aria-hidden /> {digestActions.stillWriting}
            </p>
          ) : null}

          {field.text ? (
            <div className={drafted ? 'mt-2 rounded-lg bg-muted/60 px-4 py-3' : 'mt-2'}>
              {drafted ? (
                <ul className="space-y-2 text-base leading-relaxed">
                  {parts.map((part, index) => (
                    <li key={index} className="ml-5 list-disc pl-1 marker:text-muted-foreground">
                      {withMarkers(part)}
                    </li>
                  ))}
                </ul>
              ) : (
                <div
                  className={`max-w-prose space-y-3 font-serif text-base leading-relaxed ${long && !expanded ? 'max-h-52 overflow-hidden [mask-image:linear-gradient(to_bottom,black_70%,transparent)]' : ''}`}
                >
                  {parts.map((part, index) => (
                    <p key={index}>{withMarkers(part)}</p>
                  ))}
                </div>
              )}
              {long && !drafted ? (
                <Button variant="link" size="sm" className="mt-1 h-auto px-0" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
                  {expanded ? digestActions.showLess : digestActions.showMore}
                  <span className="sr-only"> of {field.label}</span>
                </Button>
              ) : null}
              {sources ? <p className="mt-2 text-sm text-muted-foreground">{sources}</p> : null}
            </div>
          ) : null}

          {/* Nothing here yet: say why, and offer the one or two things that make sense. */}
          {!field.text && field.state !== 'pending' ? (
            <div className="mt-2 rounded-lg border border-dashed border-input px-4 py-3">
              {field.note ? <p className="text-base text-muted-foreground">{field.note}</p> : null}
              <div className="mt-3 flex flex-wrap gap-2">
                {canPick ? (
                  <Button size="sm" aria-label={`${digestActions.pick} for ${field.label}`} onClick={() => setPicking(true)}>
                    <ListChecks data-icon="inline-start" aria-hidden /> {digestActions.pick}
                  </Button>
                ) : null}
                {verbatim ? (
                  <Button size="sm" variant="outline" aria-label={`${digestActions.paste} for ${field.label}`} onClick={() => open('paste')}>
                    <ClipboardPaste data-icon="inline-start" aria-hidden /> {digestActions.paste}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    aria-label={`${digestActions.writeAgain}: ${field.label}`}
                    disabled={edits.again.isPending}
                    onClick={() => edits.again.mutate(field.key)}
                  >
                    <Sparkles data-icon="inline-start" aria-hidden /> {digestActions.writeAgain}
                  </Button>
                )}
                <Button size="sm" variant="outline" aria-label={`${digestActions.edit} ${field.label}`} onClick={() => open('write')}>
                  <Pencil data-icon="inline-start" aria-hidden /> {digestActions.emptyWrite}
                </Button>
              </div>
            </div>
          ) : null}

          {field.text && field.note ? <p className="mt-2 text-sm text-muted-foreground">{field.note}</p> : null}

          {field.text && field.state !== 'pending' ? (
            <div className="mt-3 flex flex-wrap gap-1 text-sm">
              {canPick ? (
                <Button size="sm" variant="ghost" aria-label={`${digestActions.pick} for ${field.label}`} onClick={() => setPicking(true)}>
                  <ListChecks data-icon="inline-start" aria-hidden /> {digestActions.pick}
                </Button>
              ) : null}
              {verbatim ? (
                <Button size="sm" variant="ghost" aria-label={`${digestActions.paste} for ${field.label}`} onClick={() => open('paste')}>
                  <ClipboardPaste data-icon="inline-start" aria-hidden /> {digestActions.paste}
                </Button>
              ) : null}
              <Button size="sm" variant="ghost" aria-label={`${digestActions.edit} ${field.label}`} onClick={() => open('write')}>
                <Pencil data-icon="inline-start" aria-hidden /> {digestActions.edit}
              </Button>
              {!verbatim ? (
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`${digestActions.writeAgain}: ${field.label}`}
                  disabled={edits.again.isPending}
                  onClick={() => edits.again.mutate(field.key)}
                >
                  <Sparkles data-icon="inline-start" aria-hidden /> {digestActions.writeAgain}
                </Button>
              ) : null}
              {field.can_reset ? (
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`${digestActions.restore}: ${field.label}`}
                  disabled={edits.reset.isPending}
                  onClick={() => edits.reset.mutate(field.key)}
                >
                  <RotateCcw data-icon="inline-start" aria-hidden /> {digestActions.restore}
                </Button>
              ) : null}
            </div>
          ) : null}
        </>
      ) : (
        <form
          className="mt-2 space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            save()
          }}
        >
          <label htmlFor={`edit-${digest.id}-${field.key}`} className="sr-only">
            {mode === 'paste' ? `Paste text into ${field.label}` : `Edit ${field.label}`}
          </label>
          <Textarea
            id={`edit-${digest.id}-${field.key}`}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={mode === 'paste' ? 'Paste the text here' : undefined}
            rows={8}
            autoFocus
          />
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={saving || (mode === 'paste' && draft.trim() === '')}>
              {saving ? digestActions.saving : digestActions.save}
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => setMode('view')}>
              {digestActions.cancel}
            </Button>
          </div>
        </form>
      )}

      {failure ? <p role="alert" className="mt-2 text-sm text-problem">{friendlyDigestError(failure)}</p> : null}

      {canPick ? (
        <PassagePicker
          open={picking}
          onOpenChange={setPicking}
          caseId={digest.case_id}
          fieldLabel={field.label}
          firstAllowed={digest.pickable_first!}
          lastAllowed={digest.pickable_last!}
          busy={edits.pick.isPending}
          error={edits.pick.error}
          onPick={(first, last) => edits.pick.mutate({ key: field.key, first, last }, { onSuccess: () => setPicking(false) })}
        />
      ) : null}
    </section>
  )
}
