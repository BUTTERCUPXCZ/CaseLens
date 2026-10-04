import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
  useRouterState,
} from '@tanstack/react-router'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'

/** Shows where the router ended up, so a test can check that something navigated. */
function Where() {
  const location = useRouterState({ select: (s) => s.location })
  return <output data-testid="location">{location.pathname + location.searchStr}</output>
}

/** Render a component inside a real router and query client, with stand-in pages for the
 *  places it may link or navigate to. */
export async function renderApp(ui: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const root = createRootRoute({
    component: () => (
      <>
        <Outlet />
        <Where />
      </>
    ),
  })
  const page = (path: string, element: ReactNode) =>
    createRoute({ getParentRoute: () => root, path, component: () => element })

  const router = createRouter({
    routeTree: root.addChildren([
      page('/', ui),
      page('/reviews/$reviewId', <p>review page</p>),
      page('/cases', <p>library page</p>),
      page('/cases/$caseId', <p>case page</p>),
      page('/search', <p>search page</p>),
    ]),
    history: createMemoryHistory({ initialEntries: ['/'] }),
  })
  await router.load()
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...view, queryClient, router }
}
