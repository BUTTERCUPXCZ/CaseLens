import { useMutation, useQueryClient } from '@tanstack/react-query'

import {
  askDigestQuestion,
  attachLink,
  createUpload,
  deleteUpload,
  fetchCaseByUrl,
  pasteDigestField,
  pickDigestPassage,
  regenerateDigestAnswer,
  resetDigestField,
  retryUpload,
  startCatalogBuild,
  writeDigestField,
} from './endpoints'
import { keys } from './queries'
import type { Digest, Upload } from './types'

/** Put a fresh server answer straight into the cache, and refresh the lists that mention it. */
function useRememberUpload() {
  const queryClient = useQueryClient()
  return (upload: Upload) => {
    queryClient.setQueryData(keys.upload(upload.id), upload)
    void queryClient.invalidateQueries({ queryKey: keys.uploads })
  }
}

export function useUploadReviewer() {
  const remember = useRememberUpload()
  return useMutation({ mutationFn: (file: File) => createUpload(file), onSuccess: remember })
}

/** Remove a review. Its digest boxes go with it; the cases it cited stay in the library. */
export function useDeleteReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (uploadId: number) => deleteUpload(uploadId),
    onSuccess: (_, uploadId) => {
      queryClient.removeQueries({ queryKey: keys.upload(uploadId) })
      void queryClient.invalidateQueries({ queryKey: keys.uploads })
    },
  })
}

export function useRetryReview() {
  const remember = useRememberUpload()
  return useMutation({ mutationFn: (uploadId: number) => retryUpload(uploadId), onSuccess: remember })
}

export function useAttachLink(uploadId: number) {
  const remember = useRememberUpload()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { citationId: number; url: string }) =>
      attachLink(uploadId, input.citationId, input.url),
    onSuccess: (upload) => {
      remember(upload)
      void queryClient.invalidateQueries({ queryKey: ['library'] }) // a new case may have been saved
    },
  })
}

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

/** What a student can do to one digest box. Every answer is the whole updated digest, put straight into the cache. */
export function useDigestEdits(digestId: number) {
  const queryClient = useQueryClient()
  const remember = (digest: Digest) => {
    queryClient.setQueryData(keys.digest(digest.id), digest)
    void queryClient.invalidateQueries({ queryKey: ['finished-reviewer'] }) // the box's "ready" state may have changed
  }
  const options = { onSuccess: remember }
  return {
    write: useMutation({ mutationFn: (v: { key: string; text: string }) => writeDigestField(digestId, v.key, v.text), ...options }),
    paste: useMutation({ mutationFn: (v: { key: string; text: string }) => pasteDigestField(digestId, v.key, v.text), ...options }),
    pick: useMutation({
      mutationFn: (v: { key: string; first: number; last: number }) => pickDigestPassage(digestId, v.key, v.first, v.last),
      ...options,
    }),
    reset: useMutation({ mutationFn: (key: string) => resetDigestField(digestId, key), ...options }),
    ask: useMutation({ mutationFn: (question: string) => askDigestQuestion(digestId, question), ...options }),
    again: useMutation({ mutationFn: (key: string) => regenerateDigestAnswer(digestId, [key]), ...options }),
  }
}
