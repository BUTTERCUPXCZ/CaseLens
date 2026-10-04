import { ExternalLink } from 'lucide-react'
import { Fragment, useMemo } from 'react'

import type { Footnote } from '@/api/types'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

import { type Block, splitMarkers, toBlocks } from './readerBlocks'

/** A footnote number in the text. It opens the footnote right there, with a link to the exact
 *  spot on Lawphil, so the student never has to scroll to the bottom and back. */
function FootnoteMarker({ number, footnote }: { number: number; footnote: Footnote | undefined }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="mx-px -mt-1 inline-flex min-w-5 cursor-pointer items-center justify-center rounded-sm bg-accent px-1 align-super font-sans text-[0.7rem] leading-5 font-semibold text-accent-foreground hover:bg-primary hover:text-primary-foreground"
          aria-label={`Footnote ${number}`}
        >
          {number}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[min(26rem,90vw)] font-sans" align="start">
        <p className="mb-1 text-sm font-semibold">Footnote {number}</p>
        <p className="text-base leading-relaxed">
          {footnote?.text ? footnote.text : 'This footnote is empty on the Court’s page.'}
        </p>
        {footnote?.source_url ? (
          <a
            href={footnote.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1.5 text-sm text-primary underline"
          >
            See this footnote on Lawphil
            <ExternalLink className="size-3.5" aria-hidden />
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        ) : null}
      </PopoverContent>
    </Popover>
  )
}

function Inline({ text, footnotes }: { text: string; footnotes: Map<number, Footnote> }) {
  return (
    <>
      {splitMarkers(text).map((piece, index) =>
        piece.kind === 'text' ? (
          <Fragment key={index}>{piece.text}</Fragment>
        ) : (
          <FootnoteMarker key={index} number={piece.number} footnote={footnotes.get(piece.number)} />
        ),
      )}
    </>
  )
}

function renderBlock(block: Block, index: number, footnotes: Map<number, Footnote>) {
  const inline = <Inline text={block.text} footnotes={footnotes} />
  switch (block.kind) {
    case 'caption':
      return <p key={index} className="text-center font-sans text-sm tracking-wide text-muted-foreground">{block.text}</p>
    case 'parties':
      return <p key={index} className="my-5 text-center text-lg leading-snug font-semibold">{block.text}</p>
    case 'title':
      return <h2 key={index} className="mt-8 mb-1 text-center text-xl font-semibold tracking-[0.3em]">{block.text}</h2>
    case 'ponente':
      return <p key={index} className="mb-6 text-center font-medium">{block.text}</p>
    case 'heading':
      return <h3 key={index} className="mt-9 mb-2 text-lg leading-snug font-semibold">{block.text}</h3>
    case 'notice':
      return <h3 key={index} className="mt-10 border-t border-border pt-4 text-center font-sans text-sm font-semibold tracking-[0.25em] text-muted-foreground">{block.text}</h3>
    case 'signature':
      return <p key={index} className="my-1 text-center font-sans text-base text-muted-foreground">{block.text}</p>
    case 'paragraph':
      return <p key={index} className="my-4">{inline}</p>
  }
}

/** The Court's own words, set for reading: a calm 68-character column in Literata, headings
 *  where the Court put them, and footnotes one click away. */
export function OfficialText({ text, footnotes }: { text: string; footnotes: Footnote[] }) {
  const blocks = useMemo(() => toBlocks(text), [text])
  const byNumber = useMemo(() => new Map(footnotes.map((footnote) => [footnote.number, footnote])), [footnotes])

  return (
    <div className="mx-auto max-w-[62ch] font-serif text-[1.0625rem] leading-[1.8] text-foreground">
      {blocks.map((block, index) => renderBlock(block, index, byNumber))}
    </div>
  )
}
