import { describe, expect, it } from 'vitest'

import { splitMarkers, toBlocks } from '@/features/cases/readerBlocks'
import { statuteLabel } from '@/features/cases/statutes'

import realCase from '../fixtures/api/case-180046.json'

describe('toBlocks on the real text of GR 180046', () => {
  const blocks = toBlocks(realCase.full_text)
  const kinds = (kind: string) => blocks.filter((b) => b.kind === kind).map((b) => b.text)

  it('keeps every line: nothing is dropped or reworded', () => {
    const nonEmpty = realCase.full_text.split('\n').filter((line) => line.trim() !== '')
    expect(blocks).toHaveLength(nonEmpty.length)
    // Every block's text is the original line, except the two spaced titles which are closed up.
    const plain = blocks.filter((b) => b.kind !== 'title' && b.kind !== 'notice').map((b) => b.text)
    const originals = nonEmpty.filter((l) => !/^(?:[A-Z] ){3,}[A-Z]$/.test(l))
    expect(plain).toEqual(originals)
  })

  it('finds the caption, parties, title and ponente at the top', () => {
    expect(blocks.slice(0, 6).map((b) => b.kind)).toEqual(['caption', 'caption', 'caption', 'parties', 'title', 'ponente'])
    expect(blocks[4].text).toBe('DECISION')
    expect(blocks[5].text).toBe('CARPIO, J.:')
  })

  it('recognises exactly the section headings the Court printed (read from the real text)', () => {
    expect(kinds('heading')).toEqual([
      'The Case',
      'The Antecedent Facts',
      'The Assailed Executive Order and the RIRR',
      'EXECUTIVE ORDER NO. 566',
      'Rule VII',
      'IMPLEMENTING GUIDELINES AND PROCEDURES',
      'Rule XIV TRANSITORY PROVISIONS',
      'The Issues',
      'The Ruling of this Court',
      'Violation of Judicial Hierarchy',
      'OSG\u2019s Technical Objections',
      'EO 566 Expands the Coverage of RA 7722',
      'Usurpation of Legislative Power',
      'Exercise of Police Power',
      'Republic Act No. 8981 is Not the Appropriate Law',
    ])
  })

  it('does not mistake sentences, introductions or signatures for headings', () => {
    const headings = kinds('heading')
    for (const notHeading of ['We do not agree.', 'Executive Order No. 566 states in full:', 'By the President:', '(Sgd.) Gloria Macapagal-Arroyo', 'x x x']) {
      expect(headings).not.toContain(notHeading)
    }
    expect(headings.some((h) => /Associate Justice|Chief Justice/.test(h))).toBe(false)
  })

  it('sets the 13 concurring justices, the Chief Justice and the ponente signature as signatures', () => {
    const signatures = kinds('signature')
    expect(signatures).toContain('WE CONCUR:')
    expect(signatures).toContain('LEONARDO A. QUISUMBING Associate Justice')
    expect(signatures.filter((s) => /Justice/.test(s)).length).toBeGreaterThanOrEqual(14)
  })

  it('marks the certification apart from the decision', () => {
    expect(kinds('notice')).toContain('CERTIFICATION')
  })
})

describe('splitMarkers', () => {
  it('turns footnote markers into positions in the text, in order', () => {
    expect(splitMarkers('assailing EO 566[^1] and the RIRR.[^2] Next')).toEqual([
      { kind: 'text', text: 'assailing EO 566' },
      { kind: 'marker', number: 1 },
      { kind: 'text', text: ' and the RIRR.' },
      { kind: 'marker', number: 2 },
      { kind: 'text', text: ' Next' },
    ])
  })

  it('finds every one of the 42 real markers and no others', () => {
    const numbers = realCase.full_text
      .split('\n')
      .flatMap((line) => splitMarkers(line).filter((p) => p.kind === 'marker'))
      .map((p) => (p as { number: number }).number)
    expect(new Set(numbers)).toEqual(new Set(realCase.footnotes.map((f) => f.number)))
  })

  it('leaves text without markers alone', () => {
    expect(splitMarkers('plain')).toEqual([{ kind: 'text', text: 'plain' }])
  })
})

describe('statuteLabel', () => {
  it('reads the way a student writes it', () => {
    expect(statuteLabel('RA', '7722')).toBe('Republic Act No. 7722')
    expect(statuteLabel('EO', '566')).toBe('Executive Order No. 566')
    expect(statuteLabel('CONST', 'Art. VI, Sec. 1')).toBe('Constitution, Art. VI, Sec. 1')
    expect(statuteLabel('BP', '129')).toBe('Batas Pambansa Blg. 129')
  })
})
