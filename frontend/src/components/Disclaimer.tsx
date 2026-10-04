import { disclaimer } from '@/lib/copy'

/** Quiet, always findable: where the text comes from and what it is not. */
export function Disclaimer({ className = '' }: { className?: string }) {
  return (
    <p className={`text-sm leading-relaxed text-muted-foreground ${className}`}>
      {disclaimer}{' '}
      <a href="https://lawphil.net/usepolicy.html" target="_blank" rel="noopener noreferrer" className="underline">
        Lawphil's terms
      </a>
    </p>
  )
}
