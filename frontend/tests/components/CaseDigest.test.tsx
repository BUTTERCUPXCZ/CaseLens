import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { CaseDigest } from '@/api/types'
import { CaseDigestView } from '@/features/digest/CaseDigestView'

import marcos from '../fixtures/api/case-digest-marcos.json'
import pending from '../fixtures/api/case-digest-pending.json'
import { renderApp } from '../utils'

// The real digest of Marcos v. Manglapus, as the backend gave it (the AI run of 5 October 2026).
const digest = marcos as unknown as CaseDigest

const show = (value: CaseDigest = digest, onRewrite = () => undefined, rewriting = false) =>
  renderApp(<CaseDigestView digest={value} onRewrite={onRewrite} rewriting={rewriting} />)

describe('the case digest in the client’s format', () => {
  it('starts like the client’s sample: the case, its citation, the topic and the ponente', async () => {
    await show()
    expect(screen.getByRole('heading', { level: 2, name: 'Marcos v. Manglapus' })).toBeInTheDocument()
    expect(screen.getByText('G.R. No. 88211, September 15, 1989 (En Banc)')).toBeInTheDocument()
    expect(screen.getByText(/Topic: Constitutional Law/)).toHaveTextContent('Ponente: Cortes, J.')
  })

  it('shows the sections in the client’s order', async () => {
    await show()
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual([
      'Doctrine', 'Facts', 'Petitioners’ arguments', 'Respondents’ arguments', 'Issue', 'Ruling',
      'Ratio Decidendi', 'The Dissents (useful for recitation)', 'Topic Explained', 'Why This Case Matters',
    ])
  })

  it('prints a list as bullets, and a block’s own heading as a subheading (the numbered reasoning, each justice)', async () => {
    await show()
    const arguments_ = screen.getByRole('region', { name: 'Petitioners’ arguments' })
    expect(within(arguments_).getAllByRole('listitem').length).toBeGreaterThanOrEqual(3)
    const ratio = screen.getByRole('region', { name: 'Ratio Decidendi' })
    expect(within(ratio).getAllByRole('heading', { level: 4 })[0]).toHaveTextContent(/^1\. /)
    const dissents = screen.getByRole('region', { name: 'The Dissents (useful for recitation)' })
    expect(within(dissents).getAllByRole('heading', { level: 4 }).map((h) => h.textContent)).toEqual(
      expect.arrayContaining([expect.stringMatching(/Cruz|CRUZ/), expect.stringMatching(/Sarmiento|SARMIENTO/)]),
    )
  })

  it('says under every block which paragraphs of the decision it rests on, and names a separate opinion plainly', async () => {
    await show()
    const ruling = screen.getByRole('region', { name: 'Ruling' })
    expect(within(ruling).getByText(/^Based on decision paragraphs? \d/)).toBeInTheDocument()
    const dissents = screen.getByRole('region', { name: 'The Dissents (useful for recitation)' })
    expect(within(dissents).getAllByText(/Also based on a separate opinion/).length).toBeGreaterThan(0)
  })

  it('offers the three downloads of the drawing for this case, and "Write it again"', async () => {
    const user = userEvent.setup()
    const onRewrite = vi.fn()
    await show(digest, onRewrite)
    expect(screen.getByRole('link', { name: 'Facts and Doctrine' })).toHaveAttribute('href', '/api/cases/23/case-digest.docx?level=short')
    expect(screen.getByRole('link', { name: 'Doctrine, Facts, Issue, Ruling' })).toHaveAttribute('href', '/api/cases/23/case-digest.docx?level=standard')
    expect(screen.getByRole('link', { name: 'Full case digest' })).toHaveAttribute('href', '/api/cases/23/case-digest.docx?level=full')
    await user.click(screen.getByRole('button', { name: 'Write it again' }))
    expect(onRewrite).toHaveBeenCalledOnce()
  })

  it('always says it is a draft to check, and how many sentences the checks kept out', async () => {
    await show()
    expect(screen.getByText('Drafted from the decision. Check it.')).toBeInTheDocument()
    expect(screen.getByText(/left out because the decision did not support/)).toBeInTheDocument()
  })

  it('says it is being written when the digest is pending, and never offers a Word file of nothing', async () => {
    await show(pending as unknown as CaseDigest)
    expect(within(screen.getByRole('article', { name: 'Case digest' })).getByRole('status')).toHaveTextContent('Writing the digest…')
    expect(screen.getByText('The decision did not give enough to write this digest.')).toBeInTheDocument()
  })

  it('keeps showing an older digest while a new one is being written (synthetic: the real digest, pending again)', async () => {
    await show({ ...digest, state: 'pending' }, () => undefined, true)
    expect(screen.getByRole('region', { name: 'Doctrine' })).toBeInTheDocument()
    expect(within(screen.getByRole('article', { name: 'Case digest' })).getByRole('status')).toHaveTextContent('Writing the digest…')
    expect(screen.getByRole('button', { name: 'Write it again' })).toBeDisabled()
  })
})

describe('editing a section in a review (the real Marcos digest)', () => {
  const editing = () => ({ save: vi.fn().mockResolvedValue(undefined), putBack: vi.fn().mockResolvedValue(undefined), busy: false })

  it('starts from the section’s own text and saves what the student typed', async () => {
    const user = userEvent.setup()
    const edit = editing()
    await renderApp(<CaseDigestView digest={marcos as unknown as CaseDigest} onRewrite={() => undefined} rewriting={false} batchId={3} editing={edit} />)
    await user.click(screen.getByRole('button', { name: 'Edit Facts' }))
    const box = screen.getByLabelText('Your text for Facts')
    expect((box as HTMLTextAreaElement).value).toBe((marcos as unknown as CaseDigest).sections.find((s) => s.key === 'facts')!.text)
    await user.clear(box)
    await user.type(box, 'My own facts.')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(edit.save).toHaveBeenCalledWith('facts', 'My own facts.')
    expect(screen.queryByLabelText('Your text for Facts')).not.toBeInTheDocument() // back to reading
  })

  it('marks an edited section, drops its paragraph line, and can put back the AI version', async () => {
    const user = userEvent.setup()
    const edit = editing()
    const base = marcos as unknown as CaseDigest
    const edited = { ...base, sections: base.sections.map((s) => (s.key === 'doctrine' ? { ...s, edited: true, blocks: [{ heading: null, as_list: false, sentences: [{ text: 'My doctrine.', key: false, cites: [] }] }], text: 'My doctrine.' } : s)) }
    await renderApp(<CaseDigestView digest={edited} onRewrite={() => undefined} rewriting={false} batchId={3} editing={edit} />)
    const doctrine = screen.getByRole('region', { name: /Doctrine/ })
    expect(within(doctrine).getByText('Edited by you')).toBeInTheDocument()
    expect(within(doctrine).queryByText(/Based on decision paragraph/)).not.toBeInTheDocument()
    await user.click(within(doctrine).getByRole('button', { name: 'Put back the AI version' }))
    expect(edit.putBack).toHaveBeenCalledWith('doctrine')
  })

  it('offers no editing outside a review', async () => {
    await renderApp(<CaseDigestView digest={marcos as unknown as CaseDigest} onRewrite={() => undefined} rewriting={false} />)
    expect(screen.queryByRole('button', { name: /^Edit / })).not.toBeInTheDocument()
  })

  it('links the Word downloads to the review so they include the student’s edits', async () => {
    await renderApp(<CaseDigestView digest={marcos as unknown as CaseDigest} onRewrite={() => undefined} rewriting={false} batchId={3} editing={editing()} />)
    expect(screen.getByRole('link', { name: /Full case digest/ }).getAttribute('href')).toContain('batch_id=3')
  })
})
