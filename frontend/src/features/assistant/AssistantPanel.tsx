import { useQuery } from '@tanstack/react-query'
import { Loader2, MessageCircleQuestion, Send } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'

import { useAskAboutCase } from '@/api/mutations'
import { caseQuestionsQuery } from '@/api/queries'
import type { CaseQuestion } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { assistantCopy, friendlyError } from '@/lib/copy'

const MAX_QUESTION = 500

function Answer({ question }: { question: CaseQuestion }) {
  if (question.state === 'pending') {
    return (
      <p role="status" className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" aria-hidden /> {assistantCopy.answering}
      </p>
    )
  }
  if (question.state === 'failed') {
    return (
      <p className="mt-2 text-sm text-problem">
        <span className="font-semibold">{assistantCopy.failed}. </span>
        {question.error}
      </p>
    )
  }
  if (question.sentences.length === 0) return <p className="mt-2 text-base text-muted-foreground">{assistantCopy.noAnswer}</p>
  const paragraphs = [...new Set(question.sentences.flatMap((s) => s.cites).filter((c) => c.startsWith('P')).map((c) => c.slice(1)))]
  return (
    <div className="mt-2">
      <p className="text-base leading-relaxed">{question.sentences.map((s) => s.text).join(' ')}</p>
      {paragraphs.length > 0 ? <p className="mt-1 text-sm text-muted-foreground">{assistantCopy.sources(paragraphs.slice(0, 10))}</p> : null}
      <p className="mt-1 text-xs font-medium text-look">{assistantCopy.drafted}</p>
    </div>
  )
}

/** Ask the AI about the case being read. Each answer is written from the decision, every sentence checked; what cannot be backed is left out. */
export function AssistantPanel({ caseId, caseName, batchId }: { caseId: number | null; caseName: string | null; batchId: number | null }) {
  const [draft, setDraft] = useState('')
  const questions = useQuery({ ...caseQuestionsQuery(caseId ?? 0, batchId), enabled: caseId !== null })
  const ask = useAskAboutCase(caseId ?? 0, batchId)
  const end = useRef<HTMLLIElement>(null)
  const count = questions.data?.length ?? 0

  useEffect(() => end.current?.scrollIntoView?.({ block: 'nearest' }), [count])

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const text = draft.trim()
    if (!text || caseId === null || ask.isPending) return
    ask.mutate(text, { onSuccess: () => setDraft('') })
  }

  return (
    <section aria-label={assistantCopy.title} className="flex h-full min-h-0 flex-col">
      <header className="border-b border-border px-4 py-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <MessageCircleQuestion className="size-5 text-primary" aria-hidden />
          {assistantCopy.title}
        </h2>
        <p className="truncate text-sm text-muted-foreground">{caseName ? assistantCopy.about(caseName) : assistantCopy.noCase}</p>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        {caseId === null ? null : count === 0 ? (
          <p className="text-base text-muted-foreground">{assistantCopy.empty}</p>
        ) : (
          <ol className="space-y-5" aria-label="Questions and answers">
            {questions.data!.map((question) => (
              <li key={question.id}>
                <p className="rounded-lg bg-muted px-3 py-2 text-base font-medium">{question.question}</p>
                <Answer question={question} />
              </li>
            ))}
            <li ref={end} aria-hidden className="h-0" />
          </ol>
        )}
      </div>

      <form onSubmit={submit} className="border-t border-border px-4 py-3">
        <label htmlFor="assistant-question" className="mb-1 block text-sm font-medium">
          {assistantCopy.label}
        </label>
        <Textarea
          id="assistant-question"
          rows={3}
          maxLength={MAX_QUESTION}
          value={draft}
          disabled={caseId === null}
          placeholder={assistantCopy.placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              event.currentTarget.form?.requestSubmit()
            }
          }}
        />
        <div className="mt-2 flex items-center justify-between gap-2">
          <span className="tabular text-xs text-muted-foreground">
            {draft.length}/{MAX_QUESTION}
          </span>
          <Button type="submit" size="sm" disabled={caseId === null || draft.trim() === '' || ask.isPending}>
            {ask.isPending ? <Loader2 data-icon="inline-start" className="animate-spin" aria-hidden /> : <Send data-icon="inline-start" aria-hidden />}
            {ask.isPending ? assistantCopy.asking : assistantCopy.ask}
          </Button>
        </div>
        {ask.isError ? (
          <p role="alert" className="mt-2 text-sm text-problem">
            {friendlyError(ask.error)}
          </p>
        ) : null}
      </form>
    </section>
  )
}
