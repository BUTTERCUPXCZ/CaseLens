import { useQuery } from '@tanstack/react-query'
import { CircleCheck, FileText, FileUp, Loader2, Search, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useDropzone } from 'react-dropzone'

import { useStartBulk } from '@/api/mutations'
import { catalogSearchQuery } from '@/api/queries'
import type { CatalogItem } from '@/api/types'
import { ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { friendlyError, individualCopy, searchCopy, upload } from '@/lib/copy'
import { formatDate } from '@/lib/format'

import { SubjectTags } from './SubjectTags'
import { TopicScope } from './TopicScope'

const ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

type Picked = { title: string; text: string }

function FindOnLawphil({ picked, onPick }: { picked: Picked | null; onPick: (next: Picked) => void }) {
  const [draft, setDraft] = useState('')
  const [q, setQ] = useState('')
  const results = useQuery({ ...catalogSearchQuery(q, undefined, 0), enabled: q.length >= 2 })
  const search = (event: FormEvent) => {
    event.preventDefault()
    setQ(draft.trim())
  }
  return (
    <div className="space-y-4">
      <form onSubmit={search} role="search" aria-label={individualCopy.findTab} className="flex flex-wrap items-end gap-2">
        <div className="min-w-0 flex-1 basis-64">
          <label htmlFor="individual-search" className="mb-1 block text-sm font-medium">
            {searchCopy.boxLabel}
          </label>
          <Input id="individual-search" value={draft} placeholder={searchCopy.boxPlaceholder} onChange={(event) => setDraft(event.target.value)} />
        </div>
        <Button type="submit">
          <Search data-icon="inline-start" aria-hidden />
          Search
        </Button>
      </form>
      {q.length < 2 ? null : results.isPending ? (
        <Skeleton className="h-24 w-full" aria-busy="true" aria-label="Searching Lawphil's list" />
      ) : results.error ? (
        <ErrorState error={results.error} onRetry={() => void results.refetch()} title="The search didn't work" />
      ) : results.data.items.length === 0 ? (
        <p className="text-base text-muted-foreground">
          {searchCopy.noMatchName(q)} {searchCopy.noMatchNameHelp}
        </p>
      ) : (
        <ul className="divide-y divide-border border-y border-border" aria-label="Matching decisions">
          {results.data.items.map((item: CatalogItem) => {
            const text = `${item.gr_no}${item.decision_date ? ` (${item.decision_date.slice(0, 4)})` : ''}`
            const on = picked?.text === text
            return (
              <li key={item.source_url} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 py-3">
                <div className="min-w-0 flex-1 basis-64">
                  <p className="line-clamp-2 font-serif text-base leading-snug font-semibold">{item.title}</p>
                  <p className="tabular text-sm text-muted-foreground">
                    G.R. No. {item.gr_no} &middot; {formatDate(item.decision_date)}
                  </p>
                </div>
                <Button variant={on ? 'default' : 'outline'} aria-pressed={on} aria-label={individualCopy.chooseLabel(item.title)} onClick={() => onPick({ title: item.title, text })}>
                  {on ? <CircleCheck data-icon="inline-start" aria-hidden /> : null}
                  {on ? individualCopy.chosen : individualCopy.choose}
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function UploadOneFile({ file, onFile, disabled }: { file: File | null; onFile: (next: File | null) => void; disabled: boolean }) {
  const [problem, setProblem] = useState<string | null>(null)
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: ACCEPT,
    maxSize: upload.maxBytes,
    multiple: false,
    noClick: true,
    noKeyboard: true,
    disabled,
    onDrop: (accepted, rejected) => {
      setProblem(rejected.length > 0 ? (rejected[0]!.errors.some((e) => e.code === 'file-too-large') ? upload.tooBig : upload.wrongType) : null)
      if (accepted[0]) onFile(accepted[0])
    },
  })
  return (
    <div>
      <div
        {...getRootProps()}
        className={[
          'flex flex-col items-center rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors',
          file ? 'border-match bg-match-wash' : isDragActive ? 'border-primary bg-accent' : 'border-input bg-card',
        ].join(' ')}
      >
        <input {...getInputProps()} aria-label={individualCopy.fileLabel} />
        {file ? (
          <div className="flex items-center gap-3">
            <FileText className="size-5 text-muted-foreground" aria-hidden />
            <span className="font-serif text-base font-semibold">{file.name}</span>
            <Button type="button" variant="ghost" size="sm" onClick={() => onFile(null)} aria-label={`Remove ${file.name}`}>
              <X data-icon="inline-start" aria-hidden /> Remove
            </Button>
          </div>
        ) : (
          <>
            <FileUp className="mb-2 size-8 text-primary" aria-hidden />
            <p className="max-w-md text-base text-muted-foreground">{individualCopy.fileHelp}</p>
            <Button type="button" className="mt-4" onClick={open}>
              {individualCopy.fileButton}
            </Button>
          </>
        )}
      </div>
      {problem ? (
        <p role="alert" className="mt-2 text-base text-problem">
          {problem}
        </p>
      ) : null}
    </div>
  )
}

/** Individual (the client's sketch: "access full text & what subject?"): ONE case, found on Lawphil or uploaded, filed under the subjects
 *  the student chooses, then opened for its full text. Its digest is written in the background. */
export function IndividualForm({ onStarted }: { onStarted: (batchId: number) => void }) {
  const [how, setHow] = useState<'find' | 'file'>('find')
  const [picked, setPicked] = useState<Picked | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [tags, setTags] = useState<number[]>([])
  const [scope, setScope] = useState('')
  const [missing, setMissing] = useState(false)
  const start = useStartBulk()
  const ready = how === 'find' ? picked !== null : file !== null

  const open = () => {
    if (!ready) return setMissing(true)
    setMissing(false)
    start.mutate(
      how === 'find'
        ? { kind: 'individual', text: picked!.text, subjectIds: tags, topicScope: scope.trim(), files: [] }
        : { kind: 'individual', text: '', subjectIds: tags, topicScope: scope.trim(), files: [file!] },
      { onSuccess: (batch) => onStarted(batch.id) },
    )
  }

  return (
    <div className="space-y-8">
      <section aria-labelledby="individual-step1">
        <h2 id="individual-step1" className="mb-3 text-xl font-semibold">
          {individualCopy.step1}
        </h2>
        <Tabs value={how} onValueChange={(next) => setHow(next === 'file' ? 'file' : 'find')}>
          <TabsList className="mb-4">
            <TabsTrigger value="find" className="px-4 text-base">
              <Search aria-hidden /> {individualCopy.findTab}
            </TabsTrigger>
            <TabsTrigger value="file" className="px-4 text-base">
              <FileUp aria-hidden /> {individualCopy.fileTab}
            </TabsTrigger>
          </TabsList>
          <TabsContent value="find">
            <FindOnLawphil picked={picked} onPick={setPicked} />
          </TabsContent>
          <TabsContent value="file">
            <UploadOneFile file={file} onFile={setFile} disabled={start.isPending} />
          </TabsContent>
        </Tabs>
        {how === 'find' && picked ? (
          <p className="mt-3 text-base font-medium text-match" role="status">
            {individualCopy.picked(picked.title)}
          </p>
        ) : null}
      </section>

      <section aria-labelledby="individual-step2" className="space-y-6 rounded-xl border border-border bg-card px-5 py-5">
        <h2 id="individual-step2" className="text-xl font-semibold">
          {individualCopy.step2}
        </h2>
        <SubjectTags id="individual-tags" value={tags} onChange={setTags} disabled={start.isPending} />
        <TopicScope id="individual-scope" value={scope} onChange={setScope} disabled={start.isPending} />
      </section>

      <div>
        <Button size="lg" className="w-full" disabled={start.isPending} onClick={open}>
          {start.isPending ? <Loader2 data-icon="inline-start" className="animate-spin" aria-hidden /> : <FileText data-icon="inline-start" aria-hidden />}
          {start.isPending ? individualCopy.opening : individualCopy.open}
        </Button>
        <p className="mt-3 text-center text-sm text-muted-foreground">{individualCopy.timeNote}</p>
        <div aria-live="polite" className="min-h-6 pt-1 text-center">
          {missing ? <p role="alert" className="text-base text-problem">{individualCopy.needCase}</p> : null}
          {start.isError ? <p role="alert" className="text-base text-problem">{friendlyError(start.error)}</p> : null}
        </div>
      </div>
    </div>
  )
}
