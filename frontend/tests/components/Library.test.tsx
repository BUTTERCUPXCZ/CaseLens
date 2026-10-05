import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { CaseSummary, SubjectCount } from '@/api/types'
import { LibraryTable } from '@/features/library/LibraryTable'
import { SubjectRail } from '@/features/library/SubjectRail'

import library from '../fixtures/api/library.json'
import subjects from '../fixtures/api/library-subjects.json'
import { renderApp } from '../utils'

const cases = library.items as unknown as CaseSummary[]
const rail = subjects as SubjectCount[]

describe('the table of the drawing (Case | G.R. No., date and ponente | View / Download)', () => {
  it('has exactly the three columns the client drew', async () => {
    await renderApp(<LibraryTable cases={cases} />)
    expect(screen.getAllByRole('columnheader').map((th) => th.textContent)).toEqual(['Case', 'G.R. No., date and ponente', 'View / Download'])
  })

  it('shows one readable row per case with its numbers, date, ponente and subject (real saved cases)', async () => {
    await renderApp(<LibraryTable cases={cases} />)
    const row = screen.getByRole('link', { name: 'Aquilino Pimentel III et al.' }).closest('tr')!
    expect(within(row).getByText('G.R. No. 274778')).toBeInTheDocument()
    expect(within(row).getByText(/December 3, 2025 · Lazaro-Javier, J\./)).toBeInTheDocument()
    expect(within(row).getByText('Constitutional Law')).toBeInTheDocument() // the subject the case is filed under
  })

  it('says every number a joint decision settles, and "No subject yet" when none is chosen', async () => {
    await renderApp(<LibraryTable cases={cases} />)
    const row = screen.getByRole('link', { name: 'Walden F. Bello et al. v. Commission on Elections' }).closest('tr')!
    expect(within(row).getByText('G.R. Nos. 191998, 192769, 192832')).toBeInTheDocument()
    expect(within(row).getByText('No subject yet')).toBeInTheDocument()
  })

  it('links View to the case digest and to the full text, by case, with the case named for a screen reader', async () => {
    await renderApp(<LibraryTable cases={cases} />)
    const row = screen.getByRole('link', { name: 'Aquilino Pimentel III et al.' }).closest('tr')!
    expect(within(row).getByRole('link', { name: /Case digest of Aquilino Pimentel III et al\./ })).toHaveAttribute('href', '/cases/7/digest')
    expect(within(row).getByRole('link', { name: /Full text of Aquilino Pimentel III et al\./ })).toHaveAttribute('href', '/cases/7/decision')
  })

  it('offers the three download options of the drawing when the digest is written', async () => {
    const user = userEvent.setup()
    const ready = cases.map((c) => (c.id === 7 ? { ...c, digest_ready: true } : c)) // synthetic: the real list with one digest written
    await renderApp(<LibraryTable cases={ready} />)
    await user.click(screen.getByRole('button', { name: 'Download: Aquilino Pimentel III et al.' }))

    expect(await screen.findByRole('link', { name: /Facts and Doctrine/ })).toHaveAttribute('href', '/api/cases/7/case-digest.docx?level=short')
    expect(screen.getByRole('link', { name: /Doctrine, Facts, Issue, Ruling.*1 to 2 pages/ })).toHaveAttribute('href', '/api/cases/7/case-digest.docx?level=standard')
    expect(screen.getByRole('link', { name: /Full case digest.*about 6 pages/ })).toHaveAttribute('href', '/api/cases/7/case-digest.docx?level=full')
    expect(screen.getByRole('link', { name: /Full text of the decision/ })).toHaveAttribute('href', '/api/cases/7/document.docx')
  })

  it('does not offer a file that does not exist yet: it points to writing the digest first', async () => {
    const user = userEvent.setup()
    await renderApp(<LibraryTable cases={cases} />) // none of the real cases has a digest
    await user.click(screen.getByRole('button', { name: 'Download: Aquilino Pimentel III et al.' }))
    expect(await screen.findByText('Write the digest first, then download it.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Full case digest/ })).not.toBeInTheDocument()
  })
})

describe('the subject filter on the left', () => {
  it('lists every subject with its count, All cases first, and hides "No subject yet" when there is none', async () => {
    await renderApp(<SubjectRail counts={rail} selected={undefined} onSelect={() => undefined} />)
    const nav = screen.getByRole('navigation', { name: 'Filter by subject' })
    const names = within(nav).getAllByRole('button').map((b) => b.textContent)
    expect(names[0]).toBe('All cases8')
    expect(names).toContain('Constitutional Law2')
    expect(names).toContain('No subject yet2')

    const none = rail.map((s) => (s.subject_id === null ? { ...s, count: 0 } : s)) // synthetic: nothing without a subject
    const { unmount } = await renderApp(<SubjectRail counts={none} selected={undefined} onSelect={() => undefined} />)
    expect(within(screen.getAllByRole('navigation', { name: 'Filter by subject' }).at(-1)!).queryByText('No subject yet')).not.toBeInTheDocument()
    unmount()
  })

  it('marks the chosen subject and reports a click (a subject, "none", or all)', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    await renderApp(<SubjectRail counts={rail} selected={4} onSelect={onSelect} />)
    const nav = screen.getByRole('navigation', { name: 'Filter by subject' })
    expect(within(nav).getByRole('button', { name: /Constitutional Law/ })).toHaveAttribute('aria-pressed', 'true')

    await user.click(within(nav).getByRole('button', { name: /Labor Law/ }))
    await user.click(within(nav).getByRole('button', { name: /No subject yet/ }))
    await user.click(within(nav).getByRole('button', { name: /All cases/ }))
    expect(onSelect.mock.calls.map((c) => c[0])).toEqual([5, 'none', undefined])
  })

  it('is a list to choose from on a phone', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    await renderApp(<SubjectRail counts={rail} selected={undefined} onSelect={onSelect} />)
    await user.selectOptions(screen.getByLabelText('Filter by subject', { selector: 'select' }), 'Remedial Law (1)')
    expect(onSelect).toHaveBeenCalledWith(3)
  })
})

describe('decisions on Lawphil that are not saved yet, found from the library search', () => {
  it('lists the unsaved matches under the saved ones, each with a button that saves it, and leaves out the saved ones (real catalog answer)', async () => {
    const { LawphilMatches } = await import('@/features/library/LawphilMatches')
    await renderApp(<LawphilMatches q="Ermita" />)
    const region = await screen.findByRole('region', { name: 'Also on Lawphil, not saved yet' })
    expect(within(region).getByText(/not in your library yet/)).toBeInTheDocument()
    expect(within(region).getAllByRole('button', { name: 'Open this case' }).length).toBeGreaterThan(0)
    expect(within(region).queryByText('In your library')).not.toBeInTheDocument()
  })

  it('says so when nothing else matches', async () => {
    const { server, http, HttpResponse, API } = await import('../mocks/server')
    const empty = (await import('../fixtures/api/catalog-search-empty.json')).default
    server.use(http.get(`${API}/catalog/search`, () => HttpResponse.json(empty)))
    const { LawphilMatches } = await import('@/features/library/LawphilMatches')
    await renderApp(<LawphilMatches q="zzzzqq" />)
    expect(await screen.findByText('Nothing else on Lawphil’s list matches.')).toBeInTheDocument()
  })
})
