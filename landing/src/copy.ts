/** Every word a visitor reads, in one place (the app keeps its wording the same way, in frontend/src/lib/copy.ts).
 *  Each claim traces to the product: README.md, docs/TECHNICAL_DOC.md, or the code. Numbers in `notes` say where they come from. */

export const siteCopy = {
  name: 'CaseLens',
  openApp: 'Open CaseLens',
  skip: 'Skip to the main content',
  menu: 'Open the menu',
  menuTitle: 'Menu',
  navLabel: 'Main',
  home: 'CaseLens, back to the top',
}

/** The page's parts, in order. All of them are in the navbar; "title" is the top of the page (the wordmark goes there). */
export const chapters = [
  { id: 'title', numeral: 'I', label: 'Top' },
  { id: 'how', numeral: 'II', label: 'How it works' },
  { id: 'check', numeral: 'III', label: 'The check' },
  { id: 'library', numeral: 'IV', label: 'Library' },
  { id: 'downloads', numeral: 'V', label: 'Downloads' },
  { id: 'limits', numeral: 'VI', label: 'Questions' },
] as const

export const navLinks = chapters.filter((chapter) => chapter.id !== 'title')

export type ChapterId = (typeof chapters)[number]['id']

export const themeCopy = {
  toDark: 'Switch to the dark theme',
  toLight: 'Switch to the light theme',
}

export const heroCopy = {
  title: 'From G.R. number to a checked case digest.',
  lead:
    'CaseLens gets the Supreme Court’s decision, writes the digest in your reviewer’s format, and checks every sentence against the paragraph it came from. What the decision does not say is struck out.',
  searchLabel: 'Case name or G.R. No.',
  searchPlaceholder: 'Ermita, or 180046',
  searchButton: 'Open',
  searchHelp: 'Opens the case in CaseLens. Decisions from 1987 onward.',
  searchEmpty: 'Type a case name or a G.R. number first.',
  seeHow: 'See how a sentence is checked',
  desktop: 'Desktop app for Windows',
  desktopShort: 'Windows app',
}

export const demoCopy = {
  label: 'CaseLens at work, on a real decision',
  sampleNote: 'Sample: the Court’s own paragraphs from G.R. No. 180046. Sped up: a digest takes about 2 minutes in the app.',
  chaptersLabel: 'Steps of the sample',
  chapters: [
    { id: 'find', label: 'Find the case' },
    { id: 'write', label: 'Write and check' },
    { id: 'digest', label: 'Read the digest' },
    { id: 'download', label: 'Download' },
  ],
  play: 'Play',
  pause: 'Pause',
  replay: 'Play again',
  announce: (step: number, label: string) => `Step ${step} of 4: ${label}`,
  realApp: 'Open the real app',
  navLabel: 'CaseLens menu (sample)',
  nav: ['Individual', 'Bulk', 'Case library', 'How to use it', 'Settings'],
  find: {
    title: 'Individual',
    help: 'Type a case name or G.R. No. and pick the exact case.',
    field: 'Case name or G.R. No.',
    hitSource: 'Lawphil',
    open: 'Open this case',
    subject: 'What subject?',
  },
  write: {
    writing: 'Writing the digest…',
    stages: {
      queued: 'Waiting for its turn',
      writing: 'Step 1 of 3 · The AI is writing the digest from the decision',
      checking: 'Step 2 of 3 · Checking each sentence against the decision',
      repairing: 'Step 3 of 3 · Fixing sentences the decision does not support',
    },
    help: 'You can read other cases meanwhile; this one appears by itself when it is done.',
  },
  digest: {
    drafted: 'Drafted from the decision. Check it.',
    pick: 'Point at a sentence to see the paragraph it rests on.',
    decision: 'The decision',
    supported: 'Supported',
    supportedBy: (ids: string) => `The checker read ${ids} and said “supported”.`,
    struck: 'Struck out',
    paragraph: (id: string) => `Paragraph ${id.slice(1)}`,
  },
  download: {
    button: 'Download',
    levels: [
      { id: 'short', label: 'Case Summary and Doctrine', note: 'About 1 page' },
      { id: 'standard', label: 'Doctrine, Facts, Issue, Ruling', note: '1 to 2 pages' },
      { id: 'full', label: 'Full case digest', note: 'About 6 pages' },
    ],
    file: 'Word file, ready for your reviewer',
  },
}

export const howCopy = {
  title: 'How it works',
  lead: 'Four steps, the same for one case or forty.',
  sources: [
    { name: 'Lawphil', when: 'first' },
    { name: 'SC E-Library', when: 'if Lawphil has none' },
  ],
  checkedSample: 'A review center is not an institution of higher learning…',
  supported: 'Supported',
  steps: [
    {
      title: 'Give it a case',
      body: 'Type a case name or G.R. No. (Individual), or drop PDF and Word files and pasted numbers (Bulk). Answer “What subject?”, or let CaseLens suggest one.',
    },
    {
      title: 'It gets the official decision',
      body: 'From Lawphil, or from the Supreme Court E-Library when Lawphil does not have it. Every case keeps a link to its official page.',
    },
    {
      title: 'It writes the digest and checks it',
      body: 'Doctrine, Facts, Issue, Ruling, Ratio Decidendi, Dissents, Topic Explained and Why This Case Matters. Every sentence names its paragraphs and is checked.',
    },
    {
      title: 'You read, change and download',
      body: 'Rewrite any part in your own words, put the AI version back, ask your own question about the case, and download it as Word.',
    },
  ],
}

export const checkCopy = {
  title: 'The check',
  lead: 'A general AI chat can say things a decision never says. In law, one wrong sentence is a real problem. So every sentence CaseLens writes goes through these checks before you see it.',
  stages: [
    { title: 'The writer', body: 'An AI writes the digest from the decision and names the paragraphs each sentence uses.' },
    { title: 'The code check', body: 'A paragraph that does not exist, or a number or name the decision never mentions, fails at once. A risky sentence (“always”, “only”, a party’s argument written as the Court’s holding) goes on to the checker.' },
    { title: 'The checker', body: 'A second AI is shown the sentence and only the paragraphs it cites. It must say “supported”.' },
    { title: 'One repair', body: 'A sentence that fails is rewritten once from its own paragraphs, and faces the same checks.' },
    { title: 'Struck out', body: 'What still fails is dropped. If the Doctrine, Facts, Issue or Ruling ends up empty, the digest says “Try again”. It is never shown as finished.' },
  ],
  resultLead: 'On 8 real decisions, 43 of 48 drafted sentences were kept, and a person read every one against the decision:',
  result: 'none was unsupported.',
  draftNote: 'Every digest still says “Drafted from the decision. Check it.”',
  kept: {
    steps: ['Every name and number is in paragraph 103.', 'The checker read paragraph 103: supported.'],
    verdict: 'Kept in the digest',
  },
  struck: {
    steps: ['“never” is not in paragraph 103: sent to the checker.', 'The checker read paragraph 103: not supported.', 'Rewritten once, checked again: still not supported.'],
    verdict: 'Struck out: not in the digest',
  },
}

export const libraryCopy = {
  title: 'Your case library',
  lead: 'Every case you open is kept by subject, one row per main case. A later Resolution, a repeat, or a decision filed under several G.R. numbers is never a second row.',
  subjectsLabel: 'Subjects',
  subjects: ['Constitutional Law', 'Civil Law', 'Criminal Law', 'Remedial Law', 'Political Law', 'Labor Law'],
  columns: ['Case', 'G.R. No.'],
  actionsHeader: 'Actions',
  actions: 'Digest · Download',
  caption: 'Saved cases under Constitutional Law (sample)',
  region: 'Saved cases (sample)',
  official: 'Every case links to its official page on Lawphil or the SC E-Library.',
  rows: [
    { name: 'Review Center Association of the Philippines v. Ermita', number: '180046', date: 'April 2, 2009', ponente: 'Carpio' },
    { name: 'Marcos v. Manglapus', number: '88211', date: 'September 15, 1989', ponente: 'Cortes' },
  ],
  bulkTitle: 'Many cases at once',
  bulk: 'Drop your reviewers or case files, or paste G.R. numbers. CaseLens adds one main case per file or number. A case a file only cites is never added, and anything it could not add is listed with the reason.',
  searchTitle: 'Find any decision',
  search: 'Search by case name or G.R. number, from 1987 onward. Cases not saved yet are found too, and open in a few seconds.',
}

export const downloadsCopy = {
  title: 'Three downloads',
  lead: 'The digest is written once. You choose how much of it goes into the Word file.',
  sheets: [
    { title: 'Case Summary and Doctrine', note: 'About 1 page', lines: ['Case Summary', 'Doctrine'] },
    { title: 'Doctrine, Facts, Issue, Ruling', note: '1 to 2 pages', lines: ['Doctrine', 'Facts', 'Issue', 'Ruling'] },
    {
      title: 'Full case digest',
      note: 'About 6 pages',
      lines: ['Case Summary', 'Doctrine', 'Facts', 'Issue', 'Ruling', 'Ratio Decidendi', 'Dissents', 'Topic Explained', 'Why This Case Matters'],
    },
  ],
  fullCase: 'Not happy with a digest? Download the full case: the Court’s own text, footnotes and opinions, nothing reworded.',
}

export const limitsCopy = {
  title: 'What it is not',
  lead: 'CaseLens helps you read faster. It does not read for you.',
  items: [
    'It gives no legal advice. Always read the digest against the decision.',
    'The searchable list starts in 1987. An older case needs its year or its Lawphil link.',
    'A scanned, picture-only PDF cannot be read.',
    'A.M. and A.C. cases are not covered yet.',
  ],
  faqTitle: 'Questions',
  faq: [
    {
      q: 'Does the AI write the Facts, Issue and Ruling?',
      a: 'The AI writes the digest, but every sentence names the paragraphs of the decision it rests on, is checked by code and by a second AI, and is dropped if the decision does not support it.',
    },
    {
      q: 'Where do the decisions come from?',
      a: 'From Lawphil (the Arellano Law Foundation), and from the Supreme Court E-Library for cases Lawphil does not have. CaseLens reads at most one page a second and keeps a copy, so it never asks for the same page twice.',
    },
    {
      q: 'Can I change what it wrote?',
      a: 'Yes. Rewrite any section in your own words, or put the AI version back. You can also ask your own question about a case; the answer cites the decision too.',
    },
    {
      q: 'Is there a desktop app?',
      a: 'Yes, for Windows. It runs on your own computer, keeps your library there, and updates itself.',
    },
  ],
}

export const closeCopy = {
  title: 'Your next reviewer starts with the case.',
  lead: 'Open one case, or a whole reviewer’s worth.',
  desktopNote: 'Prefer your own computer? Get the Windows app.',
}

/** Superscript notes on the page, gathered at the end like a decision's footnotes. */
export const notes = [
  { id: 'n1', text: 'Measured on 8 real decisions: 43 of 48 drafted sentences were kept; a person read every kept sentence against the decision text and found none unsupported (CaseLens README).' },
  { id: 'n2', text: 'The sample is G.R. No. 180046, Review Center Association of the Philippines v. Ermita, April 2, 2009 (En Banc, Carpio, J.), as stored from Lawphil. Paragraph numbers are CaseLens’s own. The digest sentences were written for this page; the dropped one shows what the checks strike out.' },
  { id: 'n3', text: 'About 35,000 decisions from 1987 onward, kept from Lawphil’s monthly lists of decisions.' },
]

export const footerCopy = {
  notesTitle: 'Notes',
  back: 'Back',
  backLabel: (n: number) => ` to the text of note ${n}`,
  sourcesTitle: 'Sources',
  sources:
    'Case text comes from Lawphil (Arellano Law Foundation) and the Supreme Court E-Library. Lawphil gives no warranty that its text is complete or correct: confirm with the Supreme Court. Cite the E-Library as “SC E-Library”; the official printed copy prevails. CaseLens is for information only and gives no legal advice.',
  made: 'Made for law students in the Philippines.',
}
