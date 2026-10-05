import { createFileRoute, redirect } from '@tanstack/react-router'

/** The old "My reviews" address: the uploads now live in the Case library, under "My uploads". */
export const Route = createFileRoute('/reviews/')({
  beforeLoad: () => {
    throw redirect({ to: '/library', search: { tab: 'uploads' } })
  },
})
