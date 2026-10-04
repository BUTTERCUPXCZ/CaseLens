import { createFileRoute, Link } from '@tanstack/react-router'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { ReviewList } from '@/features/reviews/ReviewList'

export const Route = createFileRoute('/reviews/')({
  component: Reviews,
})

function Reviews() {
  return (
    <>
      <PageHeader
        title="My reviews"
        description="Every reviewer you've checked, newest first."
        actions={
          <Button asChild>
            <Link to="/">Check another</Link>
          </Button>
        }
      />
      <ReviewList limit={50} emptyMessage="Nothing yet. Drop a reviewer on the start page and it will appear here." />
    </>
  )
}
