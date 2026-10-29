import { Menu, Monitor, Scale } from 'lucide-react'
import { useState } from 'react'

import { ThemeToggle } from '@/components/ThemeToggle'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { heroCopy, navLinks, siteCopy, type ChapterId } from '@/copy'
import { appLink, DESKTOP_URL } from '@/lib/links'

/** The one navigation of the page, set in the hero panel between its rails: the wordmark on the left, every part of the page
 *  in the middle, the way into the app on the right. On a phone the parts open from the menu button. */
export function Navbar({ current }: { current: ChapterId }) {
  const [open, setOpen] = useState(false)

  return (
    <header className="relative z-10 grid h-16 grid-cols-[1fr_auto] items-center gap-2 px-2 sm:gap-4 sm:px-4 lg:grid-cols-[1fr_auto_1fr]">
      <a href="#title" aria-label={siteCopy.home} className="flex w-fit items-center gap-2 rounded-md">
        <Scale className="size-5 text-primary" aria-hidden />
        <span className="text-base font-semibold tracking-tight">{siteCopy.name}</span>
      </a>

      <nav aria-label={siteCopy.navLabel} className="hidden lg:block">
        <ul className="flex items-center gap-1">
          {navLinks.map((link) => (
            <li key={link.id}>
              <a
                href={`#${link.id}`}
                aria-current={link.id === current ? 'location' : undefined}
                className="rounded-md px-3 py-2 text-sm text-foreground/80 transition-colors hover:bg-background/70 hover:text-foreground aria-[current=location]:text-foreground"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex items-center justify-end gap-2">
        <a
          href={DESKTOP_URL}
          className="hidden items-center gap-1.5 rounded-md px-2.5 py-2 text-sm whitespace-nowrap text-foreground/80 transition-colors hover:text-foreground xl:inline-flex"
        >
          <Monitor className="size-4" aria-hidden />
          {heroCopy.desktopShort}
        </a>
        <ThemeToggle />
        <Button asChild size="sm" variant="outline" className="hidden bg-card sm:inline-flex">
          <a href={appLink('/individual')}>{siteCopy.openApp}</a>
        </Button>

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label={siteCopy.menu} className="lg:hidden">
              <Menu aria-hidden />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-80 max-w-[85vw]">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <Scale className="size-5 text-primary" aria-hidden />
                {siteCopy.name}
              </SheetTitle>
              <SheetDescription className="sr-only">{siteCopy.menuTitle}</SheetDescription>
            </SheetHeader>
            <nav aria-label={siteCopy.navLabel} className="px-4">
              <ul className="border-t border-border">
                {navLinks.map((link) => (
                  <li key={link.id} className="border-b border-border">
                    <a
                      href={`#${link.id}`}
                      onClick={() => setOpen(false)}
                      aria-current={link.id === current ? 'location' : undefined}
                      className="flex items-baseline gap-3 py-3.5 text-base aria-[current=location]:font-semibold"
                    >
                      <span className="w-6 font-serif text-sm text-primary/70" aria-hidden>
                        {link.numeral}
                      </span>
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
            <div className="mt-6 space-y-2 px-4">
              <Button asChild className="w-full">
                <a href={appLink('/individual')}>{siteCopy.openApp}</a>
              </Button>
              <ThemeToggle withLabel />
              <Button asChild variant="outline" className="w-full">
                <a href={DESKTOP_URL}>
                  <Monitor aria-hidden />
                  {heroCopy.desktop}
                </a>
              </Button>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  )
}
