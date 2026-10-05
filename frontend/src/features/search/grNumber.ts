import { z } from 'zod'

/** What a student types for a G.R. number -> the form the backend accepts, or null.
 *  Accepts "180046", "G.R. No. 180046", "GR no 180046", and old-style "L-12345" / "l12345". */
export function parseGrNumber(input: string): string | null {
  const bare = input
    .trim()
    .replace(/^g\.?\s?r\.?\s*(?:nos?\.?)?\s*/i, '')
    .trim()
    .toUpperCase()
  const match = /^(?:L-?(\d{3,6})|(\d{3,7}))$/.exec(bare)
  if (!match) return null
  return match[1] ? `L-${match[1]}` : match[2]
}

export function isValidYear(text: string, now: Date = new Date()): boolean {
  if (!/^\d{4}$/.test(text)) return false
  const year = Number(text)
  return year >= 1900 && year <= now.getFullYear()
}

/** The search box: a case name or a G.R. number, and the year if the student wants to narrow it.
 *  Whether the text is a name or a number is decided by the server (it knows every format). */
export const findCaseSchema = z.object({
  q: z.string().trim().min(1, 'Type a case name or a G.R. number, for example Ermita or 180046.').max(200, 'That is too long. Try a few words.'),
  year: z
    .string()
    .trim()
    .refine((value) => value === '' || isValidYear(value), 'Use a four-digit year, for example 2009.'),
})