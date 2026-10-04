import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Scale } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'

import { ApiError, postJson, request } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { accessCopy } from '@/lib/copy'

type Access = { required: boolean; granted: boolean }

/** When the owner of the app set an access code, nothing opens until it is entered. With no code set (a laptop, a test),
 *  this shows the app straight away. If the server cannot be reached, the app opens and shows its own errors. */
export function AccessGate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { data, isPending } = useQuery({
    queryKey: ['access'],
    queryFn: () => request<Access>('/access'),
    staleTime: Infinity,
    retry: false,
  })
  const [code, setCode] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (isPending) return <p className="p-8 text-muted-foreground">{accessCopy.opening}</p>
  if (!data || !data.required || data.granted) return <>{children}</>

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setProblem(null)
    try {
      await postJson<Access>('/access', { code })
      queryClient.setQueryData<Access>(['access'], { required: true, granted: true })
    } catch (error) {
      setProblem(error instanceof ApiError && error.detail ? error.detail : accessCopy.unreachable)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-svh max-w-sm flex-col justify-center gap-6 px-4">
      <div className="flex items-center gap-2 text-xl font-semibold">
        <Scale className="size-6 text-primary" aria-hidden />
        CaseLens
      </div>
      <p className="text-base text-muted-foreground">{accessCopy.intro}</p>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <Label htmlFor="access-code">{accessCopy.label}</Label>
        <Input
          id="access-code"
          type="password"
          autoComplete="off"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          aria-invalid={problem !== null}
          aria-describedby={problem ? 'access-problem' : undefined}
        />
        {problem ? (
          <p id="access-problem" role="alert" className="text-sm text-problem">
            {problem}
          </p>
        ) : null}
        <Button type="submit" disabled={busy || code.trim() === ''}>
          {accessCopy.submit}
        </Button>
      </form>
    </main>
  )
}
