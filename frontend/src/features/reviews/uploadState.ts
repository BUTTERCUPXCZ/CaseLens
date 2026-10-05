import { CircleAlert, CircleCheck, Loader2, type LucideIcon } from 'lucide-react'

import type { Bulk } from '@/api/types'
import { reviewsCopy } from '@/lib/copy'

export type UploadState = { label: string; tone: 'working' | 'ready' | 'problem'; icon: LucideIcon; busy: boolean }

/** How an upload is doing, in words a student understands, with an icon and a colour. */
export function uploadState(bulk: Bulk): UploadState {
  const c = bulk.counts
  const notAdded = c.not_found + c.unreadable + c.failed
  if (!bulk.finished) return { label: reviewsCopy.stateGetting, tone: 'working', icon: Loader2, busy: true }
  if (c.digests_pending > 0) return { label: reviewsCopy.stateWriting(c.digests_ready, c.found), tone: 'working', icon: Loader2, busy: true }
  if (c.found === 0) return { label: reviewsCopy.stateNothing, tone: 'problem', icon: CircleAlert, busy: false }
  if (notAdded > 0) return { label: `${reviewsCopy.stateReady} · ${reviewsCopy.stateNotAdded(notAdded)}`, tone: 'problem', icon: CircleAlert, busy: false }
  return { label: reviewsCopy.stateReady, tone: 'ready', icon: CircleCheck, busy: false }
}

export const TONE_CLASS: Record<UploadState['tone'], string> = { working: 'text-muted-foreground', ready: 'text-match', problem: 'text-look' }
