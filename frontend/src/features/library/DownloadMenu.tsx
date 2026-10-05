import { ChevronDown, Download } from 'lucide-react'

import { caseDigestDownloadUrl } from '@/api/endpoints'
import type { DigestLevel } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { libraryCopy } from '@/lib/copy'

const OPTIONS: { level: DigestLevel; label: string; hint: string | null }[] = [
  { level: 'short', label: libraryCopy.optionShort, hint: null },
  { level: 'standard', label: libraryCopy.optionStandard, hint: libraryCopy.optionStandardHint },
  { level: 'full', label: libraryCopy.optionFull, hint: libraryCopy.optionFullHint },
]

/** The "Download options" of the drawing: Facts and Doctrine; Doctrine, Facts, Issue, Ruling (1 to 2 pages); the full case digest (about 6 pages).
 *  A digest is written the first time it is opened, so until then the options point there instead of at a file that does not exist. */
export function DownloadMenu({ caseId, caseName, digestReady, onNeedDigest }: { caseId: number; caseName: string; digestReady: boolean; onNeedDigest: () => void }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" aria-label={`${libraryCopy.download}: ${caseName}`}>
          <Download data-icon="inline-start" aria-hidden />
          {libraryCopy.download}
          <ChevronDown data-icon="inline-end" aria-hidden />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-2">
        {digestReady ? (
          <ul>
            {OPTIONS.map((option) => (
              <li key={option.level}>
                <a
                  href={caseDigestDownloadUrl(caseId, option.level)}
                  download
                  className="block rounded-md px-3 py-2 hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="block text-base font-medium">{option.label}</span>
                  {option.hint ? <span className="block text-sm text-muted-foreground">{option.hint}</span> : null}
                </a>
              </li>
            ))}
            <li>
              <a href={`/api/cases/${caseId}/document.docx`} download className="block rounded-md px-3 py-2 hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring">
                <span className="block text-base font-medium">{libraryCopy.optionFullText}</span>
                <span className="block text-sm text-muted-foreground">{libraryCopy.optionFullTextHint}</span>
              </a>
            </li>
          </ul>
        ) : (
          <div className="space-y-2 px-2 py-1">
            <p className="text-sm text-muted-foreground">{libraryCopy.menuNeedsDigest}</p>
            <Button size="sm" onClick={onNeedDigest}>
              {libraryCopy.caseDigest}
            </Button>
            <a href={`/api/cases/${caseId}/document.docx`} download className="block text-sm underline">
              {libraryCopy.optionFullText} ({libraryCopy.optionFullTextHint})
            </a>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
