import { Link, useRouterState } from '@tanstack/react-router'
import { BookOpen, FileSearch, Layers, Library, Scale } from 'lucide-react'

import { bulkPageCopy, guideCopy, individualCopy, libraryCopy } from '@/lib/copy'
import { ThemeToggle } from '@/components/ThemeToggle'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

const NAV = [
  { to: '/individual', label: individualCopy.title, icon: FileSearch, matches: (path: string) => path.startsWith('/individual') },
  { to: '/bulk', label: bulkPageCopy.title, icon: Layers, matches: (path: string) => path.startsWith('/bulk') },
  { to: '/library', label: libraryCopy.title, icon: Library, matches: (path: string) => path === '/library' || path.startsWith('/cases') || path.startsWith('/search') || path.startsWith('/reviews') },
  { to: '/guide', label: guideCopy.navLabel, icon: BookOpen, matches: (path: string) => path.startsWith('/guide') },
] as const

export function AppSidebar() {
  const path = useRouterState({ select: (state) => state.location.pathname })

  return (
    <Sidebar>
      <SidebarHeader className="px-4 pt-5 pb-3">
        <Link to="/library" search={{}} className="flex items-center gap-2.5 rounded-md text-sidebar-foreground">
          <Scale className="size-6 text-gilt" aria-hidden />
          <span className="text-lg font-semibold tracking-tight">CaseLens</span>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <nav aria-label="Main">
              <SidebarMenu>
                {NAV.map((item) => {
                  const active = item.matches(path)
                  return (
                    <SidebarMenuItem key={item.label}>
                      <SidebarMenuButton asChild isActive={active} size="lg" className="text-base">
                        <Link to={item.to} aria-current={active ? 'page' : undefined}>
                          <item.icon className={active ? 'text-gilt' : undefined} />
                          <span>{item.label}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </nav>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="gap-3 px-3 pb-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <ThemeToggle />
          </SidebarMenuItem>
        </SidebarMenu>
        <p className="px-2 text-sm leading-snug text-sidebar-muted">
          Cases come from{' '}
          <a
            href="https://lawphil.net"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-sidebar-foreground"
          >
            Lawphil
          </a>
          , the Arellano Law Foundation's free law library.
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}
