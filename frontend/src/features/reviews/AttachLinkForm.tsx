import { useAttachLink } from '@/api/mutations'

import { LawphilLinkForm } from './LawphilLinkForm'

/** For a cited case we couldn't find by itself: the student pastes the case's own Lawphil link.
 *  On success the review refreshes and this citation's card shows how it checked out. */
export function AttachLinkForm({ uploadId, citationId }: { uploadId: number; citationId: number }) {
  const attach = useAttachLink(uploadId)
  return (
    <LawphilLinkForm
      id={`link-${citationId}`}
      submitLabel="Check this case"
      pendingLabel="Checking…"
      pending={attach.isPending}
      error={attach.isError ? attach.error : null}
      onSubmit={(url) => attach.mutateAsync({ citationId, url })}
    />
  )
}
