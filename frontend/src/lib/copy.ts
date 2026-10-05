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

export const upload = {
  maxBytes: 5 * 1024 * 1024,
  tooBig: 'That file is larger than 5 MB. Try a smaller one.',
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

/** The page shown before the app opens, when the owner set an access code. */
export const accessCopy = {
  opening: 'Opening CaseLens…',
  intro: 'This app is shared with a few people. Enter the access code you were given.',
  label: 'Access code',
  submit: 'Open CaseLens',
  unreachable: "We couldn't reach the server. Try again in a minute.",
}

/** The "How to use CaseLens" page. Plain words, one idea per step. The result labels are not repeated here: the page shows the
 *  real ones from `citationStatus`, so the guide cannot drift from the app. */
export type GuideStep = { title: string; body: string[] }

export const guideCopy = {
  navLabel: 'How to use it',
  title: 'How to use CaseLens',
  description: 'Upload decisions, tag their subject, and get a checked digest of each in the format your professor asks for.',
  promise:
    'CaseLens keeps the Supreme Court cases you upload, filed under the subjects you choose, and writes a digest of each one. It gets the real decision from Lawphil and shows where everything comes from. It never guesses: where the decision does not say something, the digest says so. You always decide what to keep.',
  libraryTitle: 'From upload to digest',
  librarySteps: [
    {
      title: 'One case: Individual',
      body: [
        'Open “Individual”. Find the case on Lawphil by its name or G.R. number and press “Choose”, or upload its file (a decision, or your reviewer with one case).',
        'Say what subject it is, then press “Open the case”. You can read the full decision right away; its digest is written in a few minutes.',
      ],
    },
    {
      title: 'Many cases: Bulk',
      body: [
        'Open “Bulk”. Drop the decision files (PDF or Word), or press “Have G.R. numbers instead?” and type the numbers. Each file or number is one case. The cases a decision only mentions are not added, and a case you give twice is shown once.',
        'Say what subject they are, then press “Generate case digests”.',
      ],
    },
    {
      title: 'Label it: Subject Tags and Topic scope',
      body: [
        'Pick one or more Subject Tags (Civil Law, Constitutional Law, Remedial Law and the others). You label the case: the app never guesses a subject. The tags apply to every case in the upload, and you can change them later on the case page.',
        'If you want the digest to focus on one doctrine or issue, write it in Topic scope (for example “Presidential powers”). Leave it empty for the standard digest.',
      ],
    },
    {
      title: 'Find it in the Case library, under My uploads',
      body: [
        'After “Open the case” or “Generate case digests” you go straight to your upload: its cases on the left, the digest of the one you choose in the middle. Each digest takes about 3 to 5 minutes; you can leave the page.',
        'The digest follows the format your professor asks for: Doctrine, Facts, Issue, Ruling, Ratio Decidendi, the dissents, the topic explained and why the case matters. Every part says which paragraphs of the decision it rests on, and anything the checks could not back was left out. It is a draft: read it against the Court’s text.',
        'To change a part, press “Edit” beside its title, type, and press “Save”. Your text is kept in this upload only and goes into your Word download; “Put back the AI version” undoes it.',
      ],
    },
    {
      title: 'Ask the AI assistant',
      body: [
        'On the right of your upload’s page, ask anything about the case you are reading. The answer is written from the decision and every sentence is checked against it. If the decision does not say enough, it tells you so instead of guessing. On a phone, press “Ask the AI assistant”.',
      ],
    },
    {
      title: 'Download it',
      body: [
        'Use the buttons on the digest. Pick “Facts and Doctrine”, “Doctrine, Facts, Issue, Ruling” (1 to 2 pages) or the “Full case digest” (about 6 pages). The full text of the decision is a Word file too.',
        'Every case you uploaded is also under “All cases” in the Case library, filed under its tags.',
      ],
    },
  ] satisfies GuideStep[],
  extraTitle: 'More',
  steps: [
    {
      title: 'Not happy with the digest? Take the whole case',
      body: [
        'Use “Full text” on a row, then “Download full case (Word)”. You get the Court’s own text, every footnote and any opinions printed with it, nothing reworded, with a link to the official page.',
        'Then write your own digest from it.',
      ],
    },
    {
      title: 'Find any case',
      body: [
        'In the Case library, type a case name or a G.R. number in “Find a case by name or G.R. number”. Cases from 1987 onward are in the list. For an older case, add the year or paste its Lawphil link.',
        'Cases you open are kept in the Case library, with their footnotes, the ruling, and the laws and cases they cite.',
      ],
    },
  ] satisfies GuideStep[],
  goodToKnowTitle: 'Good to know',
  goodToKnow: [
    'CaseLens gives information, not legal advice. Lawphil gives no warranty that its text is complete or correct: confirm with the Supreme Court.',
    'If the writing service is busy, the case is still saved with its full text. The digest is written when the service answers again.',
    'The text of every decision comes from Lawphil, and each digest links to the official page.',
  ],
  faqTitle: 'Questions',
  faq: [
    {
      q: 'Why is part of the digest missing or short?',
      a: 'We only keep what the decision supports. If a sentence could not be backed by the Court’s paragraphs, it was left out, and the part says the decision does not say enough.',
    },
    {
      q: 'Can I trust the digest?',
      a: 'It is written from the decision, and each sentence is checked against it. It can still be wrong, so it is marked as a draft. The Court’s own words are the source.',
    },
    {
      q: 'A case could not be found. What now?',
      a: 'Check the number and year you wrote, or paste the case’s Lawphil link. For a case before 1987, write the year, like 88211 (1969).',
    },
  ],
  start: 'Open the case library',
}

/** The short card new visitors see once on the start page. */
export const welcomeCopy = {
  title: 'New here? It takes four steps',
  steps: ['Open one case in Individual, or many in Bulk', 'Say what subject it is and, if you like, a Topic scope', 'Find it in the Case library, under My uploads, and ask the AI assistant', 'Download it as a Word file'],
  guide: 'Read the full guide',
  dismiss: 'Got it',
  dismissLabel: 'Close this welcome card',
}

/** The full decision, on its own page. */
export const decisionCopy = {
  read: 'Read the full decision',
  back: 'Back to the case',
  opening: 'Opening the decision',
  failed: "The decision didn't open",
  missing: "We can't find that decision",
}

/** Taking the whole case away, for a student who wants to write the digest by hand. */
export const caseDownloadCopy = {
  one: 'Download full case (Word)',
  oneInBox: 'Download the full case',
  all: 'Download all cases (Word)',
  help: 'Not happy with a digest? Download the whole case and write your own. The file has the Court’s own text, its footnotes and any opinions, nothing reworded.',
}

/** The Case library: the client's drawing (subject rail, three columns, download options) and the Individual and Bulk entries above it. */
export const libraryCopy = {
  title: 'Case library',
  description: 'Your uploads, and every case saved, filed by subject. Read a digest, open the full decision, or download it as Word.',
  modeIndividual: 'Individual',
  modeBulk: 'Bulk',
  individualHelp: 'Look up one case by its name or G.R. number. You get the full text, and you say what subject it is.',
  individualButton: 'Find the case',
  individualPlaceholder: 'e.g. Marcos v. Manglapus, or 88211',
  whatSubject: 'What subject?',
  letSystemDecide: 'Let the system decide',
  allCases: 'All cases',
  noSubjectYet: 'No subject yet',
  railTitle: 'Filter by subject',
  columnCase: 'Case',
  columnNumber: 'G.R. No., date and ponente',
  columnActions: 'View / Download',
  caseDigest: 'Case digest',
  readDigest: 'Read the digest',
  digestWriting: 'Digest being written…',
  lawphilTitle: 'Also on Lawphil, not saved yet',
  lawphilHelp: 'These decisions are on Lawphil’s list but not in your library yet. Press “Open this case” to save one.',
  lawphilMore: (n: number) => `See all ${n} matches on Lawphil’s list`,
  lawphilNone: 'Nothing else on Lawphil’s list matches.',
  digestFailed: 'The digest could not be written yet.',
  fullText: 'Full text',
  download: 'Download',
  digestNotWritten: 'The digest is written when you open it.',
  optionShort: 'Facts and Doctrine',
  optionStandard: 'Doctrine, Facts, Issue, Ruling',
  optionStandardHint: '1 to 2 pages',
  optionFull: 'Full case digest',
  optionFullHint: 'about 6 pages',
  optionFullText: 'Full text of the decision',
  optionFullTextHint: 'Word',
  menuNeedsDigest: 'Write the digest first, then download it.',
  emptyTitle: 'Your library is empty',
  emptyBody: 'Cases are saved here when you open one in “Individual” or upload many in “Bulk”.',
  emptySubject: 'No case is filed under this subject yet.',
  noMatch: (q: string) => `No saved case matches “${q}”`,
  searchLabel: 'Filter your saved cases',
  savedTitle: 'Saved cases',
  savedNote: 'Only the cases already saved in CaseLens are listed here. To find any other decision, use “Find any decision on Lawphil” above.',
  lawphilSearch: 'Find any decision on Lawphil',
  lawphilSearchHelp: 'Finds every decision on Lawphil’s list, saved or not. Open one to save it to your library.',
  searchPlaceholder: 'Case name or G.R. number',
  ponente: (name: string) => `${name}, J.`,
  subjectLabel: 'Subject tags',
  subjectChanged: 'Tags saved.',
  subjectFailed: 'We could not save the tags. Try again.',
  noTags: 'No subject yet',
}

/** "Individual": one case, opened for its full text (the first line of the client's sketch). */
export const individualCopy = {
  title: 'Individual',
  description: 'One case: find it or upload it, say what subject it is, and open its full text. Its digest is written for you too.',
  step1: '1. Which case?',
  step2: '2. What subject?',
  findTab: 'Find it on Lawphil',
  fileTab: 'Upload the file',
  choose: 'Choose',
  chosen: 'Chosen',
  chooseLabel: (title: string) => `Choose ${title}`,
  picked: (title: string) => `Your case: ${title}`,
  change: 'Choose another',
  fileHelp: 'One decision (PDF or Word), or your reviewer with one case in it. Up to 5 MB.',
  fileButton: 'Choose the file',
  fileLabel: 'The case file (PDF or Word)',
  open: 'Open the case',
  opening: 'Opening…',
  needCase: 'Choose a case first: find it on Lawphil, or upload its file.',
  timeNote: 'You can read the full decision right away. The case digest takes about 3 to 5 minutes.',
}

/** "Bulk": many cases at once (the second line of the client's sketch). */
export const bulkPageCopy = {
  title: 'Bulk',
  description: 'Many cases at once: upload the decisions or your reviewer, or type the G.R. numbers, and say what subject they are.',
  generate: 'Generate case digests',
}

/** Moving around the app. */
export const navCopy = {
  back: 'Back',
  toLibrary: 'Back to the Case library',
  toUploads: 'Back to My uploads',
}

/** The pieces of the Individual and Bulk forms: the file drop, the Subject Tags and the Topic scope. */
export const uploadCopy = {
  title: 'New digest',
  description: 'Upload decisions or find a case, tag its subject, and get a case digest.',
  tabUpload: 'Upload file',
  tabSearch: 'Search cases',
  dropTitle: 'Drop the decision files here',
  dropHelp: 'PDF or Word, up to 5 MB each. Each file is one case. The cases a decision only mentions are not added.',
  choose: 'Choose files',
  filesLabel: 'Decision files (PDF or Word)',
  remove: (name: string) => `Remove ${name}`,
  removeShort: 'Remove',
  numbersToggle: 'Have G.R. numbers instead?',
  numbersLabel: 'G.R. numbers',
  numbersHelp: 'One per line, or separated by commas. Add a year for a case older than 1987, like 88211 (1969).',
  tagsLabel: 'Subject Tags (optional)',
  tagsCount: (n: number) => (n === 0 ? 'No subject selected' : n === 1 ? '1 subject selected' : `${n} subjects selected`),
  tagsHelp: 'Tags file the case in your library. They apply to every case in this upload. You can change them later on the case page.',
  tagsHelpCase: 'Tags file this case in your library. Press a subject to add it, press it again to remove it. It is saved at once.',
  scopeLabel: 'Topic scope',
  scopeHint: 'optional, narrows the digest to one doctrine or issue',
  scopeExample: 'Family Code under Conjugal Partnership of Gains',
  scopeUseExample: (text: string) => `Use the example: ${text}`,
  scopeCount: (n: number, max: number) => `${n}/${max}`,
  generate: 'Generate Case Digest',
  sending: (sent: number, total: number) => `Sending files: ${sent} of ${total}`,
  starting: 'Starting…',
  nothing: 'Add a file, or a G.R. number, first.',
  timeNote: 'We write a case digest of each case from the Court’s own decision. It takes about 3 to 5 minutes per case. You can leave the page.',
  failedToStart: 'We could not send all the files. The ones already sent are being worked on: see My uploads in the Case library.',
  searchHelp: 'Find the case on Lawphil’s list, then press “Generate digest”. The tags and topic scope below apply to it.',
  generateOne: 'Generate digest',
  generating: 'Starting…',
}

/** "My uploads" (in the Case library): every upload, and one upload's cases with their digests and the AI assistant. */
export const reviewsCopy = {
  title: 'My uploads',
  tabUploads: 'My uploads',
  tabCases: 'All cases',
  description: 'What you uploaded, newest first. Open one to read its digests, edit them, and ask the AI assistant.',
  emptyTitle: 'Nothing uploaded yet',
  emptyBody: 'Open one case in “Individual”, or many at once in “Bulk”. Each upload appears here, and its cases go into the library.',
  kind: { individual: 'Individual', bulk: 'Bulk' } as Record<string, string>,
  open: 'Open',
  delete: (name: string) => `Delete ${name}`,
  deleteTitle: 'Delete this upload?',
  deleteBody: 'The upload, your edits and the questions you asked in it will be removed. The cases and their digests stay in the Case library.',
  deleteConfirm: 'Delete',
  deleting: 'Deleting…',
  keep: 'Keep it',
  untitled: 'Upload',
  andMore: (n: number) => ` and ${n} more`,
  casesIn: (title: string) => `Cases in ${title}`,
  moreCases: (n: number) => (n === 1 ? 'and 1 more case' : `and ${n} more cases`),
  uploaded: (what: string) => `Uploaded: ${what}`,
  scope: (text: string) => `Topic scope: ${text}`,
  noScope: 'Standard digest',
  cases: (found: number, ready: number) => `${found === 1 ? '1 case' : `${found} cases`} · ${ready} ${ready === 1 ? 'digest' : 'digests'} ready`,
  stateGetting: 'Getting the cases…',
  stateWriting: (ready: number, found: number) => `Writing the digests (${ready} of ${found} ready)…`,
  stateReady: 'Ready',
  stateNotAdded: (n: number) => (n === 1 ? '1 item could not be added' : `${n} items could not be added`),
  stateNothing: 'No case was found',
  crumbLibrary: 'Case library',
  casesTitle: 'Cases in this upload',
  pickCase: 'Choose a case to read its digest.',
  waitingFirst: 'Your cases will appear here as each one is found.',
  nothingAdded: 'No case was added from this upload.',
  fullText: 'Full text',
  digestStates: { none: 'Not started', pending: 'Being written', ready: 'Ready', failed: 'Could not be written' } as Record<string, string>,
  page: (first: number, last: number, total: number) => `${first}–${last} of ${total}`,
}

/** The AI assistant panel on the right of an upload's page. */
export const assistantCopy = {
  title: 'AI assistant',
  open: 'Ask the AI assistant',
  close: 'Close the AI assistant',
  about: (name: string) => `About ${name}`,
  noCase: 'Choose a case to ask about it.',
  empty: 'Ask anything about this case. The answer is written from the decision, and every sentence is checked against it.',
  label: 'Your question',
  placeholder: 'e.g. What power did the President use?',
  ask: 'Ask',
  asking: 'Asking…',
  answering: 'Writing the answer…',
  noAnswer: 'The decision does not say enough to answer this. Try asking it another way.',
  drafted: 'Drafted from the decision. Check it.',
  sources: (paragraphs: string[]) => `Based on decision ${paragraphs.length === 1 ? 'paragraph' : 'paragraphs'} ${paragraphs.join(', ')}`,
  failed: 'Not answered',
  tooLong: (max: number) => `Keep it under ${max} characters.`,
}

/** The page of one case's digest. */
export const digestPageCopy = {
  back: 'Back to the case',
  edit: (title: string) => `Edit ${title}`,
  editShort: 'Edit',
  save: 'Save',
  saving: 'Saving…',
  cancel: 'Cancel',
  putBack: 'Put back the AI version',
  editedByYou: 'Edited by you',
  editHelp: 'Your text is kept in this upload only. A blank line starts a new paragraph, a line starting “- ” is a bullet point, a line starting “# ” is a subheading.',
  editLabel: (title: string) => `Your text for ${title}`,
  saveFailed: 'We could not save your text. Try again.',
  pageTitle: 'Case digest',
  writing: 'Writing the digest…',
  writingHelp: 'This takes a few minutes. You can leave this page; it will be here when you come back.',
  start: 'Write the digest',
  failedTitle: 'The digest could not be written',
  retry: 'Try again',
  rewrite: 'Write it again',
  downloadTitle: 'Download',
  downloadShort: 'Facts and Doctrine',
  downloadStandard: 'Doctrine, Facts, Issue, Ruling',
  downloadFull: 'Full case digest',
  includes: 'Prints',
  draftNote: 'Drafted from the decision. Check it.',
  sources: (paragraphs: string[]) => (paragraphs.length === 1 ? `Based on decision paragraph ${paragraphs[0]}` : `Based on decision paragraphs ${paragraphs.join(', ')}`),
  opinionSource: 'a separate opinion',
  recordSource: 'the case record',
  leftOut: (n: number) => `${n === 1 ? '1 sentence was' : `${n} sentences were`} left out because the decision did not support ${n === 1 ? 'it' : 'them'}.`,
  noSections: 'The decision did not give enough to write this digest.',
  topic: 'Topic',
  ponente: 'Ponente',
}

/** Bulk upload: many cases at once. Each file or number is ONE main case. */
export const bulkCopy = {
  help: 'Give many cases at once. Each G.R. number or file is one case: the cases a decision only mentions are not added, and a case you give twice is shown once.',
  textLabel: 'G.R. numbers',
  textHelp: 'One per line, or separated by commas. Add a year if the case is older than 1987, like 88211 (1969).',
  textPlaceholder: '88211\nG.R. No. 180046\n173931',
  filesLabel: 'Decision files (PDF or Word)',
  filesHelp: 'A file is one case. We read its G.R. number from the top of the page, then get the official decision from Lawphil.',
  filesChosen: (n: number) => (n === 1 ? '1 file chosen' : `${n} files chosen`),
  start: 'Start',
  starting: 'Starting…',
  sending: (sent: number, total: number) => `Sending files: ${sent} of ${total}`,
  nothing: 'Paste at least one G.R. number or choose a file.',
  failedToStart: 'We could not send all the files. The ones already sent are being worked on; start again with the rest.',
  progressTitle: 'Your bulk upload',
  recent: 'Recent bulk uploads',
  open: 'Open',
  total: (n: number) => (n === 1 ? '1 item' : `${n} items`),
  statusLabel: {
    queued: 'Waiting',
    found: 'In the library',
    duplicate: 'Same case as an earlier one',
    not_found: 'Not found',
    unreadable: 'Could not read',
    failed: 'Lawphil did not answer',
  } as Record<string, string>,
  summary: {
    found: 'in the library',
    duplicate: 'repeats (shown once)',
    not_found: 'not found',
    unreadable: 'could not be read',
    failed: 'need a retry',
    queued: 'waiting',
  } as Record<string, string>,
  digests: (ready: number, found: number) => `Digests written: ${ready} of ${found}`,
  digestsFailed: (n: number) => `${n === 1 ? '1 digest' : `${n} digests`} could not be written. Open the case and press “Write it again”.`,
  working: 'Working on it. You can leave this page and come back; it keeps going.',
  done: 'All done.',
  retry: 'Retry the ones Lawphil did not answer',
  retried: (n: number) => `${n} queued again.`,
  openLibrary: 'Open the case library',
  showOnly: 'Show',
  all: 'All',
  digestState: { none: 'Digest not asked for', pending: 'Digest being written', ready: 'Digest ready', failed: 'Digest failed' } as Record<string, string>,
  itemsLabel: 'Items of this upload',
  resultsTitle: 'Your upload',
  resultsCaption: 'The cases from this upload, one row each',
  caseCount: (n: number) => (n === 1 ? '1 case is in your library' : `${n} cases are in your library`),
  repeats: (n: number) => (n === 1 ? '1 repeat is shown once' : `${n} repeats are shown once`),
  notAdded: (n: number) => (n === 1 ? '1 item was not added' : `${n} items were not added`),
  notAddedTitle: 'Not added',
  waitingFirst: 'Your cases will appear here as each one is found.',
  nothingAdded: 'No case was added from this upload.',
  uploadMore: 'Upload more',
  wholeLibrary: 'See the whole library',
}
