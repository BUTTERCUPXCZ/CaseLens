import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Loader2 } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { useRequestCaseDigest, useSectionEdits } from '@/api/mutations'
import { caseDigestQuery, keys } from '@/api/queries'
import { ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { digestPageCopy } from '@/lib/copy'
import { inDesktopWindow } from '@/lib/desktop'

import { CaseDigestView } from './CaseDigestView'
import { DigestProgress } from './DigestProgress'

/** The case digest of one case for a topic scope ("" = the standard one), with its states: being written, could not be written, ready.
 *  Opening a digest nobody asked for yet asks for it (once), so opening it is all it takes. */
export function CaseDigestPanel({ caseId, scope = '', batchId = null }: { caseId: number; scope?: string; batchId?: number | null }) {
  const { data: digest, error, refetch } = useQuery(caseDigestQuery(caseId, scope, batchId))
  const request = useRequestCaseDigest(caseId, scope, batchId)
  const edits = useSectionEdits(caseId, scope, batchId ?? 0, digest?.id ?? 0)
  const asked = useRef<string | null>(null)
  const key = `${caseId}|${scope}`

  // The upload's status line stops asking once it looks finished: when this digest starts or finishes, tell it, so it never says
  // "Ready" while a digest is still being written.
  const queryClient = useQueryClient()
  const state = digest?.state
  useEffect(() => {
    if (batchId !== null && state && state !== 'none') void queryClient.invalidateQueries({ queryKey: keys.bulk(batchId) })
  }, [batchId, state, queryClient])

  useEffect(() => {
    if (digest?.state === 'none' && asked.current !== key) {
      asked.current = key
      request.mutate(false)
    }
  }, [digest?.state, key, request])

  if (error) return <ErrorState error={error} onRetry={() => void refetch()} title="The digest didn't load" />
  if (!digest) return <Skeleton className="h-96 w-full" aria-busy="true" aria-label="Opening the digest" />

  if (digest.state === 'failed') {
    return (
      <div role="alert" className="max-w-prose rounded-lg bg-problem-wash px-5 py-4 text-problem">
        <p className="font-semibold">{digestPageCopy.failedTitle}</p>
        <p className="mt-1 text-base">{digest.error}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="outline" disabled={request.isPending} onClick={() => request.mutate(true)}>
            {digestPageCopy.retry}
          </Button>
          {/* A problem with the AI key is fixed in Settings (desktop app): one click there. */}
          {inDesktopWindow && digest.error?.includes('Settings') ? (
            <Button variant="outline" asChild>
              <Link to="/settings">{digestPageCopy.openSettings}</Link>
            </Button>
          ) : null}
        </div>
      </div>
    )
  }

  if ((digest.state === 'none' || digest.state === 'pending') && digest.sections.length === 0) {
    return (
      <div role="status" className="max-w-prose">
        <h2 className="font-serif text-2xl font-semibold md:text-3xl">{digest.header.case_name}</h2>
        <p className="tabular mt-2 text-base text-muted-foreground">{digest.header.citation}</p>
        {scope ? <p className="mt-1 text-base text-muted-foreground">{digestPageCopy.topic}: {scope}</p> : null}
        {digest.stage ? (
          <DigestProgress stage={digest.stage} seconds={digest.stage_seconds ?? 0} total={digest.pending_seconds ?? 0} />
        ) : (
          <>
            {/* a digest asked for before steps were recorded */}
            <p className="mt-6 flex items-center gap-2 text-lg">
              <Loader2 className="size-5 animate-spin" aria-hidden /> {digestPageCopy.writing}
            </p>
            <p className="mt-2 text-base text-muted-foreground">{digestPageCopy.writingHelp}</p>
          </>
        )}
      </div>
    )
  }

  const editing =
    batchId !== null && digest.id !== null && digest.state === 'ready'
      ? {
          save: (section: string, text: string) => edits.save.mutateAsync({ section, text }),
          putBack: (section: string) => edits.putBack.mutateAsync(section),
          busy: edits.save.isPending || edits.putBack.isPending,
        }
      : null
  return (
    <CaseDigestView
      digest={digest}
      batchId={batchId}
      editing={editing}
      rewriting={request.isPending || digest.state === 'pending'}
      onRewrite={() => request.mutate(true)}
    />
  )
}
