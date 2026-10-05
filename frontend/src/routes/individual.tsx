import { createFileRoute, useNavigate } from '@tanstack/react-router'

import { PageHeader } from '@/components/PageHeader'
import { WelcomeCard } from '@/features/guide/WelcomeCard'
import { IndividualForm } from '@/features/upload/IndividualForm'
import { individualCopy } from '@/lib/copy'

export const Route = createFileRoute('/individual')({ component: IndividualPage })

/** Individual: one case, its full text, and what subject it is (the first line of the client's sketch). */
function IndividualPage() {
  const navigate = useNavigate()
  return (
    <>
      <PageHeader title={individualCopy.title} description={individualCopy.description} />
      <WelcomeCard />
      <div className="max-w-3xl">
        <IndividualForm onStarted={(batchId) => void navigate({ to: '/reviews/$batchId', params: { batchId: String(batchId) } })} />
      </div>
    </>
  )
}
