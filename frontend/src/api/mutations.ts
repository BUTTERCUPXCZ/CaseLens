import { useMutation, useQueryClient } from '@tanstack/react-query'

import {
  addBulkFiles,
  askAboutCase,
  deleteBulk,
  editDigestSection,
  fetchCaseByUrl,
  putBackDigestSection,
  requestCaseDigest,
  restoreBackup,
  retryBulk,
  saveAiKey,
  setCaseSubjects,
  startBulk,
  startCatalogBuild,
} from './endpoints'
import { chunkFiles } from '@/features/bulk/chunkFiles'

import { keys } from './queries'
import type { CaseQuestion, DesktopSettings } from './types'

/** The student pastes a case's own Lawphil link and we save that case straight away. */
export function useFetchByLink() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (url: string) => fetchCaseByUrl(url),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['library'] }),
  })
}

/** Start, or carry on with, reading Lawphil's case list. */
export function useStartCatalogBuild() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: startCatalogBuild,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.catalogStatus })
      void queryClient.invalidateQueries({ queryKey: ['catalog'] })
    },
  })
}

/** File a case under a subject (null clears it). The library, its rail and the case page all show the subject, so they are asked again. */
/** The student sets a case's tags (several, or none). */
export function useSetSubjects(caseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (subjectIds: number[]) => setCaseSubjects(caseId, subjectIds),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['library'] })
      void queryClient.invalidateQueries({ queryKey: keys.subjects })
      void queryClient.invalidateQueries({ queryKey: keys.case(caseId) })
      void queryClient.invalidateQueries({ queryKey: ['case-digest', caseId] }) // the digest's Topic line follows the tags
    },
  })
}

/** Ask for the case digest (or write it again). The answer is the digest in its new "pending" state; the page then polls. */
export function useRequestCaseDigest(caseId: number, scope = '', batchId: number | null = null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (regenerate: boolean) => requestCaseDigest(caseId, regenerate, scope, batchId),
    onSuccess: (digest) => {
      queryClient.setQueryData(keys.caseDigest(caseId, scope, batchId), digest)
      void queryClient.invalidateQueries({ queryKey: ['library'] })
    },
  })
}

/** Start a bulk upload: the pasted numbers first (the batch exists from then on), then the decision files in small groups. `onProgress` says how many
 *  files have been sent; the answer is the batch, ready to watch. A group that fails stops the sending and says which file it was. */
export function useStartBulk() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: {
      text: string
      subjectIds: number[]
      topicScope: string
      files: File[]
      kind?: 'individual' | 'bulk'
      onProgress?: (sent: number, total: number) => void
    }) => {
      const batch = await startBulk(input.text, input.subjectIds, input.topicScope, input.kind ?? 'bulk')
      let sent = 0
      for (const group of chunkFiles(input.files)) {
        await addBulkFiles(batch.id, group)
        sent += group.length
        input.onProgress?.(sent, input.files.length)
      }
      return batch
    },
    onSuccess: (batch) => {
      void queryClient.invalidateQueries({ queryKey: keys.bulk(batch.id) })
      void queryClient.invalidateQueries({ queryKey: keys.recentBulk })
    },
  })
}

export function useRetryBulk(batchId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => retryBulk(batchId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.bulk(batchId) })
      void queryClient.invalidateQueries({ queryKey: ['bulk-items', batchId] })
    },
  })
}

/** Ask the AI assistant about a case, in a review. The question shows at once as being answered; the list polls until the answer is in. */
export function useAskAboutCase(caseId: number, batchId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (question: string) => askAboutCase(caseId, question, batchId),
    onSuccess: (asked) => {
      queryClient.setQueryData(keys.caseQuestions(caseId, batchId), (old: CaseQuestion[] | undefined) => [...(old ?? []), asked])
      void queryClient.invalidateQueries({ queryKey: keys.caseQuestions(caseId, batchId) })
    },
  })
}

/** Remove an upload from "My uploads" (its cases and digests stay in the library). */
export function useDeleteReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (batchId: number) => deleteBulk(batchId),
    onSuccess: (_, batchId) => {
      queryClient.removeQueries({ queryKey: keys.bulk(batchId) })
      void queryClient.invalidateQueries({ queryKey: keys.recentBulk })
    },
  })
}

/** Save the student's own text for a section (in their review), or put back the AI version. The digest is read again afterwards. */
export function useSectionEdits(caseId: number, scope: string, batchId: number, digestId: number) {
  const queryClient = useQueryClient()
  const refresh = () => queryClient.invalidateQueries({ queryKey: keys.caseDigest(caseId, scope, batchId) })
  return {
    save: useMutation({ mutationFn: ({ section, text }: { section: string; text: string }) => editDigestSection(batchId, digestId, section, text), onSuccess: refresh }),
    putBack: useMutation({ mutationFn: (section: string) => putBackDigestSection(batchId, digestId, section), onSuccess: refresh }),
  }
}

/** The desktop app's Settings: the answer is the new settings, shown at once. */
export function useSaveAiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: saveAiKey,
    onSuccess: (settings: DesktopSettings) => queryClient.setQueryData(keys.desktopSettings, settings),
  })
}

export function useRestoreBackup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: restoreBackup,
    onSuccess: (settings: DesktopSettings) => queryClient.setQueryData(keys.desktopSettings, settings),
  })
}
