import { createFileRoute, Link } from '@tanstack/react-router'

import { PageHeader } from '@/components/PageHeader'
import { WelcomeCard } from '@/features/guide/WelcomeCard'
import { ReviewList } from '@/features/reviews/ReviewList'
import { UploadDropzone } from '@/features/upload/UploadDropzone'

export const Route = createFileRoute('/')({
  component: Home,
})

function Home() {
  return (
    <>
      <PageHeader
        title="Check a reviewer"
        description="Drop the file you wrote. We look up every case it cites and show you what matches the Supreme Court's record and what needs fixing."
      />

      <WelcomeCard />

      <UploadDropzone />

      <p className="mt-2 max-w-prose text-base text-muted-foreground">
        When a case you cited is off, we mark it the way a proofreader would, like the date in the sample reviewer:{' '}
        <del className="tabular text-redpen decoration-2">April 2, 2010</del>{' '}
        <ins className="tabular rounded-sm bg-look-wash px-1 font-semibold text-foreground no-underline">April 2, 2009</ins>.
        You wrote 2010; the Court&rsquo;s record says 2009.
      </p>

      <section aria-labelledby="recent-title" className="mt-12">
        <div className="mb-3 flex items-baseline justify-between gap-4">
          <h2 id="recent-title" className="text-lg font-semibold">
            Your recent reviews
          </h2>
          <Link to="/reviews" className="text-sm text-primary underline">
            See all
          </Link>
        </div>
        <ReviewList limit={5} emptyMessage="Nothing yet. Your checked reviewers will show up here." />
      </section>
    </>
  )
}
