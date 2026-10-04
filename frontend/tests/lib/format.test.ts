import { describe, expect, it } from 'vitest'

import { formatDate, formatWhen, justiceName, plural, shortCaseName } from '@/lib/format'

import realCase from '../fixtures/api/case-180046.json'

describe('formatDate', () => {
  it('writes a date the way a student would', () => {
    expect(formatDate('2009-04-02')).toBe('April 2, 2009')
  })

  it('does not drift a day with the timezone', () => {
    // 2009-04-02 must stay the 2nd whatever the machine's timezone is.
    expect(formatDate('2009-04-02T00:00:00')).toBe('April 2, 2009')
    expect(formatDate('2010-12-31')).toBe('December 31, 2010')
  })

  it('says so when there is no date', () => {
    expect(formatDate(null)).toBe('Date not shown')
  })
})

describe('shortCaseName', () => {
  it("turns the Court's real party block for GR 180046 into a readable name", () => {
    expect(shortCaseName(realCase.title)).toBe(
      'Review Center Association of the Philippines v. Executive Secretary Eduardo Ermita et al.',
    )
  })

  it('handles a single respondent without et al. (synthetic)', () => {
    expect(shortCaseName('ALPHA CORP, Petitioner, vs. BETA INC., Respondent.')).toBe('Alpha Corp v. Beta Inc.')
  })

  it('keeps acronyms (synthetic)', () => {
    expect(shortCaseName('PNB, Petitioner, vs. COMELEC, Respondent.')).toBe('PNB v. COMELEC')
  })

  it('leaves an already readable name alone (synthetic)', () => {
    expect(shortCaseName('Ople v. Torres')).toBe('Ople v. Torres')
  })

  it('does not fail on a missing title', () => {
    expect(shortCaseName(null)).toBe('Untitled case')
  })
})

describe('formatWhen', () => {
  const now = new Date(2026, 9, 3, 18, 0) // Oct 3, 2026, 6:00 PM local

  it('says today, yesterday, a weekday, then a date', () => {
    expect(formatWhen(new Date(2026, 9, 3, 17, 17).toISOString(), now)).toMatch(/^Today, /)
    expect(formatWhen(new Date(2026, 9, 2, 9, 0).toISOString(), now)).toBe('Yesterday')
    expect(formatWhen(new Date(2026, 9, 30, 9, 0).toISOString(), now)).not.toMatch(/Today|Yesterday/)
    expect(formatWhen(null, now)).toBe('')
  })
})

describe('plural', () => {
  it('counts', () => {
    expect(plural(1, 'case')).toBe('1 case')
    expect(plural(3, 'case')).toBe('3 cases')
  })
})

describe('justiceName', () => {
  it.each([
    ['REYNATO S. PUNO', 'Reynato S. Puno'],
    ['LEONARDO A. QUISUMBING', 'Leonardo A. Quisumbing'], // "A." is an initial, not the word "a"
    ['MINITA V. CHICO-NAZARIO', 'Minita V. Chico-Nazario'],
    ['PRESBITERO J. VELASCO, JR.', 'Presbitero J. Velasco, Jr.'],
    ['TERESITA J. LEONARDO-DE CASTRO', 'Teresita J. Leonardo-De Castro'],
    ['CARPIO', 'Carpio'],
  ])('%s -> %s (names as the real decision prints them)', (printed, expected) => {
    expect(justiceName(printed)).toBe(expected)
  })
})
