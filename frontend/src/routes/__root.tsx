import type { QueryClient } from '@tanstack/react-query'
import { createRootRouteWithContext, Link, Outlet } from '@tanstack/react-router'
import { Scale } from 'lucide-react'

import { AppSidebar } from '@/components/AppSidebar'
import { GrSearch } from '@/components/GrSearch'
import { Button } from '@/components/ui/button'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import { RIGHT_DOCK_ID } from '@/lib/dock'

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootLayout,
  notFoundComponent: NotFound,
})

function RootLayout() {
  return (
      <TooltipProvider>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
        >
          Skip to the main content
        </a>
        <SidebarProvider>
          <AppSidebar />
          <SidebarInset>
            <header className="sticky top-0 z-20 border-b bg-background/95 px-4 py-3 backdrop-blur-sm md:px-8">
              <div className="mb-2 flex items-center gap-3 md:hidden">
                <SidebarTrigger aria-label="Open the menu" />
                <Link to="/" className="flex items-center gap-2 text-lg font-semibold">
                  <Scale className="size-5 text-primary" aria-hidden />
                  CaseLens
                </Link>
              </div>
              <GrSearch />
            </header>
            <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 md:px-8 md:py-10">
              <Outlet />
            </main>
          </SidebarInset>
          {/* A panel docked to the right edge of the window, full height. A page puts its panel in here (see `RIGHT_DOCK_ID`);
              while nothing is in it, it is hidden and takes no room. */}
          <aside id={RIGHT_DOCK_ID} className="sticky top-0 hidden h-svh w-[24rem] shrink-0 border-l border-border bg-card empty:hidden xl:block" />
        </SidebarProvider>
      </TooltipProvider>
  )
}

function NotFound() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-semibold">We can't find that page</h1>
      <p className="mt-2 text-muted-foreground">The link may be old or mistyped.</p>
      <Button asChild className="mt-6">
        <Link to="/">Go to the start</Link>
      </Button>
    </div>
  )
}
