/** Every student-facing sentence about a result lives here, so the wording stays consistent and
 *  can be reviewed in one place. Rules: plain words (no "parse", "pending", "mismatch", "API"),
 *  law terms students already use stay (G.R. No., ponente, En Banc), and every problem says what
 *  to do next. */
import { ApiError } from '@/api/client'
import type { CitationStatus, Disposition, Mismatch } from '@/api/types'

export type Tone = 'match' | 'look' | 'notfound' | 'problem' | 'checking'

export const citationStatus: Record<CitationStatus, { label: string; tone: Tone }> = {
  match: { label: "Matches the Court's record", tone: 'match' },
  mismatch: { label: 'Needs a look', tone: 'look' },
  not_found: { label: "Couldn't find this case", tone: 'notfound' },
  error: { label: "Couldn't check right now", tone: 'problem' },
  pending: { label: 'Checking…', tone: 'checking' },
}

export const dispositionLabel: Record<Disposition, string> = {
  GRANTED: 'Petition granted',
  DENIED: 'Petition denied',
  PARTIALLY_GRANTED: 'Petition partly granted',
  DISMISSED: 'Petition dismissed',
  AFFIRMED: 'Decision affirmed',
  REVERSED: 'Decision reversed',
  UNKNOWN: 'Read the ruling below',
}

/** What the backend calls a field -> what the student calls it. */
export const fieldLabel: Record<string, string> = {
  year: 'Year decided',
  date: 'Date decided',
  title: 'Case name',
  gr_no: 'G.R. number',
}

export const fieldName = (field: string): string => fieldLabel[field] ?? field

/** "You wrote 2010. The Court's record says 2009." */
export function describeMismatch(mismatch: Mismatch): string {
  return `You wrote ${mismatch.claimed ?? 'nothing'}. The Court's record says ${mismatch.official ?? 'nothing'}.`
}

export const reporterNote =
  "We can't check the page reference (for example 538 SCRA 428): Lawphil doesn't include it."

/** Why a not-found or failed citation happened, in the student's terms. The backend's own
 *  message is technical, so the common cases are rewritten and the rest shown as given. */
export function explainCitation(status: CitationStatus, message: string | null): string | null {
  if (status === 'not_found') {
    if (message?.includes('no year was given')) {
      return "You didn't write the year, and we need it to look the case up. Add the year, or paste the case's Lawphil link."
    }
    return "We couldn't find this case on Lawphil near the year you wrote. Check the number and year, or paste the case's Lawphil link."
  }
  if (status === 'error') {
    return "Lawphil didn't answer, or the page couldn't be read. Nothing is wrong with your file. Try again in a minute."
  }
  return null
}

export const summarizeReview = {
  empty: 'No citations were found in this file.',
  checking: (done: number, total: number) => `Checking ${done} of ${total} cases…`,
}

export const upload = {
  maxBytes: 10 * 1024 * 1024,
  tooBig: 'That file is larger than 10 MB. Try a smaller one.',
  wrongType: 'We can read PDF and Word (.docx) files. Please choose one of those.',
}

/** A failed request -> something a student can act on. */
export function friendlyError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Something went wrong. Please try again.'
  const detail = error.detail ?? ''
  switch (error.status) {
    case 0:
      return "We can't reach CaseLens right now. Check your connection and try again."
    case 400:
      return detail.includes('official Lawphil')
        ? "That doesn't look like a Lawphil case link. It should start with https://lawphil.net/judjuris/ and end in .html"
        : 'That request was not valid. Please check it and try again.'
    case 404:
      return "We couldn't find that. It may have been removed."
    case 413:
      return upload.tooBig
    case 415:
      return upload.wrongType
    case 422:
      if (detail.includes('no extractable text')) {
        return "This PDF looks like a scan, so we can't read its text. Try a PDF saved from Word or Google Docs."
      }
      if (detail.includes('Not a valid G.R.')) {
        return "That G.R. number doesn't look right. Use digits only, for example 180046."
      }
      return "We couldn't read that file. Try saving it again as a PDF or Word file."
    case 502:
      return "Lawphil isn't responding right now. Please try again in a minute."
    case 503:
      return "We can't do that right now (a background service isn't reachable). Please try again in a moment."
    default:
      return 'Something went wrong on our side. Please try again in a moment.'
  }
}

/** Errors from changing a digest. The backend's 422 sentences ("Pick paragraphs 6 to 132 of the decision.") are
 *  already written for students, so they are shown as they are; everything else uses the general wording. */
export function friendlyDigestError(error: unknown): string {
  if (error instanceof ApiError && error.status === 422 && error.detail) return error.detail
  return friendlyError(error)
}

export const disclaimer =
  "Informational only, not legal advice. Lawphil gives no warranty of accuracy or completeness: confirm with the originating body (the Supreme Court)."

/** The search over Lawphil's own list of decisions. "Lawphil's case list" is what a student calls it;
 *  there is no talk of catalogs, indexes or crawling. */
export const searchCopy = {
  boxLabel: 'Find a case by name or G.R. number',
  boxPlaceholder: 'e.g. Ermita, or 180046',
  yearLabel: 'Year',
  yearPlaceholder: 'optional',
  needSomething: 'Type a case name or a G.R. number, for example Ermita or 180046.',
  results: (total: number, shown: string) =>
    total === 1 ? `1 decision on Lawphil's list matches ${shown}.` : `${total.toLocaleString('en-PH')} decisions on Lawphil's list match ${shown}.`,
  openAction: 'Open this case',
  opening: 'Opening…',
  inLibrary: 'In your library',
  readAction: 'Read the case',
  openHint: 'Opening saves the case to your library. The first time takes a few seconds.',
  alsoDecidedWith: (numbers: string[]) => `Decided together with G.R. No. ${numbers.join(', ')}`,
  noExactNumber: (typed: string) =>
    `No decision numbered ${typed} is on Lawphil's list. These numbers start the same way:`,
  noMatchName: (typed: string) => `No decision on Lawphil's list matches "${typed}".`,
  noMatchNameHelp:
    "Try fewer words, or just a surname. Lawphil's list spells out names, so write 'Commission on Elections' rather than 'Comelec'.",
  noMatchNumber: (typed: string) => `G.R. No. ${typed} isn't on Lawphil's list.`,
  noMatchNumberHelp:
    "Lawphil's list starts in 1987, so an older case won't be found by number alone. If you know the year it was decided, we can look for it directly (about a minute). Or paste the case's own Lawphil link.",
  lookUpWithYear: 'Look it up with the year',
  notReadyEmpty: "Lawphil's case list isn't ready yet, so searches can't find anything for now.",
}

/** How far the one-time read of Lawphil's list has got (shown only until it is done). */
export const listProgress = {
  buildingTitle: "Getting Lawphil's case list ready",
  buildingText: (read: number, known: number, percent: number) =>
    known > 0
      ? `${read.toLocaleString('en-PH')} of ${known.toLocaleString('en-PH')} months read (${percent}%). You can already search the newest cases; older ones appear as it goes.`
      : 'Starting… this is a one-time step that takes about 9 minutes.',
  partialTitle: "Lawphil's case list is only partly read",
  partialText: (percent: number) => `It stopped at ${percent}%, so older cases may be missing from search results.`,
  continueAction: 'Carry on reading',
  continuing: 'Starting…',
  emptyTitle: "Lawphil's case list hasn't been read yet",
}

/** The finished reviewer: the student's own text with a digest box after each case it cites. */
export const finishedCopy = {
  tabCheck: 'Check results',
  tabFinished: 'Finished reviewer',
  intro:
    'One digest box for each case your reviewer cites. The Facts, Issue, Ruling and Doctrine are the Court’s own words. Change anything you like. The Word file has your whole reviewer with the boxes inside.',
  download: 'Download as Word',
  downloadPdfNote: 'Your PDF is rebuilt as a Word file: the text is the same, but the fonts and layout differ.',
  waitingForCases: 'We are still finding your cases. The boxes appear here as they are found.',
  noBoxes: 'No case boxes yet. They appear for each case we find in your reviewer.',
  writing: 'Some explanations are still being written. They appear here by themselves.',
  unplacedTitle: 'Cases we could not place next to their paragraph',
  unplacedHelp: 'These cases are cited somewhere we could not read as a paragraph (a table, for example).',
  boxSource: 'Court’s record on Lawphil',
  groupCourt: 'From the Court',
  groupCourtHelp: 'The Court’s own words. Nothing here is reworded.',
  groupPlain: 'In plain words',
  groupPlainHelp: 'Written from the decision for you to check and change.',
  hideBox: 'Hide this digest',
  showBox: 'Show this digest',
  jumpTitle: 'Cases in your reviewer',
  progress: (ready: number, total: number) =>
    ready === total
      ? total === 1 ? '1 case, ready' : `${total} cases, all ready`
      : `${ready} of ${total} cases ready`,
  boxWriting: 'Writing the explanations…',
  boxReady: 'Ready',
  viewLabel: 'Show',
  viewBoxes: 'Digest boxes only',
  viewFull: 'With my reviewer text',
  whereIn: (heading: string | null, excerpt: string) =>
    heading ? `In your reviewer, under “${heading}”: “${excerpt}”` : `In your reviewer: “${excerpt}”`,
  whereUnplaced: 'We could not find this case in a paragraph of your file, so it is listed here.',
  ownDigestsTitle: 'Your file already has digests in it',
  ownDigests: (n: number) =>
    `We found ${n === 1 ? '1 digest' : `${n} digests`} you wrote yourself (like “Digest 1: Facts and Doctrine”). We cannot tell them apart from your other text, so we keep them and add our own box next to each case. A case may appear twice. For a cleaner result, upload your reviewer without the digests.`,
}

/** Where a field's text came from, in the words a student would use. Nothing is shown for the student's own writing. */
export const originLabel: Record<string, string | null> = {
  court_heading: 'The Court’s own words, under its heading',
  court_ruling: 'The Court’s own ruling',
  student_picked: 'Paragraphs you picked',
  student_pasted: 'Pasted by you',
  ai_drafted: 'Drafted from the decision. Check it.',
  student_written: 'Written by you',
  empty: null,
}

export const digestActions = {
  edit: 'Edit',
  save: 'Save',
  cancel: 'Cancel',
  saving: 'Saving…',
  pick: 'Pick paragraphs',
  paste: 'Paste text',
  restore: 'Put back the system’s version',
  writeAgain: 'Write it again',
  pickTitle: 'Pick paragraphs of the decision',
  pickHelp: 'Click the first paragraph, then the last one. We copy the Court’s exact words.',
  pickUse: (n: number) => (n === 1 ? 'Use this paragraph' : `Use these ${n} paragraphs`),
  pickClear: 'Start again',
  askLabel: 'Ask your own question about this case',
  askPlaceholder: 'e.g. Give me 4 sentences of the facts in plain words',
  askButton: 'Ask',
  asking: 'Asking…',
  stillWriting: 'Still being written…',
  showMore: 'Show more',
  showLess: 'Show less',
  emptyPick: 'Pick from the decision',
  emptyPaste: 'Paste your own',
  emptyWrite: 'Write it yourself',
  basedOn: (paragraphs: string[]) =>
    paragraphs.length === 1 ? `Based on paragraph ${paragraphs[0]} of the decision` : `Based on paragraphs ${paragraphs.join(', ')} of the decision`,
}
