import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { UploadDropzone } from '@/features/upload/UploadDropzone'

import { API, http, HttpResponse, server } from '../mocks/server'
import { renderApp } from '../utils'

const pdf = (name = 'sample case.pdf', size = 1000) =>
  new File([new Uint8Array(size)], name, { type: 'application/pdf' })

/** react-dropzone listens for a real drop, so a test drops a file on the zone. */
function dropOnZone(file: File) {
  const zone = screen.getByRole('heading', { name: 'Drop your reviewer here' }).closest('div')!
  fireEvent.drop(zone, { dataTransfer: { files: [file], items: [{ kind: 'file', type: file.type, getAsFile: () => file }], types: ['Files'] } })
}

describe('the drop zone', () => {
  it('shows the one thing to do and how to do it', async () => {
    await renderApp(<UploadDropzone />)
    expect(await screen.findByRole('heading', { name: 'Drop your reviewer here' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Choose a file' })).toBeInTheDocument()
    expect(screen.getByText(/A PDF or Word file, up to 10 MB/)).toBeInTheDocument()
  })

  it('takes a PDF to the results page of the review the backend created', async () => {
    const { router } = await renderApp(<UploadDropzone />)
    await screen.findByRole('heading', { name: 'Drop your reviewer here' })

    dropOnZone(pdf())

    await waitFor(() => expect(router.state.location.pathname).toBe('/reviews/2')) // id 2 is in the real response
  })

  it.each([
    ['a text file', new File(['hello'], 'notes.txt', { type: 'text/plain' }), /We can read PDF and Word/],
    ['a file over 10 MB', pdf('huge.pdf', 10 * 1024 * 1024 + 1), /larger than 10 MB/],
  ])('refuses %s in plain words and never contacts the server', async (_name, file, message) => {
    let contacted = false
    server.use(http.post(`${API}/uploads`, () => ((contacted = true), HttpResponse.json({}))))
    await renderApp(<UploadDropzone />)
    await screen.findByRole('heading', { name: 'Drop your reviewer here' })

    dropOnZone(file)

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(contacted).toBe(false)
  })

  it('explains a scanned PDF the backend cannot read', async () => {
    server.use(
      http.post(`${API}/uploads`, () =>
        HttpResponse.json({ detail: 'PDF has no extractable text (scanned image PDFs are not supported).' }, { status: 422 }),
      ),
    )
    await renderApp(<UploadDropzone />)
    await screen.findByRole('heading', { name: 'Drop your reviewer here' })

    dropOnZone(pdf())

    expect(await screen.findByRole('alert')).toHaveTextContent('looks like a scan')
  })

  it('says so when the server cannot be reached', async () => {
    server.use(http.post(`${API}/uploads`, () => HttpResponse.error()))
    await renderApp(<UploadDropzone />)
    await screen.findByRole('heading', { name: 'Drop your reviewer here' })

    dropOnZone(pdf())

    expect(await screen.findByRole('alert')).toHaveTextContent("can't reach CaseLens")
  })
})
