import { createFileRoute, useNavigate } from '@tanstack/react-router'

import { PageHeader } from '@/components/PageHeader'
import { UploadForm } from '@/features/upload/UploadForm'
import { bulkPageCopy } from '@/lib/copy'

export const Route = createFileRoute('/bulk')({ component: BulkPage })

/** Bulk: many cases at once, and what subject they are (the second line of the client's sketch). */
function BulkPage() {
  const navigate = useNavigate()
  return (
    <>
      <PageHeader title={bulkPageCopy.title} description={bulkPageCopy.description} />
      <div className="max-w-3xl">
        <UploadForm onStarted={(batchId) => void navigate({ to: '/reviews/$batchId', params: { batchId: String(batchId) } })} />
      </div>
    </>
  )
}
