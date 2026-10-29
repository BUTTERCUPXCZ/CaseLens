import { ChevronDown, FileText } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { demoCopy } from '@/copy'
import { CaseHeader } from '@/demo/scenes/CaseHeader'
import { sampleCase } from '@/demo/sample'

const MENU_AT = 700
const PICK_AT = 1800
const SHEET_AT = 2500

type Level = (typeof demoCopy.download.levels)[number]['id']

/** The sections each Word file prints (backend/caselens/domain/digest_v2.py, LEVEL_SECTIONS). */
const SHEET_LINES: Record<Level, string[]> = {
  short: ['Case Summary', 'Doctrine'],
  standard: ['Doctrine', 'Facts', 'Petitioners’ arguments', 'Respondents’ arguments', 'Issue', 'Ruling'],
  full: ['Case Summary', 'Doctrine', 'Facts', 'Issue', 'Ruling', 'Ratio Decidendi', 'Dissents', 'Topic Explained'],
}

/** The digest's Download menu: three sizes of one digest. Nothing is downloaded here; the sheet shows what the Word file holds. */
export function DownloadScene({ t }: { t: number }) {
  const [picked, setPicked] = useState<Level | null>(null)
  const open = picked !== null || t >= MENU_AT
  const level: Level | null = picked ?? (t >= PICK_AT ? 'standard' : null)
  const showSheet = picked !== null || t >= SHEET_AT

  return (
    <div>
      <CaseHeader />
      <div className="mt-5 grid gap-6 @2xl:grid-cols-[minmax(0,1fr)_minmax(0,14rem)]">
        <div>
          <Button variant="outline" size="sm" aria-expanded={open} tabIndex={-1}>
            {demoCopy.download.button}
            <ChevronDown aria-hidden />
          </Button>
          {open ? (
            <ul className="replica-in mt-2 max-w-sm rounded-lg border border-border bg-popover p-1">
              {demoCopy.download.levels.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    aria-pressed={level === item.id}
                    onClick={() => setPicked(item.id)}
                    className={[
                      'flex w-full items-baseline justify-between gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors',
                      level === item.id ? 'bg-accent text-accent-foreground' : 'hover:bg-muted',
                    ].join(' ')}
                  >
                    <span className="font-medium">{item.label}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">{item.note}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        {showSheet && level ? (
          <figure key={level} className="replica-in">
            <div className="aspect-[1/1.294] w-full max-w-56 rounded-sm border border-border bg-card p-4">
              <p className="font-serif text-[0.7rem] leading-tight font-semibold">{sampleCase.name}</p>
              <p className="tabular mt-0.5 text-[0.6rem] text-muted-foreground">
                {sampleCase.number}, {sampleCase.decided}
              </p>
              <div className="mt-3 space-y-2" aria-hidden>
                {SHEET_LINES[level].map((line) => (
                  <div key={line}>
                    <p className="text-[0.6rem] font-semibold">{line}</p>
                    <div className="mt-1 h-px bg-border" />
                    <div className="mt-1 h-px w-3/4 bg-border" />
                  </div>
                ))}
              </div>
            </div>
            <figcaption className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
              <FileText className="size-3.5" aria-hidden />
              {demoCopy.download.file}
            </figcaption>
          </figure>
        ) : null}
      </div>
    </div>
  )
}
