import { Moon, Sun } from 'lucide-react'

import { SidebarMenuButton } from '@/components/ui/sidebar'
import { setTheme, useIsDark } from '@/lib/theme'

export function ThemeToggle() {
  const dark = useIsDark()
  return (
    <SidebarMenuButton
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      size="lg" className="text-base text-sidebar-muted"
      aria-label={dark ? 'Switch to the light theme' : 'Switch to the dark theme'}
    >
      {dark ? <Sun /> : <Moon />}
      <span>{dark ? 'Light theme' : 'Dark theme'}</span>
    </SidebarMenuButton>
  )
}
