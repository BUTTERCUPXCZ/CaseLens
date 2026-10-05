import { Target } from 'lucide-react'

import { Textarea } from '@/components/ui/textarea'
import { uploadCopy } from '@/lib/copy'

export const MAX_SCOPE = 300

/** Topic scope: one doctrine or issue the digest should focus on (optional). */
export function TopicScope({ value, onChange, disabled, id = 'topic-scope' }: { value: string; onChange: (next: string) => void; disabled?: boolean; id?: string }) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-semibold tracking-wide uppercase">
        {uploadCopy.scopeLabel}
      </label>
      <span className="ml-2 text-sm text-muted-foreground">{uploadCopy.scopeHint}</span>
      <div className="mt-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(uploadCopy.scopeExample)}
          aria-label={uploadCopy.scopeUseExample(uploadCopy.scopeExample)}
          className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-look bg-look-wash px-3 py-1 text-sm text-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          <Target className="size-3.5" aria-hidden />
          {uploadCopy.scopeExample}
        </button>
      </div>
      <Textarea
        id={id}
        rows={2}
        maxLength={MAX_SCOPE}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={`${id}-count`}
        className="mt-2 text-base md:text-base"
      />
      <p id={`${id}-count`} className="tabular mt-1 text-right text-sm text-muted-foreground">
        {uploadCopy.scopeCount(value.length, MAX_SCOPE)}
      </p>
    </div>
  )
}
