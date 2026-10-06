import { invoke } from '@tauri-apps/api/core'
import { queryOptions } from '@tanstack/react-query'

import { inDesktopWindow } from '@/lib/desktop'

/** A newer CaseLens, as the desktop app's updater found it (signed by CaseLens; see desktop/src-tauri/src/updates.rs). */
export type AppUpdate = { version: string; notes: string | null }

const SIX_HOURS = 6 * 60 * 60 * 1000

/** Asked when the app opens and every six hours; the Settings button asks again. Offline or failing: no update, no error shown. */
export const appUpdateQuery = () =>
  queryOptions({
    queryKey: ['app-update'],
    queryFn: async () => (await invoke<AppUpdate | null>('check_update').catch(() => null)) ?? null,
    enabled: inDesktopWindow,
    staleTime: SIX_HOURS,
    refetchInterval: SIX_HOURS,
    retry: false,
  })

export const installAppUpdate = () => invoke<void>('install_update')
