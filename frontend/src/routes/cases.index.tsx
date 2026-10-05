import { createFileRoute, redirect } from '@tanstack/react-router'
import { z } from 'zod'

const searchSchema = z.object({
  q: z.string().optional().catch(undefined),
  page: z.coerce.number().int().min(0).optional().catch(undefined),
})

/** The old address of the library: kept so old links and bookmarks still work. */
export const Route = createFileRoute('/cases/')({
  validateSearch: searchSchema,
  beforeLoad: ({ search }) => {
    throw redirect({ to: '/library', search: { q: search.q, page: search.page } })
  },
})
