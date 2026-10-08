import { Download, Loader2, Pencil, RotateCcw, Undo2 } from 'lucide-react'
import { useState } from 'react'

import { caseDigestDownloadUrl } from '@/api/endpoints'
import type { CaseDigest, DigestBlock, DigestLevel } from '@/api/types'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { digestPageCopy } from '@/lib/copy'

/** "P12" is paragraph 12 of the decision; "O2.5" a separate opinion; "C1" the case record. Named plainly for the student. */
function sourcesLine(block: DigestBlock): string | null {
  const cites = block.sentences.flatMap((sentence) => sentence.cites)
  const paragraphs = [...new Set(cites.filter((c) => c.startsWith('P')).map((c) => c.slice(1)))]
  const extras = [cites.some((c) => c.startsWith('O')) ? digestPageCopy.opinionSource : null, cites.some((c) => c.startsWith('C')) ? digestPageCopy.recordSource : null].filter(
    (x): x is string => x !== null,
  )
  const parts = [paragraphs.length > 0 ? digestPageCopy.sources(paragraphs.slice(0, 12)) + (paragraphs.length > 12 ? ' and more' : '') : null, ...extras.map((e) => `Also based on ${e}`)].filter(Boolean)
  return parts.length > 0 ? parts.join('. ') : null
}

const LEVELS: { level: DigestLevel; label: string }[] = [
  { level: 'short', label: digestPageCopy.downloadShort },
  { level: 'standard', label: digestPageCopy.downloadStandard },
  { level: 'full', label: digestPageCopy.downloadFull },
]

type Section = CaseDigest['sections'][number]

/** What editing needs, in a review: save the student's text for a section, or put back the AI version. */
export type SectionEditing = {
  save: (section: string, text: string) => Promise<unknown>
  putBack: (section: string) => Promise<unknown>
  busy: boolean
}

function SectionBlocks({ section }: { section: Section }) {
  return (
    <div className="space-y-5">
      {section.blocks.map((block, index) => {
        const line = section.edited ? null : sourcesLine(block)
        return (
          <div key={index}>
            {block.heading ? <h4 className="mb-1 text-lg font-semibold">{block.heading}</h4> : null}
            {block.as_list ? (
              <ul className="max-w-prose space-y-2 text-base leading-relaxed">
                {block.sentences.map((sentence, i) => (
                  <li key={i} className={['ml-5 list-disc pl-1 marker:text-muted-foreground', sentence.key ? 'font-semibold' : ''].join(' ')}>
                    {sentence.text}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="max-w-prose text-base leading-relaxed">
                {block.sentences.map((s, i) => (
                  <span key={i} className={s.key ? 'font-semibold' : undefined}>
                    {i > 0 ? ' ' : ''}
                    {s.text}
                  </span>
                ))}
              </p>
            )}
            {line ? <p className="mt-1.5 text-sm text-muted-foreground">{line}</p> : null}
          </div>
        )
      })}
    </div>
  )
}

/** One section; in a review it can be rewritten by the student (kept in that review only) and put back. */
function SectionView({ section, editing }: { section: Section; editing: SectionEditing | null }) {
  const [draft, setDraft] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const id = `digest-${section.key}`
  const finish = (work: Promise<unknown>) =>
    work.then(
      () => (setDraft(null), setFailed(false)),
      () => setFailed(true),
    )

  return (
    <section aria-labelledby={id}>
      <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1">
        <h3 id={id} className="text-xl font-semibold">
          {section.title}
        </h3>
        {section.edited ? <span className="rounded-full bg-look-wash px-2.5 py-0.5 text-xs font-medium">{digestPageCopy.editedByYou}</span> : null}
        {editing && draft === null ? (
          <span className="ml-auto flex gap-1">
            <Button variant="ghost" size="sm" onClick={() => setDraft(section.text)} aria-label={digestPageCopy.edit(section.title)}>
              <Pencil data-icon="inline-start" aria-hidden />
              {digestPageCopy.editShort}
            </Button>
            {section.edited ? (
              <Button variant="ghost" size="sm" disabled={editing.busy} onClick={() => void finish(editing.putBack(section.key))}>
                <Undo2 data-icon="inline-start" aria-hidden />
                {digestPageCopy.putBack}
              </Button>
            ) : null}
          </span>
        ) : null}
      </div>
      {editing && draft !== null ? (
        <div className="max-w-prose">
          <label htmlFor={`${id}-edit`} className="sr-only">
            {digestPageCopy.editLabel(section.title)}
          </label>
          <Textarea id={`${id}-edit`} rows={Math.min(18, Math.max(5, draft.split('\n').length + 2))} value={draft} onChange={(event) => setDraft(event.target.value)} aria-describedby={`${id}-help`} className="text-base md:text-base" />
          <p id={`${id}-help`} className="mt-1 text-sm text-muted-foreground">
            {digestPageCopy.editHelp}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button size="sm" disabled={editing.busy} onClick={() => void finish(editing.save(section.key, draft))}>
              {editing.busy ? digestPageCopy.saving : digestPageCopy.save}
            </Button>
            <Button size="sm" variant="outline" onClick={() => (setDraft(null), setFailed(false))}>
              {digestPageCopy.cancel}
            </Button>
          </div>
        </div>
      ) : (
        <SectionBlocks section={section} />
      )}
      {failed ? (
        <p role="alert" className="mt-2 text-sm text-problem">
          {digestPageCopy.saveFailed}
        </p>
      ) : null}
    </section>
  )
}

/** The case digest in the client's format. Every part says which paragraphs it rests on, and the page says it is a draft to check.
 *  In a review (`batchId`), each section can be edited; the downloads then carry the student's text. */
export function CaseDigestView({
  digest,
  onRewrite,
  rewriting,
  batchId = null,
  editing = null,
}: {
  digest: CaseDigest
  onRewrite: () => void
  rewriting: boolean
  batchId?: number | null
  editing?: SectionEditing | null
}) {
  return (
    <article aria-label="Case digest">
      <header className="mb-6 border-b border-border pb-5">
        <p className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">Case digest</p>
        <h2 className="font-serif text-2xl leading-tight font-semibold md:text-3xl">{digest.header.case_name}</h2>
        <p className="tabular mt-2 text-base text-muted-foreground">{digest.header.citation}</p>
        <p className="mt-1 text-base text-muted-foreground">
          {[digest.header.topic ? `${digestPageCopy.topic}: ${digest.header.topic}` : null, digest.header.ponente ? `${digestPageCopy.ponente}: ${digest.header.ponente}` : null].filter(Boolean).join('  ·  ')}
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{digestPageCopy.downloadTitle}:</span>
          {LEVELS.map(({ level, label }) => (
            <Button key={level} variant={level === 'full' ? 'default' : 'outline'} size="sm" asChild>
              <a href={caseDigestDownloadUrl(digest.case_id, level, digest.scope, batchId)} download>
                <Download data-icon="inline-start" aria-hidden />
                {label}
              </a>
            </Button>
          ))}
          <Button variant="ghost" size="sm" disabled={rewriting} onClick={onRewrite}>
            <RotateCcw data-icon="inline-start" aria-hidden />
            {digestPageCopy.rewrite}
          </Button>
        </div>
        {digest.state === 'pending' ? (
          <p role="status" className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden />{' '}
            {digest.stage ? digestPageCopy.rewritingStage(digestPageCopy.stagesShort[digest.stage]) : digestPageCopy.writing}
          </p>
        ) : null}
      </header>

      {digest.sections.length === 0 ? (
        <p className="text-base text-muted-foreground">{digestPageCopy.noSections}</p>
      ) : (
        <div className="space-y-10">
          {digest.sections.map((section) => (
            <SectionView key={section.key} section={section} editing={editing} />
          ))}
        </div>
      )}

      <footer className="mt-12 max-w-prose border-t border-border pt-4 text-sm text-muted-foreground">
        <p>{digestPageCopy.draftNote}</p>
        {digest.dropped > 0 ? <p className="mt-1">{digestPageCopy.leftOut(digest.dropped)}</p> : null}
      </footer>
    </article>
  )
}
