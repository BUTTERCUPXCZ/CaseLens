import { useNavigate } from '@tanstack/react-router'

import { useFetchByLink } from '@/api/mutations'
import { LawphilLinkForm } from '@/features/reviews/LawphilLinkForm'

/** The way out when a number can't be found by itself: the case's own Lawphil page. */
export function PasteLink() {
  const navigate = useNavigate()
  const fetchByLink = useFetchByLink()
  return (
    <div className="mt-10 border-t border-border pt-6">
      <h2 className="text-lg font-semibold">Have the Lawphil link?</h2>
      <LawphilLinkForm
        id="search-link"
        submitLabel="Open this case"
        pendingLabel="Saving the case…"
        pending={fetchByLink.isPending}
        error={fetchByLink.isError ? fetchByLink.error : null}
        onSubmit={(url) =>
          fetchByLink.mutateAsync(url, {
            onSuccess: (saved) => void navigate({ to: '/cases/$caseId', params: { caseId: String(saved.id) } }),
          })
        }
      />
    </div>
  )
}
