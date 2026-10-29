import { Moon, Sun } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { themeCopy } from '@/copy'
import { setTheme, useIsDark } from '@/lib/theme'

/** Switches the page between the light theme (the default) and the dark one. */
export function ThemeToggle({ withLabel = false }: { withLabel?: boolean }) {
  const dark = useIsDark()
  const label = dark ? themeCopy.toLight : themeCopy.toDark
  return (
    <Button
      variant={withLabel ? 'outline' : 'ghost'}
      size={withLabel ? 'default' : 'icon'}
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      aria-label={withLabel ? undefined : label}
      title={withLabel ? undefined : label}
      className={withLabel ? 'w-full' : undefined}
    >
      {dark ? <Sun aria-hidden /> : <Moon aria-hidden />}
      {withLabel ? label : null}
    </Button>
  )
}
