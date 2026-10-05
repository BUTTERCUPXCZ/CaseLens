import { createFileRoute, redirect } from '@tanstack/react-router'

/** The start page is Individual: the first line of the client's sketch. */
export const Route = createFileRoute('/')({
  beforeLoad: () => {
    throw redirect({ to: '/individual' })
  },
})
