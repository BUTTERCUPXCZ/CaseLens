import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CircleCheck } from 'lucide-react'

import { aiInfoQuery } from '@/api/queries'
import { PageHeader } from '@/components/PageHeader'
import { ErrorState } from '@/components/States'
import { Skeleton } from '@/components/ui/skeleton'
import { settingsCopy } from '@/lib/copy'

/** The website's Settings: which AI writes the digests, read only (its key is set where the site is hosted, never in the app). */
export function WebSettingsPage() {
  const info = useQuery(aiInfoQuery())
  return (
    <>
      <PageHeader title={settingsCopy.title} description={settingsCopy.webDescription} />
      {info.isPending ? (
        <Skeleton className="h-32 w-full max-w-prose" aria-busy="true" aria-label="Loading settings" />
      ) : info.error ? (
        <ErrorState error={info.error} onRetry={() => void info.refetch()} />
      ) : (
        <section aria-labelledby="web-ai" className="max-w-prose rounded-lg border border-border px-5 py-4">
          <h2 id="web-ai" className="text-lg font-semibold">{settingsCopy.aiTitle}</h2>
          <p className="mt-2 flex items-center gap-2 text-base">
            {info.data.ready ? <CircleCheck className="size-4 text-match" aria-hidden /> : <AlertTriangle className="size-4 text-look" aria-hidden />}
            {settingsCopy.webAiLine(info.data.provider, info.data.model)}
          </p>
          {info.data.ready ? null : <p className="mt-2 text-base text-look">{settingsCopy.webNotReady}</p>}
          {info.data.only_chosen ? <p className="mt-2 text-sm text-muted-foreground">{settingsCopy.webOnlyChosen}</p> : null}
          {info.data.free ? <p className="mt-2 text-sm text-muted-foreground">{settingsCopy.webFree}</p> : null}
          <p className="mt-2 text-sm text-muted-foreground">{settingsCopy.webKeyNote}</p>
        </section>
      )}
    </>
  )
}
