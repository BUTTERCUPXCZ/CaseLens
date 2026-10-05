import { CircleCheck, FileText, FileUp, Loader2, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { type FileRejection, useDropzone } from 'react-dropzone'

import { useStartBulk } from '@/api/mutations'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { bulkPageCopy, friendlyError, individualCopy, upload, uploadCopy } from '@/lib/copy'

import { SubjectTags } from './SubjectTags'
import { TopicScope } from './TopicScope'

const ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

const sizeOf = (bytes: number) => (bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`)

function rejectionMessage(rejection: FileRejection): string {
  const codes = rejection.errors.map((error) => error.code)
  return codes.includes('file-too-large') ? upload.tooBig : upload.wrongType
}

/** The client's upload screen: decision files (or G.R. numbers), Subject Tags, Topic scope, then one button. Tags and scope apply to the whole upload. */
export function UploadForm({ onStarted }: { onStarted: (batchId: number) => void }) {
  const [files, setFiles] = useState<File[]>([])
  const [numbers, setNumbers] = useState('')
  const [showNumbers, setShowNumbers] = useState(false)
  const [tags, setTags] = useState<number[]>([])
  const [scope, setScope] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [progress, setProgress] = useState<{ sent: number; total: number } | null>(null)
  const start = useStartBulk()
  const busy = start.isPending
  const nothing = files.length === 0 && numbers.trim() === ''

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: ACCEPT,
    maxSize: upload.maxBytes,
    multiple: true,
    noClick: true, // the button opens the file picker: one clear way to do it, also by keyboard
    noKeyboard: true,
    disabled: busy,
    onDrop: (accepted, rejected) => {
      setProblem(rejected.length > 0 ? `${rejected[0]!.file.name}: ${rejectionMessage(rejected[0]!)}` : null)
      setFiles((current) => [...current, ...accepted.filter((file) => !current.some((c) => c.name === file.name && c.size === file.size))])
    },
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (busy) return
    if (nothing) return setProblem(uploadCopy.nothing)
    setProblem(null)
    start.mutate(
      { kind: 'bulk', text: numbers, subjectIds: tags, topicScope: scope.trim(), files, onProgress: (sent, total) => setProgress({ sent, total }) },
      { onSuccess: (batch) => onStarted(batch.id) },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-6" aria-label={bulkPageCopy.title}>
      <div
        {...getRootProps()}
        className={[
          'flex flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
          files.length > 0 ? 'border-match bg-match-wash' : isDragActive ? 'border-primary bg-accent' : 'border-input bg-card',
        ].join(' ')}
      >
        <input {...getInputProps()} aria-label={uploadCopy.filesLabel} />
        {files.length > 0 ? <CircleCheck className="mb-3 size-10 text-match" aria-hidden /> : <FileUp className="mb-3 size-10 text-primary" aria-hidden />}
        {files.length === 0 ? (
          <>
            <h2 className="text-xl font-semibold">{uploadCopy.dropTitle}</h2>
            <p className="mt-2 max-w-md text-base text-muted-foreground">{uploadCopy.dropHelp}</p>
          </>
        ) : (
          <ul className="w-full max-w-lg space-y-2" aria-label="Files to upload">
            {files.map((file) => (
              <li key={`${file.name}-${file.size}`} className="flex items-center justify-between gap-3 rounded-lg bg-card px-3 py-2 text-left">
                <span className="flex min-w-0 items-center gap-2">
                  <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0">
                    <span className="block truncate font-serif text-base font-semibold">{file.name}</span>
                    <span className="tabular block text-sm text-muted-foreground">{sizeOf(file.size)}</span>
                  </span>
                </span>
                <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={() => setFiles(files.filter((f) => f !== file))} aria-label={uploadCopy.remove(file.name)}>
                  <X data-icon="inline-start" aria-hidden />
                  {uploadCopy.removeShort}
                </Button>
              </li>
            ))}
          </ul>
        )}
        <Button type="button" variant={files.length > 0 ? 'outline' : 'default'} className="mt-5" disabled={busy} onClick={open}>
          {uploadCopy.choose}
        </Button>
      </div>

      <div>
        {showNumbers ? (
          <div>
            <label htmlFor="upload-numbers" className="mb-1 block text-sm font-medium">
              {uploadCopy.numbersLabel}
            </label>
            <Textarea id="upload-numbers" rows={3} value={numbers} disabled={busy} onChange={(event) => setNumbers(event.target.value)} aria-describedby="upload-numbers-help" placeholder={'88211\nG.R. No. 180046'} />
            <p id="upload-numbers-help" className="mt-1 text-sm text-muted-foreground">
              {uploadCopy.numbersHelp}
            </p>
          </div>
        ) : (
          <Button type="button" variant="link" className="h-auto px-0" onClick={() => setShowNumbers(true)}>
            {uploadCopy.numbersToggle}
          </Button>
        )}
      </div>

      <section aria-labelledby="bulk-subject" className="space-y-6 rounded-xl border border-border bg-card px-5 py-5">
        <h2 id="bulk-subject" className="text-xl font-semibold">
          {individualCopy.step2.replace(/^2\. /, '')}
        </h2>
        <SubjectTags value={tags} onChange={setTags} disabled={busy} />
        <TopicScope value={scope} onChange={setScope} disabled={busy} />
      </section>

      <div>
        <Button type="submit" size="lg" className="w-full" disabled={busy}>
          {busy ? <Loader2 data-icon="inline-start" className="animate-spin" aria-hidden /> : <FileText data-icon="inline-start" aria-hidden />}
          {busy ? uploadCopy.starting : bulkPageCopy.generate}
        </Button>
        <p className="mt-3 text-center text-sm text-muted-foreground">{uploadCopy.timeNote}</p>
        <div aria-live="polite" className="min-h-6 pt-1 text-center">
          {progress && busy ? <p role="status" className="text-sm text-muted-foreground">{uploadCopy.sending(progress.sent, progress.total)}</p> : null}
          {problem ? <p role="alert" className="text-base text-problem">{problem}</p> : null}
          {start.isError ? <p role="alert" className="text-base text-problem">{progress ? uploadCopy.failedToStart : friendlyError(start.error)}</p> : null}
        </div>
      </div>
    </form>
  )
}
