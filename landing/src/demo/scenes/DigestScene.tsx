import { Check, X } from 'lucide-react'
import { useState } from 'react'

import { demoCopy } from '@/copy'
import { CaseHeader } from '@/demo/scenes/CaseHeader'
import { digest, paragraphs, sentenceOrder, type DigestSentence } from '@/demo/sample'

const PER_SENTENCE = 1200

type Pick = { section: number; sentence: number }

/** The app's case digest with its sources open: point at a sentence and the paragraph it rests on comes up beside it.
 *  While the replica plays, it walks through the sentences by itself; a visitor's own pick wins. */
export function DigestScene({ t, playing }: { t: number; playing: boolean }) {
  const [picked, setPicked] = useState<Pick | null>(null)
  const auto = sentenceOrder[Math.min(sentenceOrder.length - 1, Math.floor(t / PER_SENTENCE))]
  const active = picked ?? (playing ? auto : sentenceOrder[0])
  const activeSentence = digest[active.section].sentences[active.sentence]

  return (
    <div>
      <CaseHeader />
      <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-look-wash px-2.5 py-0.5 text-xs font-medium text-look">
        {demoCopy.digest.drafted}
      </p>
      <p className="mt-2 text-sm text-muted-foreground">{demoCopy.digest.pick}</p>

      <div className="mt-4 grid gap-6 @4xl:grid-cols-[minmax(0,1fr)_minmax(0,19rem)]">
        <div className="space-y-5">
          {digest.map((section, s) => (
            <section key={section.title} aria-labelledby={`replica-sec-${s}`}>
              <h4 id={`replica-sec-${s}`} className="text-base font-semibold">
                {section.title}
              </h4>
              <ul className="mt-1.5 space-y-1">
                {section.sentences.map((sentence, i) => {
                  const isActive = active.section === s && active.sentence === i
                  return (
                    <li key={i}>
                      <SentenceButton
                        sentence={sentence}
                        active={isActive}
                        onPick={() => setPicked({ section: s, sentence: i })}
                      />
                      {/* On a narrow screen the paragraph opens right under its sentence. */}
                      {isActive ? (
                        <div className="replica-in mt-2 mb-3 @4xl:hidden">
                          <Sources sentence={sentence} />
                        </div>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            </section>
          ))}
        </div>

        <aside aria-label={demoCopy.digest.decision} className="hidden @4xl:block">
          <div className="sticky top-0">
            <p className="text-sm font-semibold text-muted-foreground">{demoCopy.digest.decision}</p>
            <div key={`${active.section}-${active.sentence}`} className="replica-in mt-2">
              <Sources sentence={activeSentence} />
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function SentenceButton({ sentence, active, onPick }: { sentence: DigestSentence; active: boolean; onPick: () => void }) {
  const struck = Boolean(sentence.dropped)
  return (
    <button
      type="button"
      aria-pressed={active}
      onMouseEnter={onPick}
      onFocus={onPick}
      onClick={onPick}
      className={[
        'group w-full rounded-md px-2 py-1.5 text-left text-sm leading-relaxed transition-colors @2xl:text-[0.95rem]',
        active ? 'bg-accent' : 'hover:bg-muted',
      ].join(' ')}
    >
      <span className={struck ? 'text-muted-foreground line-through decoration-redpen decoration-2' : undefined}>{sentence.text}</span>{' '}
      {sentence.cites.map((id) => (
        <span
          key={id}
          className={[
            'tabular mr-1 inline-block rounded-sm border px-1 text-[0.7rem] leading-4 font-semibold align-[0.1em]',
            struck ? 'border-redpen/50 text-redpen' : 'border-primary/30 text-primary',
          ].join(' ')}
        >
          {id}
        </span>
      ))}
      {struck ? <span className="mt-0.5 block text-xs font-medium text-redpen">{sentence.dropped}</span> : null}
    </button>
  )
}

/** The paragraphs a sentence cites, in the Court's words, with the checker's verdict. */
function Sources({ sentence }: { sentence: DigestSentence }) {
  const struck = Boolean(sentence.dropped)
  return (
    <div className="space-y-3">
      {sentence.cites.map((id) => (
        <figure key={id} className="rounded-md border border-border bg-card p-3">
          <figcaption className="tabular text-xs font-semibold text-muted-foreground">{demoCopy.digest.paragraph(id)}</figcaption>
          <blockquote className={['mt-1 font-serif text-sm leading-relaxed', struck ? '' : 'source-mark'].join(' ')}>
            {paragraphs[id].text}
          </blockquote>
        </figure>
      ))}
      {struck ? (
        <p className="flex items-start gap-1.5 text-sm font-medium text-redpen">
          <X className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            {demoCopy.digest.struck}. {sentence.dropped}
          </span>
        </p>
      ) : (
        <p className="flex items-start gap-1.5 text-sm font-medium text-match">
          <Check className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            {demoCopy.digest.supported}. {demoCopy.digest.supportedBy(sentence.cites.map((id) => demoCopy.digest.paragraph(id).toLowerCase()).join(' and '))}
          </span>
        </p>
      )}
    </div>
  )
}
