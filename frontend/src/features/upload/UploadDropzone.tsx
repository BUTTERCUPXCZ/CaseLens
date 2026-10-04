import { useNavigate } from '@tanstack/react-router'
import { FileUp, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { type FileRejection, useDropzone } from 'react-dropzone'

import { useUploadReviewer } from '@/api/mutations'
import { Button } from '@/components/ui/button'
import { friendlyError, upload as uploadCopy } from '@/lib/copy'

const ACCEPT = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

/** Why the browser refused a file, in the student's words. */
function rejectionMessage(rejection: FileRejection): string {
  const codes = rejection.errors.map((error) => error.code)
  if (codes.includes('file-too-large')) return uploadCopy.tooBig
  if (codes.includes('file-invalid-type')) return uploadCopy.wrongType
  if (codes.includes('too-many-files')) return 'Please choose one file at a time.'
  return uploadCopy.wrongType
}

/** The main thing to do in the app: drop a reviewer here. */
export function UploadDropzone() {
  const navigate = useNavigate()
  const send = useUploadReviewer()
  const [problem, setProblem] = useState<string | null>(null)

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    accept: ACCEPT,
    maxSize: uploadCopy.maxBytes,
    multiple: false,
    noClick: true, // the button below opens the file picker; one clear way to do it, also by keyboard
    noKeyboard: true,
    disabled: send.isPending,
    onDrop: (accepted, rejected) => {
      setProblem(null)
      if (rejected.length > 0) return setProblem(rejectionMessage(rejected[0]))
      const [file] = accepted
      if (!file) return
      send.mutate(file, {
        onSuccess: (review) =>
          void navigate({ to: '/reviews/$reviewId', params: { reviewId: String(review.id) } }),
        onError: (error) => setProblem(friendlyError(error)),
      })
    },
  })

  const busy = send.isPending

  return (
    <section aria-labelledby="drop-title">
      <div
        {...getRootProps()}
        className={[
          'flex flex-col items-center rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors',
          isDragActive ? 'border-primary bg-accent' : 'border-input bg-card',
        ].join(' ')}
      >
        <input {...getInputProps()} aria-label="Choose your reviewer file" />
        {busy ? (
          <Loader2 className="mb-4 size-10 animate-spin text-primary" aria-hidden />
        ) : (
          <FileUp className="mb-4 size-10 text-primary" aria-hidden />
        )}

        <h2 id="drop-title" className="text-xl font-semibold md:text-2xl">
          {busy ? 'Reading your file…' : isDragActive ? 'Let go to check this file' : 'Drop your reviewer here'}
        </h2>
        <p className="mt-2 max-w-md text-base text-muted-foreground">
          {busy
            ? 'This takes a few seconds.'
            : 'A PDF or Word file, up to 5 MB. We find every case you cited and compare it with the Court’s record.'}
        </p>

        {!busy ? (
          <Button size="lg" className="mt-6" onClick={open}>
            Choose a file
          </Button>
        ) : null}
      </div>

      <div aria-live="polite" className="min-h-6 pt-3">
        {problem ? (
          <p role="alert" className="text-base text-problem">
            {problem}
          </p>
        ) : null}
      </div>
    </section>
  )
}
