import { createFileRoute, redirect } from '@tanstack/react-router'
import { z } from 'zod'

const searchSchema = z.object({ tab: z.enum(['upload', 'search']).optional().catch(undefined) })

/** The old "New digest" address: its two tabs are now the Individual and Bulk pages. */
export const Route = createFileRoute('/upload')({
  validateSearch: searchSchema,
  beforeLoad: ({ search }) => {
    throw redirect({ to: search.tab === 'search' ? '/individual' : '/bulk' })
  },
})
