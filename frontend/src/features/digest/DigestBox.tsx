import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, ExternalLink, Loader2, MessageCircleQuestion } from 'lucide-react'
import { useState } from 'react'

import { useDigestEdits } from '@/api/mutations'
import { digestQuery } from '@/api/queries'
import type { BoxRef, Digest } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { digestActions, finishedCopy, friendlyDigestError } from '@/lib/copy'
import { formatDate, shortCaseName } from '@/lib/format'

import { boxAnchor } from './anchors'
import { DigestFieldView } from './DigestFieldView'

/** One digest box in the student's reviewer: the case on top, the Court's own words, then the explanations in plain words. */
export function DigestBox({ box }: { box: BoxRef }) {
  const { data: digest, error } = useQuery(digestQuery(box.digest_id))
  const [open, setOpen] = useState(true)
  const writing = digest ? digest.status === 'pending' || digest.fields.some((f) => f.state === 'pending') : false
  const court = digest?.fields.filter((f) => f.kind === 'verbatim') ?? []
  const plain = digest?.fields.filter((f) => f.kind !== 'verbatim') ?? []

  return (
    <article
      id={boxAnchor(box.digest_id)}
      aria-labelledby={`box-${box.digest_id}`}
      className="my-6 scroll-mt-24 rounded-xl border border-border bg-card shadow-xs"
    >
      <header className="flex flex-wrap items-start justify-between gap-3 px-4 py-4 md:px-6">
        <div className="min-w-0">
          <p className="text-base font-medium text-muted-foreground">{box.title}</p>
          <h3 id={`box-${box.digest_id}`} className="font-serif text-2xl font-semibold leading-snug md:text-3xl">
            {digest ? shortCaseName(digest.case_title) : box.heading}
          </h3>
          {digest ? <Record digest={digest} /> : null}
        </div>
        <div className="flex items-center gap-2">
          {digest ? (
            writing ? (
              <Badge variant="secondary" role="status">
                <Loader2 className="animate-spin" aria-hidden /> {finishedCopy.boxWriting}
              </Badge>
            ) : (
              <Badge variant="outline">{finishedCopy.boxReady}</Badge>
            )
          ) : null}
          <Button variant="ghost" size="sm" aria-expanded={open} aria-controls={`box-body-${box.digest_id}`} onClick={() => setOpen(!open)}>
            {open ? <ChevronUp data-icon="inline-start" aria-hidden /> : <ChevronDown data-icon="inline-start" aria-hidden />}
            {open ? finishedCopy.hideBox : finishedCopy.showBox}
          </Button>
        </div>
      </header>

      <div id={`box-body-${box.digest_id}`} hidden={!open}>
        {digest ? (
          <>
            <Group title={finishedCopy.groupCourt} help={finishedCopy.groupCourtHelp}>
              {court.map((field) => (
                <DigestFieldView key={field.key} digest={digest} field={field} />
              ))}
            </Group>
            <Group title={finishedCopy.groupPlain} help={finishedCopy.groupPlainHelp}>
              {plain.map((field) => (
                <DigestFieldView key={field.key} digest={digest} field={field} />
              ))}
              <AskOwnQuestion digestId={digest.id} />
            </Group>
          </>
        ) : error ? (
          <p role="alert" className="px-4 py-4 text-problem md:px-6">{friendlyDigestError(error)}</p>
        ) : (
          <div className="space-y-3 px-4 py-5 md:px-6" aria-busy="true" aria-label="Opening this digest">
            <Skeleton className="h-5 w-1/4" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}
      </div>
    </article>
  )
}

function Group({ title, help, children }: { title: string; help: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-border px-4 py-5 md:px-6">
      <h4 className="text-2xl font-semibold">{title}</h4>
      <p className="mb-5 text-base text-muted-foreground">{help}</p>
      <div className="divide-y divide-border">{children}</div>
    </div>
  )
}

function Record({ digest }: { digest: Digest }) {
  return (
    <p className="mt-1 text-sm text-muted-foreground">
      G.R. No. {digest.gr_no}
      {digest.decision_date ? ` · Decided ${formatDate(digest.decision_date)}` : ''} ·{' '}
      <a href={digest.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 underline">
        {finishedCopy.boxSource}
        <ExternalLink className="size-3.5" aria-hidden />
        <span className="sr-only">(opens in a new tab)</span>
      </a>
    </p>
  )
}

function AskOwnQuestion({ digestId }: { digestId: number }) {
  const { ask } = useDigestEdits(digestId)
  const [question, setQuestion] = useState('')
  const id = `ask-${digestId}`
  return (
    <form
      className="py-5 last:pb-0"
      onSubmit={(event) => {
        event.preventDefault()
        if (question.trim() === '') return
        ask.mutate(question.trim(), { onSuccess: () => setQuestion('') })
      }}
    >
      <label htmlFor={id} className="flex items-center gap-2 text-base font-semibold">
        <MessageCircleQuestion className="size-4" aria-hidden />
        {digestActions.askLabel}
      </label>
      <div className="mt-2 flex flex-wrap gap-2">
        <Input id={id} className="min-w-0 flex-1 basis-64" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={digestActions.askPlaceholder} maxLength={300} />
        <Button type="submit" disabled={ask.isPending || question.trim() === ''}>
          {ask.isPending ? (
            <>
              <Loader2 className="animate-spin" data-icon="inline-start" aria-hidden /> {digestActions.asking}
            </>
          ) : (
            digestActions.askButton
          )}
        </Button>
      </div>
      {ask.error ? <p role="alert" className="mt-2 text-sm text-problem">{friendlyDigestError(ask.error)}</p> : null}
    </form>
  )
}
