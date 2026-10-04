import { useQuery } from '@tanstack/react-query'
import { ArrowUp, Loader2, MessageCircleQuestion, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useDigestEdits } from '@/api/mutations'
import { digestQuery } from '@/api/queries'
import type { BoxRef, DigestField } from '@/api/types'
import { Button } from '@/components/ui/button'
import { digestActions, finishedCopy, friendlyDigestError } from '@/lib/copy'
import { shortCaseName } from '@/lib/format'

import { boxAnchor } from './anchors'
import { paragraphsOf, withMarkers } from './withMarkers'

/** "P12" is paragraph 12 of the decision; named plainly for the student. */
function basedOn(field: DigestField): string | null {
  const paragraphs = field.cites.filter((c) => c.startsWith('P')).map((c) => c.slice(1))
  return paragraphs.length > 0 ? digestActions.basedOn(paragraphs) : null
}

/** A chat-style side panel for the whole reviewer, like an assistant panel in a document editor: the student picks the case at
 *  the top, the conversation is in the middle (the question, then the answer in the panel itself), and the question box is
 *  pinned at the bottom. Every answer is also saved in that case's digest box, under "In plain words". */
export function AskAboutCase({ boxes, docked = false, onClose }: { boxes: BoxRef[]; docked?: boolean; onClose?: () => void }) {
  const [chosen, setChosen] = useState<number | null>(null)
  const [question, setQuestion] = useState('')
  const digestId = chosen ?? boxes[0]?.digest_id ?? 0
  const { ask } = useDigestEdits(digestId)
  const { data: digest } = useQuery({ ...digestQuery(digestId), enabled: digestId > 0 })
  const conversation = (digest?.fields ?? []).filter((field) => field.kind === 'answer' && /^q\d+$/.test(field.key))
  const log = useRef<HTMLDivElement>(null)
  const nameOf = (box: BoxRef) => shortCaseName(box.heading.split(', G.R.')[0] ?? box.heading)
  const current = boxes.find((box) => box.digest_id === digestId)

  // keep the newest message in view, like a chat
  const signature = conversation.map((f) => `${f.key}:${f.state}`).join(',')
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight
  }, [signature, digestId])

  if (boxes.length === 0) return null

  const send = (text: string) => {
    const trimmed = text.trim()
    if (trimmed === '' || ask.isPending) return
    ask.mutate(trimmed, { onSuccess: () => setQuestion('') })
  }

  return (
    <section
      aria-labelledby="ask-title"
      className={
        docked
          ? 'flex h-full flex-col bg-card' // fills the dock on the right edge of the window
          : 'flex h-[30rem] flex-col overflow-hidden rounded-xl border border-border bg-card shadow-xs' // inline, on a small screen
      }
    >
      <header className="border-b border-border px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <h2 id="ask-title" className="flex items-center gap-2 text-lg font-semibold">
            <MessageCircleQuestion className="size-5" aria-hidden />
            {finishedCopy.askTitle}
          </h2>
          {onClose ? (
            <Button type="button" variant="ghost" size="icon-sm" aria-label={finishedCopy.askClose} onClick={onClose}>
              <X aria-hidden />
            </Button>
          ) : null}
        </div>
        {boxes.length > 1 ? (
          <div className="mt-2">
            <label htmlFor="ask-case" className="sr-only">
              {finishedCopy.askWhich}
            </label>
            <select
              id="ask-case"
              value={digestId}
              onChange={(event) => setChosen(Number(event.target.value))}
              className="h-9 w-full rounded-lg border border-input bg-card px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              {boxes.map((box) => (
                <option key={box.digest_id} value={box.digest_id}>
                  {nameOf(box)}
                </option>
              ))}
            </select>
          </div>
        ) : current ? (
          <p className="mt-1 text-sm text-muted-foreground">{finishedCopy.askAbout(nameOf(current))}</p>
        ) : null}
      </header>

      <div ref={log} role="log" aria-live="polite" aria-label="Your questions and the answers" className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {conversation.length === 0 ? (
          <div>
            <p className="text-base text-muted-foreground">{finishedCopy.askEmpty}</p>
            <p className="mt-4 mb-2 text-sm font-medium">{finishedCopy.askTry}</p>
            <ul className="space-y-2">
              {finishedCopy.askSuggestions.map((text) => (
                <li key={text}>
                  <button
                    type="button"
                    onClick={() => setQuestion(text)}
                    className="w-full rounded-lg border border-border px-3 py-2 text-left text-sm hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {text}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          conversation.map((field) => (
            <div key={field.key} className="space-y-2">
              <p className="ml-8 rounded-2xl rounded-br-sm bg-muted px-3 py-2 text-base">{field.question ?? field.label}</p>
              <div className="mr-2 text-base">
                {field.state === 'pending' ? (
                  <p role="status" className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" aria-hidden /> {finishedCopy.askStateWriting}
                  </p>
                ) : field.text ? (
                  <>
                    <ul className="space-y-2 leading-relaxed">
                      {paragraphsOf(field.text).map((part, index) => (
                        <li key={index} className="ml-5 list-disc pl-1 marker:text-muted-foreground">
                          {withMarkers(part)}
                        </li>
                      ))}
                    </ul>
                    {basedOn(field) ? <p className="mt-2 text-sm text-muted-foreground">{basedOn(field)}</p> : null}
                  </>
                ) : (
                  <p className="text-muted-foreground">{field.note ?? finishedCopy.askNoAnswer}</p>
                )}
                {field.state !== 'pending' ? (
                  <a href={`#${boxAnchor(digestId)}`} className="mt-1 inline-block text-sm underline">
                    {finishedCopy.askShowInBox}
                  </a>
                ) : null}
              </div>
            </div>
          ))
        )}
      </div>

      <footer className="border-t border-border px-4 pt-3 pb-3">
        {ask.error ? <p role="alert" className="mb-2 text-sm text-problem">{friendlyDigestError(ask.error)}</p> : null}
        <form
          onSubmit={(event) => {
            event.preventDefault()
            send(question)
          }}
        >
          <label htmlFor="ask-question" className="sr-only">
            {digestActions.askLabel}
          </label>
          <div className="flex items-end gap-2 rounded-2xl border border-input bg-card px-3 py-2 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
            <textarea
              id="ask-question"
              rows={2}
              value={question}
              maxLength={300}
              placeholder={finishedCopy.askPlaceholder}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  send(question)
                }
              }}
              className="max-h-32 min-h-10 flex-1 resize-none bg-transparent text-base outline-none placeholder:text-muted-foreground md:text-sm"
            />
            <Button type="submit" size="icon" className="rounded-full" aria-label={digestActions.askButton} disabled={ask.isPending || question.trim() === ''}>
              {ask.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <ArrowUp aria-hidden />}
            </Button>
          </div>
        </form>
        <p className="mt-2 text-center text-xs text-muted-foreground">{finishedCopy.askDisclaimer}</p>
      </footer>
    </section>
  )
}
