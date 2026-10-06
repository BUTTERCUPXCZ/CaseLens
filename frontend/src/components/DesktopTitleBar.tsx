import { getCurrentWindow } from '@tauri-apps/api/window'
import { Copy, Minus, Scale, Square, X } from 'lucide-react'
import { useEffect, useState } from 'react'

/** On a Mac the system's own window buttons sit on the left of this bar; elsewhere the bar draws its own on the right. */
const isMac = typeof navigator !== 'undefined' && /Mac/i.test(navigator.userAgent)

/** The desktop app's title bar, in the app's own colours (the menu's navy) instead of the system's grey one.
 *  Drag it to move the window; double-click it to make the window bigger or smaller again. */
export function DesktopTitleBar() {
  const [maximized, setMaximized] = useState(false)

  useEffect(() => {
    const appWindow = getCurrentWindow()
    const update = () => void appWindow.isMaximized().then(setMaximized).catch(() => undefined)
    update()
    const stop = appWindow.onResized(update)
    return () => void stop.then((unlisten) => unlisten()).catch(() => undefined)
  }, [])

  const appWindow = getCurrentWindow()
  return (
    <div
      data-tauri-drag-region
      className="fixed inset-x-0 top-0 z-60 flex h-(--titlebar-height) items-center border-b border-sidebar-border bg-sidebar text-sidebar-foreground select-none"
    >
      <div data-tauri-drag-region className={`flex items-center gap-2 ${isMac ? 'pl-20' : 'pl-4'}`}>
        <Scale className="pointer-events-none size-4 text-gilt" aria-hidden />
      </div>
      <div data-tauri-drag-region className="h-full flex-1" />
      {isMac ? null : (
        <div className="flex h-full">
          <WindowButton label="Minimize" onClick={() => void appWindow.minimize()}>
            <Minus className="size-4" aria-hidden />
          </WindowButton>
          <WindowButton label={maximized ? 'Restore down' : 'Maximize'} onClick={() => void appWindow.toggleMaximize()}>
            {maximized ? <Copy className="size-3.5 -scale-x-100" aria-hidden /> : <Square className="size-3.5" aria-hidden />}
          </WindowButton>
          <WindowButton label="Close" onClick={() => void appWindow.close()} danger>
            <X className="size-4" aria-hidden />
          </WindowButton>
        </div>
      )}
    </div>
  )
}

function WindowButton({ label, onClick, danger = false, children }: { label: string; onClick: () => void; danger?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={[
        'flex h-full w-12 items-center justify-center text-sidebar-muted transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-sidebar-ring',
        danger ? 'hover:bg-destructive hover:text-sidebar-foreground' : 'hover:bg-sidebar-accent hover:text-sidebar-foreground',
      ].join(' ')}
    >
      {children}
    </button>
  )
}
