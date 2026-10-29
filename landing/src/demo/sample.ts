/** The sample the app replica plays: a real decision, G.R. No. 180046, as CaseLens stores it (backend/tests/fixtures/gr_180046_2009.html,
 *  read with the app's own parser). Paragraph numbers are the stored paragraph indexes. The digest sentences were written for this page
 *  and each one checked by hand against the paragraph it cites; the dropped one shows what the checks strike out. */

export type Paragraph = { id: string; text: string }

export type DigestSentence = {
  text: string
  cites: string[]
  /** Set on the one sentence the checks drop: why, in the app's words. */
  dropped?: string
}

export type DigestSection = { title: string; sentences: DigestSentence[] }

export const sampleCase = {
  name: 'Review Center Association of the Philippines v. Ermita',
  fullTitle:
    'Review Center Association of the Philippines vs. Executive Secretary Eduardo Ermita and Commission on Higher Education',
  number: 'G.R. No. 180046',
  query: '180046',
  decided: 'April 2, 2009',
  division: 'En Banc',
  ponente: 'Carpio, J.',
  subject: 'Constitutional Law',
  source: 'Lawphil',
  sourceUrl: 'https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html',
} as const

export const paragraphs: Record<string, Paragraph> = {
  P9: {
    id: 'P9',
    text: 'On 11 and 12 June 2006, the Professional Regulation Commission (PRC) conducted the Nursing Board Examinations nationwide. … The PRC later admitted the leakage and traced it to two Board of Nursing members.',
  },
  P11: {
    id: 'P11',
    text: 'On 8 September 2006, President Arroyo issued EO 566 which authorized the CHED to supervise the establishment and operation of all review centers and similar entities in the Philippines.',
  },
  P26: {
    id: 'P26',
    text: 'On 26 October 2007, petitioner filed a petition for Prohibition and Mandamus before this Court praying for the annulment of the RIRR, the declaration of EO 566 as invalid and unconstitutional, and the prohibition against CHED from implementing the RIRR.',
  },
  P65: {
    id: 'P65',
    text: '1. Whether EO 566 is an unconstitutional exercise by the Executive of legislative power as it expands the CHED’s jurisdiction; and',
  },
  P103: {
    id: 'P103',
    text: 'A review center is not an institution of higher learning as contemplated by RA 7722. It does not offer a degree-granting program that would put it under the jurisdiction of the CHED. … Thus, programs given by review centers could not be considered “programs x x x of higher learning” that would put them under the jurisdiction of the CHED.',
  },
  P109: {
    id: 'P109',
    text: 'The President has no inherent or delegated legislative power to amend the functions of the CHED under RA 7722. Legislative power is the authority to make laws and to alter or repeal them, and this power is vested with the Congress under Section 1, Article VI of the 1987 Constitution …',
  },
  P132: {
    id: 'P132',
    text: 'WHEREFORE, we GRANT the petition and the petition-in-intervention. We DECLARE Executive Order No. 566 and Commission on Higher Education Memorandum Order No. 30, series of 2007 VOID for being unconstitutional.',
  },
}

export const digest: DigestSection[] = [
  {
    title: 'Doctrine',
    sentences: [
      {
        text: 'The President has no inherent or delegated legislative power to amend the functions Congress gave the CHED under RA 7722; legislative power belongs to Congress.',
        cites: ['P109'],
      },
    ],
  },
  {
    title: 'Facts',
    sentences: [
      {
        text: 'After a leak in the June 2006 Nursing Board Examinations, President Arroyo issued EO 566, which put all review centers under the CHED’s supervision.',
        cites: ['P9', 'P11'],
      },
      {
        text: 'The Review Center Association asked the Court to annul the CHED’s rules and declare EO 566 unconstitutional.',
        cites: ['P26'],
      },
    ],
  },
  {
    title: 'Issue',
    sentences: [
      {
        text: 'Is EO 566 an unconstitutional exercise of legislative power by the Executive, because it expands the CHED’s jurisdiction? YES.',
        cites: ['P65'],
      },
    ],
  },
  {
    title: 'Ruling',
    sentences: [
      {
        text: 'A review center is not an institution of higher learning under RA 7722, so its programs are outside the CHED’s jurisdiction.',
        cites: ['P103'],
      },
      {
        text: 'The Court held that review centers can never be regulated by law.',
        cites: ['P103'],
        dropped: 'Dropped: paragraph 103 does not say this.',
      },
      {
        text: 'The Court granted the petition and declared EO 566 and the CHED’s rules void for being unconstitutional.',
        cites: ['P132'],
      },
    ],
  },
]

/** The first sentence a visitor sees selected, and the order the replica walks through when it plays. */
export const sentenceOrder: { section: number; sentence: number }[] = digest.flatMap((section, s) =>
  section.sentences.map((_, i) => ({ section: s, sentence: i })),
)
