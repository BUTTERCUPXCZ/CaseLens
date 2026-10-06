import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Navigate } from '@tanstack/react-router'
import { AlertTriangle, CircleCheck, Download, KeyRound, RefreshCw, Upload } from 'lucide-react'
import { useRef, useState, type FormEvent } from 'react'

import { backupUrl } from '@/api/endpoints'
import { useRestoreBackup, useSaveAiKey, useSaveAiProvider } from '@/api/mutations'
import { desktopSettingsQuery, healthQuery } from '@/api/queries'
import type { AiProvider, DesktopSettings } from '@/api/types'
import { PageHeader } from '@/components/PageHeader'
import { ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { appUpdateQuery } from '@/features/desktop/appUpdate'
import { friendlyError, settingsCopy, updateCopy } from '@/lib/copy'
import { inDesktopWindow } from '@/lib/desktop'

export const Route = createFileRoute('/settings')({
  component: Settings,
})

/** Settings exist only in the desktop app: on the website there is nothing here to set. */
function Settings() {
  const health = useQuery(healthQuery())
  if (health.isPending) return <Skeleton className="h-40 w-full" aria-busy="true" aria-label="Loading settings" />
  if (!health.data?.desktop) return <Navigate to="/library" search={{}} replace />
  return <DesktopSettingsPage />
}

function DesktopSettingsPage() {
  const settings = useQuery(desktopSettingsQuery())
  return (
    <>
      <PageHeader title={settingsCopy.title} description={settingsCopy.description} />
      {settings.isPending ? (
        <Skeleton className="h-64 w-full" aria-busy="true" aria-label="Loading settings" />
      ) : settings.error ? (
        <ErrorState error={settings.error} onRetry={() => void settings.refetch()} />
      ) : (
        <div className="max-w-prose space-y-12">
          <AiKey settings={settings.data} />
          <Backup />
          <Restore settings={settings.data} />
          <Version settings={settings.data} />
          <section aria-labelledby="where-title">
            <h2 id="where-title" className="mb-2 text-xl font-semibold">
              {settingsCopy.whereTitle}
            </h2>
            <p className="font-mono text-sm break-all text-muted-foreground">{settings.data.data_dir}</p>
          </section>
        </div>
      )}
    </>
  )
}

/** Which AI writes (Groq, DeepSeek, OpenRouter or Gemini) and each one's key. The chosen one writes first; the others that have a key take
 *  over when it cannot answer (busy, out of allowance), so digests keep coming. */
function AiKey({ settings }: { settings: DesktopSettings }) {
  const choose = useSaveAiProvider()
  const providers = settings.providers ?? []
  return (
    <section aria-labelledby="ai-title">
      <h2 id="ai-title" className="mb-2 text-xl font-semibold">
        {settingsCopy.aiTitle}
      </h2>
      <p className="mb-4 text-base leading-relaxed">{settingsCopy.aiHelp}</p>
      <fieldset className="space-y-3">
        <legend className="sr-only">{settingsCopy.aiChoose}</legend>
        {providers.map((provider) => (
          <ProviderCard
            key={provider.id}
            provider={provider}
            chosen={settings.ai_provider === provider.id}
            onChoose={() => choose.mutate(provider.id)}
            choosing={choose.isPending}
          />
        ))}
      </fieldset>
      {choose.error ? (
        <p role="alert" className="mt-2 text-base text-problem">
          {friendlyError(choose.error)}
        </p>
      ) : null}
    </section>
  )
}

function ProviderCard({ provider, chosen, onChoose, choosing }: { provider: AiProvider; chosen: boolean; onChoose: () => void; choosing: boolean }) {
  const [key, setKey] = useState('')
  const [done, setDone] = useState<string | null>(null)
  const save = useSaveAiKey()
  const words = settingsCopy.providers[provider.id]
  const send = (value: string, message: string) =>
    save.mutate(
      { key: value, provider: provider.id },
      {
        onSuccess: () => {
          setKey('')
          setDone(message)
        },
      },
    )
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (key.trim()) send(key.trim(), settingsCopy.aiSaved)
  }
  const inputId = `ai-key-${provider.id}`
  return (
    <div className={['rounded-lg border px-4 py-4', chosen ? 'border-primary bg-accent/40' : 'border-border'].join(' ')}>
      <label className="flex cursor-pointer items-start gap-3">
        <input type="radio" name="ai-provider" className="mt-1.5 size-4 accent-primary" checked={chosen} disabled={choosing} onChange={onChoose} />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-base font-semibold">{provider.name}</span>
            {provider.id === 'groq' ? <span className="rounded-full border border-border px-2 py-0.5 text-xs font-medium">{settingsCopy.aiRecommended}</span> : null}
            {chosen ? <span className="text-sm text-muted-foreground">{settingsCopy.aiWritesFirst}</span> : null}
          </span>
          <span className="tabular block text-sm text-muted-foreground">{provider.model}</span>
          <span className="mt-1 block text-sm leading-relaxed">{words.about}</span>
        </span>
      </label>

      <p className="mt-3 flex items-center gap-2 text-sm font-medium">
        {provider.key_set ? <CircleCheck className="size-4 text-match" aria-hidden /> : <KeyRound className="size-4 text-muted-foreground" aria-hidden />}
        {provider.key_set ? settingsCopy.aiSet : settingsCopy.aiNotSet}
      </p>
      {provider.problem ? (
        <div role="alert" className="mt-3 flex gap-3 rounded-lg border border-problem/30 bg-problem-wash px-4 py-3">
          <AlertTriangle className="mt-0.5 size-5 shrink-0 text-problem" aria-hidden />
          <div>
            <p className="font-medium text-problem">{provider.problem === 'invalid' ? settingsCopy.aiInvalidTitle(provider.name) : settingsCopy.aiOutTitle(provider.name)}</p>
            <p className="mt-1 text-base leading-relaxed">{provider.problem === 'invalid' ? words.invalid : words.out}</p>
            <a href={words.billing} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block text-base underline">
              {settingsCopy.aiOutLink}
            </a>
          </div>
        </div>
      ) : null}

      <form onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
        <div className="min-w-0 flex-1 basis-64">
          <label htmlFor={inputId} className="mb-1 block text-sm font-medium">
            {settingsCopy.aiLabel(provider.name)}
          </label>
          <Input id={inputId} type="password" autoComplete="off" spellCheck={false} value={key} placeholder={words.placeholder} onChange={(event) => setKey(event.target.value)} />
        </div>
        <Button type="submit" disabled={save.isPending || !key.trim()}>
          {save.isPending ? settingsCopy.aiChecking : provider.key_set ? settingsCopy.aiReplace : settingsCopy.aiSave}
        </Button>
        {provider.key_set ? (
          <Button type="button" variant="outline" disabled={save.isPending} onClick={() => send('', settingsCopy.aiRemoved)}>
            {settingsCopy.aiRemove}
          </Button>
        ) : null}
      </form>
      <p className="mt-2 text-sm">
        <a href={words.keys} target="_blank" rel="noopener noreferrer" className="underline">
          {settingsCopy.aiGetOne(provider.name)}
        </a>
      </p>
      {save.error ? (
        <p role="alert" className="mt-2 text-base text-problem">
          {friendlyError(save.error)}
        </p>
      ) : done ? (
        <p role="status" className="mt-2 text-base">
          {done}
        </p>
      ) : null}
    </div>
  )
}

function Backup() {
  return (
    <section aria-labelledby="backup-title">
      <h2 id="backup-title" className="mb-2 text-xl font-semibold">
        {settingsCopy.backupTitle}
      </h2>
      <p className="mb-4 text-base leading-relaxed">{settingsCopy.backupHelp}</p>
      <Button asChild variant="outline">
        <a href={backupUrl} download>
          <Download data-icon="inline-start" aria-hidden />
          {settingsCopy.backupButton}
        </a>
      </Button>
    </section>
  )
}

function Restore({ settings }: { settings: DesktopSettings }) {
  const input = useRef<HTMLInputElement>(null)
  const restore = useRestoreBackup()
  return (
    <section aria-labelledby="restore-title">
      <h2 id="restore-title" className="mb-2 text-xl font-semibold">
        {settingsCopy.restoreTitle}
      </h2>
      <p className="mb-4 text-base leading-relaxed">{settingsCopy.restoreHelp}</p>
      <input
        ref={input}
        type="file"
        accept=".db"
        className="sr-only"
        aria-label={settingsCopy.restoreButton}
        tabIndex={-1}
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) restore.mutate(file)
          event.target.value = ''
        }}
      />
      <Button type="button" variant="outline" disabled={restore.isPending} onClick={() => input.current?.click()}>
        <Upload data-icon="inline-start" aria-hidden />
        {settingsCopy.restoreButton}
      </Button>
      {restore.error ? (
        <p role="alert" className="mt-2 text-base text-problem">
          {friendlyError(restore.error)}
        </p>
      ) : settings.restore_pending ? (
        <p role="status" className="mt-2 text-base font-medium">
          {settingsCopy.restoreWaiting}
        </p>
      ) : null}
    </section>
  )
}

/** The installed version, and a button to look for a newer one now (the app also looks by itself every few hours). */
function Version({ settings }: { settings: DesktopSettings }) {
  const update = useQuery(appUpdateQuery())
  const [asked, setAsked] = useState(false)
  if (!settings.app_version) return null
  return (
    <section aria-labelledby="version-title">
      <h2 id="version-title" className="mb-2 text-xl font-semibold">
        {updateCopy.versionTitle}
      </h2>
      <p className="mb-4 text-base">{updateCopy.version(settings.app_version)}</p>
      {inDesktopWindow ? (
        <Button
          type="button"
          variant="outline"
          disabled={update.isFetching}
          onClick={() => {
            setAsked(true)
            void update.refetch()
          }}
        >
          <RefreshCw data-icon="inline-start" className={update.isFetching ? 'animate-spin' : undefined} aria-hidden />
          {update.isFetching ? updateCopy.checking : updateCopy.check}
        </Button>
      ) : null}
      {asked && !update.isFetching ? (
        <p role="status" className="mt-2 text-base">
          {update.data ? updateCopy.available(update.data.version) : updateCopy.upToDate}
        </p>
      ) : null}
    </section>
  )
}
