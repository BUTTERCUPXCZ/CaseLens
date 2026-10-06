import './zod-setup'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { AccessGate } from './components/AccessGate'
import { inDesktopWindow } from './lib/desktop'
import { routeTree } from './routeTree.gen'
import './index.css'

// After a new version is deployed, a tab that was opened before it asks for files that no longer exist. Load the new
// version once instead of leaving a blank page (the flag stops a reload loop if the files are really missing).
window.addEventListener('vite:preloadError', () => {
  try {
    if (window.sessionStorage.getItem('caselens:reloaded') === '1') return
    window.sessionStorage.setItem('caselens:reloaded', '1')
  } catch {
    return
  }
  window.location.reload()
})

// The desktop app has no system title bar: ours takes the top strip of the window (see index.css).
if (inDesktopWindow) document.documentElement.classList.add('has-titlebar')

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // A failed lookup should show an error the student can act on, not retry silently for ages.
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: 'intent',
  scrollRestoration: true,
  scrollToTopSelectors: ['#root'], // the desktop app scrolls this, not the window (index.css)
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
  interface HistoryState {
    fromCase?: number // set when the student opens a case's decision or digest from its page: "Back to the case" then steps back
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AccessGate>
        <RouterProvider router={router} />
      </AccessGate>
    </QueryClientProvider>
  </StrictMode>,
)
