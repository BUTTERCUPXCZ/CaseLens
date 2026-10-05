import { createFileRoute, redirect } from '@tanstack/react-router'

/** The start page is "New digest": the client's upload screen. */
export const Route = createFileRoute('/')({
  beforeLoad: () => {
    throw redirect({ to: '/upload', search: {} })
  },
})
