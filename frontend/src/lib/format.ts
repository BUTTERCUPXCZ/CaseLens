const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

/** "2009-04-02" -> "April 2, 2009". Built from the parts, so no timezone can shift the day. */
export function formatDate(isoDate: string | null | undefined): string {
  if (!isoDate) return 'Date not shown'
  const [year, month, day] = isoDate.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return isoDate
  return `${MONTHS[month - 1]} ${day}, ${year}`
}

/** A moment in the student's own words: "Today, 5:17 PM", "Yesterday", "Oct 1". */
export function formatWhen(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return ''
  const when = new Date(iso)
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const days = Math.round((startOfDay(now) - startOfDay(when)) / 86_400_000)
  const time = when.toLocaleTimeString('en-PH', { hour: 'numeric', minute: '2-digit' })
  if (days === 0) return `Today, ${time}`
  if (days === 1) return 'Yesterday'
  if (days < 7) return when.toLocaleDateString('en-PH', { weekday: 'long' })
  return when.toLocaleDateString('en-PH', { month: 'short', day: 'numeric', year: when.getFullYear() === now.getFullYear() ? undefined : 'numeric' })
}

export const plural = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`

const SMALL_WORDS = new Set(['of', 'the', 'and', 'on', 'for', 'in', 'a', 'an', 'to', 'at', 'by', 'vs', 'v'])
const ROMAN_NUMERALS = new Set(['II', 'III', 'IV', 'VI', 'VII', 'VIII', 'IX']) // "PIMENTEL III" stays "Pimentel III"

// Short all-caps words that are acronyms, not shouted words.
const ACRONYMS = new Set(['COMELEC', 'CHED', 'PRC', 'DOJ', 'NLRC', 'GSIS', 'SSS', 'DENR', 'DAR', 'PNB', 'BIR', 'LTO', 'MWSS', 'NAPOCOR', 'ABS-CBN', 'COA', 'CSC', 'CA', 'RTC'])

/** The Court prints parties in ALL CAPS. Return it as normal capitalisation, keeping acronyms. */
export function toTitleCase(text: string): string {
  if (text !== text.toUpperCase()) return text // already mixed case: leave it
  return text
    .split(/(\s+)/)
    .map((word, index) => {
      if (/^\s+$/.test(word) || word === '') return word
      const bare = word.replace(/[^A-Za-z-]/g, '')
      if (ACRONYMS.has(bare) || ROMAN_NUMERALS.has(bare)) return word
      if (/^[^AEIOUaeiou]{2,4}$/.test(bare) && bare.length <= 4 && bare === bare.toUpperCase() && !/^(MR|MS|JR|SR|DR|ST)$/.test(bare)) {
        return word // PNB-style consonant clusters are acronyms
      }
      const lower = word.toLowerCase()
      const letters = lower.replace(/[^a-z]/g, '')
      if (letters.length === 1) return word.toUpperCase() // an initial: "A.", "V." in a justice's name
      if (index > 0 && SMALL_WORDS.has(letters)) return lower
      return lower.replace(/(^|[-.(])([a-z])/g, (_, edge: string, letter: string) => edge + letter.toUpperCase())
    })
    .join('')
}

const ABBREVIATIONS = new Set(['inc', 'co', 'corp', 'ltd', 'jr', 'sr', 'bros', 'al'])

/** Drop trailing commas and spaces, and a sentence-ending period, but keep the period of an
 *  abbreviation that belongs to the name ("Inc.", "Jr."). */
function trimEnd(text: string): string {
  let trimmed = text.replace(/[,\s]+$/, '')
  if (trimmed.endsWith('.')) {
    const lastWord = trimmed.slice(0, -1).split(/\s+/).pop()?.toLowerCase() ?? ''
    if (!ABBREVIATIONS.has(lastWord)) trimmed = trimmed.slice(0, -1).replace(/[,\s]+$/, '')
  }
  return trimmed
}

/** "REVIEW CENTER ASSOCIATION OF THE PHILIPPINES, Petitioner, vs. EXECUTIVE SECRETARY EDUARDO
 *  ERMITA and COMMISSION ON ..., Respondents. ..." -> "Review Center Association of the
 *  Philippines v. Executive Secretary Eduardo Ermita et al." The full text stays on the case page. */
export function shortCaseName(title: string | null | undefined): string {
  if (!title) return 'Untitled case'
  // A long caption lists many parties: "A, B, C, petitioners, vs. D, E, ...". Show the first on each side. A comma that
  // belongs to a name ("Marcelo, Jr.", "Acme, Inc.") does not end it.
  const lead = (side: string) => {
    const [head = '', ...others] = side.split(/(?:,|;)\s+(?!(?:Jr|Sr|Inc|Co|Corp|Ltd|II|III|IV)\b)/i)
    const [name = head, ...joined] = head.split(/\s+and\s+/) // the Court writes the joining "and" in lowercase
    return { name, more: others.length > 0 || joined.length > 0 }
  }
  // "vs" is the divider when the caption has one; a lone "V." can be a middle initial ("RADITO V. PADRIGANO").
  const parts = /\s+vs\.?\s+/i.test(title) ? title.split(/\s+vs\.?\s+/i) : title.split(/\s+v\.?\s+/i)
  if (parts.length < 2) {
    const only = lead(title.replace(/,\s*(Petitioners?|Respondents?).*$/i, '').trim())
    return `${toTitleCase(only.name)}${only.more ? ' et al.' : ''}`
  }

  const clean = (side: string) =>
    trimEnd(side.replace(/,?\s*(Petitioners?|Respondents?|Appellants?|Appellees?|Plaintiffs?|Defendants?)\b.*$/i, ''))

  const first = lead(clean(parts[0]))
  const secondFull = clean(parts.slice(1).join(' vs. '))
  const second = lead(secondFull)
  const hasMoreParties = second.more
  return `${toTitleCase(first.name)}${first.more ? ' et al.' : ''} v. ${toTitleCase(second.name)}${hasMoreParties ? ' et al.' : ''}`
}

/** "REYNATO S. PUNO" -> "Reynato S. Puno", "VELASCO, JR." -> "Velasco, Jr." */
export const justiceName = (name: string): string => toTitleCase(name)

/** "EN BANC" -> "En Banc", "SECOND DIVISION" -> "Second Division". */
export const divisionName = (division: string): string =>
  division.toLowerCase().replace(/\b[a-z]/g, (letter) => letter.toUpperCase())
