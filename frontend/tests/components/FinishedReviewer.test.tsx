import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { FinishedReviewer } from '@/features/digest/FinishedReviewer'

import afterAsk from '../fixtures/api/digest-after-ask.json'
import afterPick from '../fixtures/api/digest-after-pick.json'
import afterReset from '../fixtures/api/digest-after-reset.json'
import afterWrite from '../fixtures/api/digest-after-write.json'
import digest from '../fixtures/api/digest-ermita.json'
import badPassage from '../fixtures/api/error-bad-passage.json'
import reviewer from '../fixtures/api/finished-reviewer.json'
import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

/** The tests run on a pretend screen: a laptop (wide) unless a test says otherwise. */
function setScreen(wide: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: wide,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia
}
beforeEach(() => setScreen(true))
afterEach(() => document.getElementById('right-dock')?.remove())

const show = (checking = false, view: 'boxes' | 'full' = 'boxes') => renderApp(<FinishedReviewer uploadId={3} checking={checking} initialView={view} />)
const serve = (path: string, body: object, status = 200) =>
  server.use(http.get(`${API}${path}`, () => HttpResponse.json(body as Record<string, unknown>, { status })))

/** The first digest box (Review Center v. Ermita) once it has loaded. */
async function ermitaBox() {
  const box = await screen.findByRole('article', { name: /Review Center/ })
  await within(box).findByRole('heading', { name: 'Facts' })
  return box
}

describe('the finished reviewer (real responses from the running backend)', () => {
  it('with the reviewer text switched on, puts each digest box right after the paragraph that cites its case', async () => {
    await show(false, 'full')
    await ermitaBox()

    const cites = screen.getByText(/See Review Center v Ermita, 538 SCRA 428, GR no 180046/)
    const box = screen.getByRole('article', { name: /Review Center/ })
    expect(cites.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    // and before the next paragraph of the reviewer
    const next = screen.getByText(/Explanation: Legislative power is the authority/)
    expect(box.compareDocumentPosition(next) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })

  it('shows where each field came from: the Court’s words, or a drafted answer to be checked', async () => {
    await show()
    const box = await ermitaBox()
    expect(within(box).getByText(/On 11 and 12 June 2006, the Professional Regulation Commission/)).toBeInTheDocument()
    expect(within(box).getAllByText('The Court’s own words, under its heading').length).toBeGreaterThan(0)
    expect(within(box).getByText('The Court’s own ruling')).toBeInTheDocument()
    expect(within(box).getAllByText('Drafted from the decision. Check it.')).toHaveLength(2)
    expect(within(box).getAllByText(/Based on paragraphs? \d/).length).toBeGreaterThan(0)
  })

  it('names the Court’s record and links to the official page', async () => {
    await show()
    const box = await ermitaBox()
    expect(within(box).getByText(/G\.R\. No\. 180046/)).toBeInTheDocument()
    const link = within(box).getByRole('link', { name: /Court’s record on Lawphil/ })
    expect(link).toHaveAttribute('href', 'https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('says plainly why an empty field is empty, and never fills the Doctrine in by itself', async () => {
    await show()
    const box = await ermitaBox()
    const doctrine = within(box).getByRole('region', { name: 'Doctrine' })
    expect(within(doctrine).getByText(/Pick the paragraph that states the rule, or paste it\. We do not guess/)).toBeInTheDocument()
  })

  it('offers the Word file as a download', async () => {
    await show()
    await ermitaBox()
    const link = screen.getByRole('link', { name: /Download as Word/ })
    expect(link).toHaveAttribute('href', '/api/uploads/3/document.docx')
    expect(link).toHaveAttribute('download')
  })

  it('tells the student a PDF is rebuilt as a Word file (synthetic: the real response with source set to pdf)', async () => {
    serve('/uploads/3/document', { ...reviewer, source: 'pdf' })
    await show()
    expect(await screen.findByText(/Your PDF is rebuilt as a Word file/)).toBeInTheDocument()
  })
})

describe('changing a field', () => {
  it('typing over a field saves the student’s own words and marks them as theirs', async () => {
    const user = userEvent.setup()
    let sent: unknown
    server.use(
      http.put(`${API}/digests/9/fields/doctrine/text`, async ({ request }) => {
        sent = await request.json()
        return HttpResponse.json(afterWrite)
      }),
    )
    await show()
    const box = await ermitaBox()

    await user.click(within(box).getByRole('button', { name: 'Edit Doctrine' }))
    await user.type(within(box).getByRole('textbox', { name: 'Edit Doctrine' }), 'My own words about the rule.')
    await user.click(within(box).getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(sent).toEqual({ text: 'My own words about the rule.' }))
    expect(await within(box).findByText('My own words about the rule.')).toBeInTheDocument()
    expect(within(box).getByText('Written by you')).toBeInTheDocument()
  })

  it('picking paragraphs of the decision sends only the range; the Court’s words come from the server', async () => {
    const user = userEvent.setup()
    let sent: unknown
    server.use(
      http.put(`${API}/digests/9/fields/doctrine/passage`, async ({ request }) => {
        sent = await request.json()
        return HttpResponse.json(afterPick)
      }),
    )
    await show()
    const box = await ermitaBox()

    await user.click(within(box).getByRole('button', { name: 'Pick paragraphs for Doctrine' }))
    const dialog = await screen.findByRole('dialog')
    const paragraph = await within(dialog).findByRole('button', { name: /The President has no inherent or delegated legislative power/ })
    await user.click(paragraph)
    expect(within(dialog).getByText('Paragraph 109')).toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Use this paragraph' }))

    await waitFor(() => expect(sent).toEqual({ first: 109, last: 109 }))
    expect(await within(box).findByText('Paragraphs you picked')).toBeInTheDocument()
  })

  it('picking a range: first click, second click, and the count is shown', async () => {
    const user = userEvent.setup()
    await show()
    const box = await ermitaBox()
    await user.click(within(box).getByRole('button', { name: 'Pick paragraphs for Facts' }))
    const dialog = await screen.findByRole('dialog')
    const first = await within(dialog).findByRole('button', { name: /On 11 and 12 June 2006/ })
    await user.click(first)
    await user.click(within(dialog).getByRole('button', { name: /The President has no inherent or delegated legislative power/ }))
    expect(within(dialog).getByText('Paragraphs 9 to 109')).toBeInTheDocument()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Pick at most 40 paragraphs at a time.')
    expect(within(dialog).getByRole('button', { name: /Use these 101 paragraphs/ })).toBeDisabled()
  })

  it('shows a server refusal in the server’s own plain words', async () => {
    const user = userEvent.setup()
    server.use(http.put(`${API}/digests/9/fields/doctrine/passage`, () => HttpResponse.json(badPassage, { status: 422 })))
    await show()
    const box = await ermitaBox()
    await user.click(within(box).getByRole('button', { name: 'Pick paragraphs for Doctrine' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(await within(dialog).findByRole('button', { name: /The President has no inherent or delegated legislative power/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Use this paragraph' }))
    expect(await within(dialog).findByText('Pick paragraphs 6 to 132 of the decision.')).toBeInTheDocument()
  })

  it('pasting text marks it as pasted', async () => {
    const user = userEvent.setup()
    let sent: unknown
    server.use(
      http.post(`${API}/digests/9/fields/doctrine/paste`, async ({ request }) => {
        sent = await request.json()
        return HttpResponse.json({ ...afterWrite })
      }),
    )
    await show()
    const box = await ermitaBox()
    await user.click(within(box).getByRole('button', { name: 'Paste text for Doctrine' }))
    expect(within(box).getByRole('button', { name: 'Save' })).toBeDisabled() // nothing pasted yet
    await user.type(within(box).getByRole('textbox', { name: 'Paste text into Doctrine' }), 'Pasted rule.')
    await user.click(within(box).getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(sent).toEqual({ text: 'Pasted rule.' }))
  })

  it('an edited field can be put back as the system made it', async () => {
    const user = userEvent.setup()
    let called = false
    serve('/digests/9', afterWrite)
    server.use(
      http.post(`${API}/digests/9/fields/doctrine/reset`, () => {
        called = true
        return HttpResponse.json(afterReset)
      }),
    )
    await show()
    const box = await ermitaBox()
    await user.click(within(box).getByRole('button', { name: /Put back the system’s version: Doctrine/ }))
    await waitFor(() => expect(called).toBe(true))
  })

  it('a field that cannot be reset has no reset button', async () => {
    await show()
    const box = await ermitaBox()
    expect(within(box).queryByRole('button', { name: /Put back the system’s version/ })).toBeNull()
  })

  it('the student can ask a question of their own about a case, and it shows as being written in that case’s box', async () => {
    const user = userEvent.setup()
    let sent: unknown
    server.use(
      http.post(`${API}/digests/9/questions`, async ({ request }) => {
        sent = await request.json()
        return HttpResponse.json(afterAsk, { status: 202 })
      }),
    )
    await show()
    const box = await ermitaBox()
    const ask = screen.getByRole('region', { name: 'Ask your own question' })
    await user.type(within(ask).getByRole('textbox', { name: 'Ask your own question about this case' }), 'Is EO 566 valid?')
    await user.click(within(ask).getByRole('button', { name: 'Ask' }))
    await waitFor(() => expect(sent).toEqual({ question: 'Is EO 566 valid?' }))
    expect(await within(box).findByRole('heading', { name: 'Is EO 566 valid?' })).toBeInTheDocument()
    expect(within(box).getByText('Still being written…')).toBeInTheDocument()
    expect(within(ask).getByRole('status')).toHaveTextContent('Writing…') // and in the panel itself, as a chat
    expect(within(ask).getByText('Is EO 566 valid?')).toBeInTheDocument() // the student's question as a message
  })

  it('an explanation that is still being written says so and offers no edit yet (synthetic: a real field set to pending)', async () => {
    const pending = { ...digest, status: 'pending', fields: digest.fields.map((f) => (f.key === 'topic' ? { ...f, state: 'pending', text: '', origin: 'empty', cites: [] } : f)) }
    serve('/digests/9', pending)
    await show()
    const box = await screen.findByRole('article', { name: /Review Center/ })
    const topic = await within(box).findByRole('region', { name: 'Topic explained' })
    expect(within(topic).getByRole('status')).toHaveTextContent('Still being written…')
    expect(within(topic).queryByRole('button')).toBeNull()
  })
})

describe('waiting and problems', () => {
  it('while cases are still being found it says so instead of looking empty (synthetic: the real response with no boxes)', async () => {
    serve('/uploads/3/document', { ...reviewer, blocks: reviewer.blocks.map((b) => ({ ...b, boxes: [] })), all_ready: true })
    await show(true)
    expect(await screen.findByText(/We are still finding your cases/)).toBeInTheDocument()
  })

  it('with nothing to show and nothing left to wait for, it explains', async () => {
    serve('/uploads/3/document', { ...reviewer, blocks: reviewer.blocks.map((b) => ({ ...b, boxes: [] })), all_ready: true })
    await show(false)
    expect(await screen.findByText('No case boxes yet')).toBeInTheDocument()
  })

  it('says when some explanations are still being written (synthetic: the real response with all_ready false)', async () => {
    serve('/uploads/3/document', { ...reviewer, all_ready: false })
    await show()
    expect(await screen.findByText(/Some explanations are still being written/)).toBeInTheDocument()
  })

  it('a failed load says what to do', async () => {
    server.use(http.get(`${API}/uploads/:id/document`, () => HttpResponse.json({ detail: 'x' }, { status: 500 })))
    await show()
    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText("The finished reviewer didn't open")).toBeInTheDocument()
    expect(within(alert).getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('the revamped box', () => {
  it('separates the Court’s own words from the explanations written in plain words', async () => {
    await show()
    const box = await ermitaBox()
    expect(within(box).getByRole('heading', { name: 'From the Court' })).toBeInTheDocument()
    expect(within(box).getByRole('heading', { name: 'In plain words' })).toBeInTheDocument()
    const court = within(box).getByRole('heading', { name: 'From the Court' }).parentElement as HTMLElement
    expect(within(court).getByRole('region', { name: 'Ruling' })).toBeInTheDocument()
    expect(within(court).queryByRole('region', { name: 'Topic explained' })).toBeNull()
  })

  it('shows how many cases are ready and lets the student jump to each one', async () => {
    await show()
    await ermitaBox()
    expect(screen.getByText('3 cases, all ready')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Cases in your reviewer' })
    expect(within(nav).getAllByRole('link')).toHaveLength(3)
    expect(within(nav).getAllByRole('link')[0]).toHaveAttribute('href', '#digest-9')
  })

  it('a digest can be hidden and shown again', async () => {
    const user = userEvent.setup()
    await show()
    const box = await ermitaBox()
    const hide = within(box).getByRole('button', { name: 'Hide this digest' })
    expect(hide).toHaveAttribute('aria-expanded', 'true')
    await user.click(hide)
    expect(within(box).getByRole('button', { name: 'Show this digest' })).toHaveAttribute('aria-expanded', 'false')
    expect(within(box).queryByRole('region', { name: 'Ruling' })).toBeNull()
    await user.click(within(box).getByRole('button', { name: 'Show this digest' }))
    expect(within(box).getByRole('region', { name: 'Ruling' })).toBeInTheDocument()
  })

  it('long Court text starts folded and can be opened and folded again', async () => {
    const user = userEvent.setup()
    await show()
    const box = await ermitaBox()
    const facts = within(box).getByRole('region', { name: 'Facts' })
    const more = within(facts).getByRole('button', { name: /Show more/ })
    expect(more).toHaveAttribute('aria-expanded', 'false')
    await user.click(more)
    expect(within(facts).getByRole('button', { name: /Show less/ })).toHaveAttribute('aria-expanded', 'true')
  })

  it('a drafted explanation is a short list of points with its sources, and is marked as a draft (synthetic: the real answer split into points)', async () => {
    const points = 'The Court declared EO 566 void.\n\nThe President cannot make law by order.\n\nThe IRR fell with it.'
    serve('/digests/9', { ...digest, fields: digest.fields.map((f) => (f.key === 'why' ? { ...f, text: points } : f)) })
    await show()
    const box = await ermitaBox()
    const why = within(box).getByRole('region', { name: 'Why this case matters' })
    expect(within(why).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'The Court declared EO 566 void.',
      'The President cannot make law by order.',
      'The IRR fell with it.',
    ])
    expect(within(why).getByText('Drafted from the decision. Check it.')).toBeInTheDocument()
  })

  it('an empty field says why and offers the clear next steps, never a guess', async () => {
    await show()
    const box = await ermitaBox()
    const doctrine = within(box).getByRole('region', { name: 'Doctrine' })
    expect(within(doctrine).getByText(/We do not guess which one it is/)).toBeInTheDocument()
    expect(within(doctrine).getByRole('button', { name: 'Pick paragraphs for Doctrine' })).toBeInTheDocument()
    expect(within(doctrine).getByRole('button', { name: 'Paste text for Doctrine' })).toBeInTheDocument()
    expect(within(doctrine).getByRole('button', { name: 'Edit Doctrine' })).toBeInTheDocument()
  })
})

describe('the reviewer’s own titles', () => {
  it('stand out as real headings, so the document can be scanned, while body text stays plain', async () => {
    await show(false, 'full')
    await ermitaBox()
    expect(screen.getByRole('heading', { name: 'Constitutional Law Reviewer', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /PART NINE: LEGISLATIVE DEPARTMENT/, level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'I. Legislative power Section 1:', level: 3 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'II. Reclassification of positions', level: 3 })).toBeInTheDocument()
    // a paragraph that cites a case is body text, not a heading
    expect(screen.queryByRole('heading', { name: /See Review Center v Ermita/ })).toBeNull()
    expect(screen.getByText(/Explanation: Legislative power is the authority/).tagName).toBe('P')
  })
})

describe('a file that already has the student’s own digests', () => {
  it('says so, once, in plain words, and tells the student what to do', async () => {
    serve('/uploads/3/document', { ...reviewer, own_digests: 2 }) // synthetic: the real response with the count set to 2
    await show()
    const note = await screen.findByRole('complementary', { name: 'Your file already has digests in it' })
    expect(within(note).getByText(/We found 2 digests you wrote yourself/)).toBeInTheDocument()
    expect(within(note).getByText(/upload your reviewer without the digests/)).toBeInTheDocument()
  })

  it('says nothing for a plain reviewer (the real response)', async () => {
    await show()
    await ermitaBox()
    expect(screen.queryByRole('complementary')).toBeNull()
  })

  it('uses the singular for one digest', async () => {
    serve('/uploads/3/document', { ...reviewer, own_digests: 1 })
    await show()
    expect(await screen.findByText(/We found 1 digest you wrote yourself/)).toBeInTheDocument()
  })
})


describe('showing only the digest boxes (the default)', () => {
  it('leaves out the reviewer’s long text and shows just the boxes', async () => {
    await show()
    await ermitaBox()
    expect(screen.getAllByRole('article')).toHaveLength(3)
    expect(screen.queryByText(/Explanation: Legislative power is the authority/)).toBeNull() // body text of the reviewer
    expect(screen.queryByRole('heading', { name: 'Constitutional Law Reviewer' })).toBeNull()
  })

  it('says where each box sits in the reviewer: the heading above it and the start of the citing paragraph', async () => {
    await show()
    await ermitaBox()
    expect(screen.getByText(/In your reviewer, under “I\. Legislative power Section 1:”: “Section 1: The legislative power shall be vested/)).toBeInTheDocument()
    expect(screen.getByText(/In your reviewer, under “II\. Reclassification of positions”: “A reclassified civil service position/)).toBeInTheDocument()
  })

  it('a switch brings the reviewer’s text back, and another puts it away again', async () => {
    const user = userEvent.setup()
    await show()
    await ermitaBox()
    const boxesOnly = screen.getByRole('button', { name: 'Digest boxes only' })
    const withText = screen.getByRole('button', { name: 'With my reviewer text' })
    expect(boxesOnly).toHaveAttribute('aria-pressed', 'true')
    expect(withText).toHaveAttribute('aria-pressed', 'false')

    await user.click(withText)
    expect(await screen.findByText(/Explanation: Legislative power is the authority/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Constitutional Law Reviewer' })).toBeInTheDocument()
    expect(withText).toHaveAttribute('aria-pressed', 'true')

    await user.click(screen.getByRole('button', { name: 'Digest boxes only' }))
    expect(screen.queryByText(/Explanation: Legislative power is the authority/)).toBeNull()
  })

  it('a case that could not be found in a paragraph still gets its box, with a plain reason (synthetic: one box moved to unplaced)', async () => {
    const moved = reviewer.blocks[3].boxes
    serve('/uploads/3/document', {
      ...reviewer,
      blocks: reviewer.blocks.map((b, i) => (i === 3 ? { ...b, boxes: [] } : b)),
      unplaced: moved,
    })
    await show()
    await ermitaBox()
    expect(screen.getByText(/We could not find this case in a paragraph of your file/)).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })

  it('the download is still the whole document, whichever view is on', async () => {
    await show()
    await ermitaBox()
    expect(screen.getByRole('link', { name: /Download as Word/ })).toHaveAttribute('href', '/api/uploads/3/document.docx')
  })
})


describe('one question form for the whole file', () => {
  it('is a single card on the review page, outside every digest, with a plain explanation', async () => {
    await show()
    await ermitaBox()
    const asks = screen.getAllByRole('region', { name: 'Ask your own question' })
    expect(asks).toHaveLength(1) // one form, not one per digest
    const ask = asks[0]
    for (const box of screen.getAllByRole('article')) expect(box.contains(ask)).toBe(false)
    expect(within(ask).getByRole('heading', { name: 'Ask your own question' })).toBeInTheDocument()
    expect(within(ask).getByText(/Ask anything about this case. The answer is written from the decision and checked/)).toBeInTheDocument()
  })

  it('lets the student choose which case the question is about', async () => {
    await show()
    await ermitaBox()
    const ask = screen.getByRole('region', { name: 'Ask your own question' })
    const which = within(ask).getByRole('combobox', { name: 'Which case?' })
    expect(within(which).getAllByRole('option')).toHaveLength(3)
    expect(within(which).getAllByRole('option')[0]).toHaveTextContent(/Review Center/)
  })

  it('sends the question to the case that was chosen', async () => {
    const user = userEvent.setup()
    let url = ''
    server.use(
      http.post(`${API}/digests/:id/questions`, async ({ params }) => {
        url = String(params.id)
        return HttpResponse.json(afterAsk, { status: 202 })
      }),
    )
    await show()
    await ermitaBox()
    const ask = screen.getByRole('region', { name: 'Ask your own question' })
    const which = within(ask).getByRole('combobox', { name: 'Which case?' })
    await user.selectOptions(which, within(which).getAllByRole('option')[1])
    await user.type(within(ask).getByRole('textbox', { name: 'Ask your own question about this case' }), 'Who won?')
    await user.click(within(ask).getByRole('button', { name: 'Ask' }))
    await waitFor(() => expect(url).toBe('10'))
  })

  it('with only one case there is nothing to choose: it just says which case (synthetic: one box)', async () => {
    serve('/uploads/3/document', { ...reviewer, blocks: reviewer.blocks.map((b) => ({ ...b, boxes: b.boxes.slice(0, b.index === 3 ? 1 : 0) })) })
    await show()
    await ermitaBox()
    const ask = screen.getByRole('region', { name: 'Ask your own question' })
    expect(within(ask).queryByRole('combobox')).toBeNull()
    expect(within(ask).getByText(/About: Review Center/)).toBeInTheDocument()
  })

  it('is no longer inside the digest card', async () => {
    await show()
    const box = await ermitaBox()
    expect(within(box).queryByRole('textbox', { name: /Ask your own question/ })).toBeNull()
    expect(within(box).queryByRole('button', { name: 'Ask' })).toBeNull()
  })

  it('the Ask button stays off until something is typed', async () => {
    await show()
    await ermitaBox()
    expect(within(screen.getByRole('region', { name: 'Ask your own question' })).getByRole('button', { name: 'Ask' })).toBeDisabled()
  })

  it('is not shown when there is no case yet (nothing to ask about)', async () => {
    serve('/uploads/3/document', { ...reviewer, blocks: reviewer.blocks.map((b) => ({ ...b, boxes: [] })), all_ready: true })
    await show(false)
    await screen.findByText('No case boxes yet')
    expect(screen.queryByRole('region', { name: 'Ask your own question' })).toBeNull()
  })
})

describe('the question panel (right side, like a coding assistant)', () => {
  it('shows the conversation inside the panel: the question, then the answer as points with its sources, and a link to the digest box', async () => {
    const answered = {
      ...afterAsk,
      fields: afterAsk.fields.map((f) =>
        f.key === 'q1' ? { ...f, state: 'ready', origin: 'ai_drafted', text: 'Yes, EO 566 is void.\n\nThe President cannot make law by order.', cites: ['P121', 'P132'] } : f,
      ),
    } // synthetic: the real reply with the question answered
    serve('/digests/9', answered)
    await show()
    await ermitaBox()
    const panel = screen.getByRole('region', { name: 'Ask your own question' })
    const log = await within(panel).findByRole('log', { name: 'Your questions and the answers' })
    expect(within(log).getByText('Is EO 566 valid?')).toBeInTheDocument()
    expect(within(log).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Yes, EO 566 is void.', 'The President cannot make law by order.'])
    expect(within(log).getByText('Based on paragraphs 121, 132 of the decision')).toBeInTheDocument()
    expect(within(log).getByRole('link', { name: 'Show in the digest box' })).toHaveAttribute('href', '#digest-9')
  })

  it('shows a question that is still being written as a message with a spinner', async () => {
    serve('/digests/9', afterAsk) // the real reply: the question is still being written
    await show()
    await ermitaBox()
    const panel = screen.getByRole('region', { name: 'Ask your own question' })
    expect(await within(panel).findByText('Is EO 566 valid?')).toBeInTheDocument()
    expect(within(panel).getByRole('status')).toHaveTextContent('Writing…')
  })

  it('offers a few questions to start with, and a click puts one in the box to read and send', async () => {
    const user = userEvent.setup()
    await show()
    await ermitaBox()
    const panel = screen.getByRole('region', { name: 'Ask your own question' })
    await user.click(within(panel).getByRole('button', { name: 'Give me 4 sentences of the facts in plain words' }))
    expect(within(panel).getByRole('textbox', { name: 'Ask your own question about this case' })).toHaveValue('Give me 4 sentences of the facts in plain words')
  })

  it('sends with the Enter key, and Shift+Enter makes a new line', async () => {
    const user = userEvent.setup()
    let sent: unknown
    server.use(
      http.post(`${API}/digests/9/questions`, async ({ request }) => {
        sent = await request.json()
        return HttpResponse.json(afterAsk, { status: 202 })
      }),
    )
    await show()
    await ermitaBox()
    const box = within(screen.getByRole('region', { name: 'Ask your own question' })).getByRole('textbox', { name: 'Ask your own question about this case' })
    await user.type(box, 'Line one{Shift>}{Enter}{/Shift}Line two')
    expect(box).toHaveValue('Line one\nLine two')
    await user.keyboard('{Enter}')
    await waitFor(() => expect(sent).toEqual({ question: 'Line one\nLine two' }))
  })

  it('warns that the AI can make mistakes', async () => {
    await show()
    await ermitaBox()
    expect(within(screen.getByRole('region', { name: 'Ask your own question' })).getByText(/It can make mistakes: check every answer/)).toBeInTheDocument()
  })

  it('shows no messages when nothing has been asked yet (the real digest)', async () => {
    await show()
    await ermitaBox()
    const panel = screen.getByRole('region', { name: 'Ask your own question' })
    expect(within(panel).getByRole('log').querySelectorAll('li')).toHaveLength(3) // only the three starter questions
  })

})


describe('docked on the right edge of the window', () => {
  const addDock = () => {
    const dock = document.createElement('aside')
    dock.id = 'right-dock'
    document.body.appendChild(dock)
    return dock
  }

  it('on a laptop screen the panel is placed in the dock on the right edge, not inside the page content', async () => {
    const dock = addDock()
    await show()
    await ermitaBox()
    const panel = await within(dock).findByRole('region', { name: 'Ask your own question' })
    expect(dock.contains(panel)).toBe(true)
    for (const box of screen.getAllByRole('article')) expect(box.contains(panel)).toBe(false)
  })

  it('has a button in the toolbar that closes and opens it, and a close button inside it', async () => {
    const user = userEvent.setup()
    const dock = addDock()
    await show()
    await ermitaBox()
    const toggle = screen.getByRole('button', { name: 'Ask a question' })
    expect(toggle).toHaveAttribute('aria-pressed', 'true')

    await user.click(within(dock).getByRole('button', { name: 'Close the question panel' }))
    expect(within(dock).queryByRole('region', { name: 'Ask your own question' })).toBeNull() // the dock is empty again, so it takes no room
    expect(toggle).toHaveAttribute('aria-pressed', 'false')

    await user.click(toggle)
    expect(await within(dock).findByRole('region', { name: 'Ask your own question' })).toBeInTheDocument()
  })

  it('when the panel is closed, a handle stays on screen to open it again, and it goes away once the panel is open', async () => {
    const user = userEvent.setup()
    const dock = addDock()
    await show()
    await ermitaBox()
    expect(screen.queryByRole('button', { name: 'Open the question panel' })).toBeNull() // open: no handle needed

    await user.click(within(dock).getByRole('button', { name: 'Close the question panel' }))
    const handle = await screen.findByRole('button', { name: 'Open the question panel' })
    expect(handle.className).toMatch(/fixed/) // fixed to the window, so it is there wherever the student has scrolled
    expect(handle.parentElement).toBe(document.body)

    await user.click(handle)
    expect(await within(dock).findByRole('region', { name: 'Ask your own question' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open the question panel' })).toBeNull()
  })

  it('on a small screen the handle is there from the start, because the panel starts closed', async () => {
    setScreen(false)
    await show()
    await ermitaBox()
    expect(await screen.findByRole('button', { name: 'Open the question panel' })).toBeInTheDocument()
  })

  it('on a small screen there is no dock: the panel starts closed and opens above the digests', async () => {
    setScreen(false)
    const user = userEvent.setup()
    await show()
    await ermitaBox()
    expect(screen.queryByRole('region', { name: 'Ask your own question' })).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Ask a question' }))
    const panel = await screen.findByRole('region', { name: 'Ask your own question' })
    const firstBox = screen.getAllByRole('article')[0]
    expect(panel.compareDocumentPosition(firstBox) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy() // above the digests
  })

  it('has no toolbar button when there is no case to ask about (synthetic: no boxes)', async () => {
    serve('/uploads/3/document', { ...reviewer, blocks: reviewer.blocks.map((b) => ({ ...b, boxes: [] })), all_ready: true })
    await show(false)
    await screen.findByText('No case boxes yet')
    expect(screen.queryByRole('button', { name: 'Ask a question' })).toBeNull()
  })
})

describe('taking the whole case away', () => {
  it('offers every case of the review as one Word file, and each box offers its own full case', async () => {
    await show()
    const box = await ermitaBox()

    expect(screen.getByRole('link', { name: 'Download all cases (Word)' })).toHaveAttribute('href', '/api/uploads/3/cases.docx')
    expect(screen.getByRole('link', { name: 'Download as Word' })).toHaveAttribute('href', '/api/uploads/3/document.docx')
    expect(within(box).getByRole('link', { name: 'Download the full case' })).toHaveAttribute('href', `/api/cases/${digest.case_id}/document.docx`)
    expect(screen.getByText(/Not happy with a digest\?/)).toBeInTheDocument()
  })
})

