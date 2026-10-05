import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { SubjectTags } from '@/features/upload/SubjectTags'
import { TopicScope } from '@/features/upload/TopicScope'
import { UploadForm } from '@/features/upload/UploadForm'

import progress from '../fixtures/api/bulk-progress.json'
import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

const pdf = (name: string, bytes = 43_200) => new File([new Uint8Array(bytes)], name, { type: 'application/pdf' })

describe('Subject Tags: the student labels the case', () => {
  it('shows the client’s eleven chips, several can be picked, and says how many are selected', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    const { unmount } = await renderApp(<SubjectTags value={[]} onChange={onChange} />)
    const group = await screen.findByRole('group', { name: 'Subject Tags (optional)' })
    expect(await within(group).findAllByRole('button')).toHaveLength(11)
    expect(within(group).getByText('No subject selected')).toBeInTheDocument()
    await user.click(within(group).getByRole('button', { name: 'Constitutional Law' }))
    expect(onChange).toHaveBeenLastCalledWith([4])

    unmount()
    await renderApp(<SubjectTags value={[4, 9]} onChange={onChange} />)
    expect(await screen.findByRole('button', { name: 'Constitutional Law' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Political Law' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('2 subjects selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Constitutional Law' }))
    expect(onChange).toHaveBeenLastCalledWith([9]) // pressing a chosen tag removes it
  })
})

describe('Topic scope', () => {
  it('counts up to 300 characters and offers the example', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    await renderApp(<TopicScope value="Presidential powers" onChange={onChange} />)
    expect(screen.getByLabelText('Topic scope')).toHaveAttribute('maxLength', '300')
    expect(screen.getByText('19/300')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Use the example/ }))
    expect(onChange).toHaveBeenCalledWith('Family Code under Conjugal Partnership of Gains')
  })
})

describe('the upload screen', () => {
  it('lists the files chosen, sends the tags and scope once for the whole upload, then the files in small groups, and opens the review', async () => {
    const user = userEvent.setup()
    let started: unknown
    let fileRequests = 0
    server.use(
      http.post(`${API}/bulk`, async ({ request }) => {
        started = await request.json()
        return HttpResponse.json(progress, { status: 201 })
      }),
      http.post(`${API}/bulk/:id/files`, () => {
        fileRequests += 1
        return HttpResponse.json({ items: [], total: 0 }, { status: 202 })
      }),
    )
    const onStarted = vi.fn()
    await renderApp(<UploadForm onStarted={onStarted} />)
    const many = Array.from({ length: 12 }, (_, i) => pdf(`case-${i}.pdf`))
    await user.upload(screen.getByLabelText('Decision files (PDF or Word)'), many)
    expect(within(screen.getByRole('list', { name: 'Files to upload' })).getAllByRole('listitem')).toHaveLength(12)
    expect(screen.getAllByText('42.2 KB')).toHaveLength(12)

    await user.click(screen.getByRole('button', { name: 'Remove case-0.pdf' }))
    await user.click(await screen.findByRole('button', { name: 'Constitutional Law' }))
    await user.type(screen.getByLabelText('Topic scope'), 'Presidential powers')
    await user.click(screen.getByRole('button', { name: 'Generate case digests' }))

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(progress.id))
    expect(started).toEqual({ text: '', subject_ids: [4], topic_scope: 'Presidential powers', kind: 'bulk' })
    expect(fileRequests).toBe(2) // 11 files: 10, then 1
  })

  it('takes G.R. numbers instead of files, and asks for something before starting', async () => {
    const user = userEvent.setup()
    let started: unknown
    server.use(http.post(`${API}/bulk`, async ({ request }) => ((started = await request.json()), HttpResponse.json(progress, { status: 201 }))))
    const onStarted = vi.fn()
    await renderApp(<UploadForm onStarted={onStarted} />)
    await user.click(screen.getByRole('button', { name: 'Generate case digests' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Add a file, or a G.R. number, first.')

    await user.click(screen.getByRole('button', { name: 'Have G.R. numbers instead?' }))
    await user.type(screen.getByLabelText('G.R. numbers'), '88211')
    await user.click(screen.getByRole('button', { name: 'Generate case digests' }))
    await waitFor(() => expect(onStarted).toHaveBeenCalled())
    expect(started).toEqual({ text: '88211', subject_ids: [], topic_scope: '', kind: 'bulk' })
  })

  it('says how long it takes, without promising more than it does', async () => {
    await renderApp(<UploadForm onStarted={() => undefined} />)
    expect(screen.getByText(/about 3 to 5 minutes per case/)).toBeInTheDocument()
    expect(screen.queryByText(/flashcard|quiz/i)).not.toBeInTheDocument()
  })
})

describe('Individual: one case, its full text, and what subject it is', () => {
  it('finds the case on Lawphil, chooses it, and opens it as one case with its subject', async () => {
    const user = userEvent.setup()
    const { IndividualForm } = await import('@/features/upload/IndividualForm')
    let started: unknown
    server.use(http.post(`${API}/bulk`, async ({ request }) => ((started = await request.json()), HttpResponse.json(progress, { status: 201 }))))
    const onStarted = vi.fn()
    await renderApp(<IndividualForm onStarted={onStarted} />)

    await user.click(screen.getByRole('button', { name: 'Open the case' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose a case first') // nothing chosen yet

    await user.type(screen.getByLabelText('Find a case by name or G.R. number'), 'Ermita')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    const choose = (await screen.findAllByRole('button', { name: /^Choose / }))[0]!
    await user.click(choose)
    expect(choose).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText(/^Your case: /)).toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: 'Constitutional Law' }))
    await user.click(screen.getByRole('button', { name: 'Open the case' }))
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(progress.id))
    expect(started).toMatchObject({ kind: 'individual', subject_ids: [4], topic_scope: '' })
    expect((started as { text: string }).text).toMatch(/^\d+ \(\d{4}\)$/) // the case's G.R. number with its year
  })

  it('opens one uploaded file as the case', async () => {
    const user = userEvent.setup()
    const { IndividualForm } = await import('@/features/upload/IndividualForm')
    let files = 0
    server.use(
      http.post(`${API}/bulk`, () => HttpResponse.json(progress, { status: 201 })),
      http.post(`${API}/bulk/:id/files`, () => ((files += 1), HttpResponse.json({ items: [], total: 0 }, { status: 202 }))),
    )
    const onStarted = vi.fn()
    await renderApp(<IndividualForm onStarted={onStarted} />)
    await user.click(screen.getByRole('tab', { name: 'Upload the file' }))
    await user.upload(screen.getByLabelText('The case file (PDF or Word)'), pdf('marcos.pdf'))
    expect(screen.getByText('marcos.pdf')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open the case' }))
    await waitFor(() => expect(onStarted).toHaveBeenCalled())
    expect(files).toBe(1)
  })
})
