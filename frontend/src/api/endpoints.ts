import { postJson, putJson, query, request } from './client'
import type {
  CaseDetail,
  CatalogBuild,
  CatalogSearch,
  CatalogStatus,
  CaseInsights,
  CasePage,
  Digest,
  FinishedReviewer,
  SearchResult,
  Upload,
  UploadSummary,
} from './types'

export const getUploads = (limit = 20) => request<UploadSummary[]>(`/uploads${query({ limit })}`)

export const getUpload = (id: number) => request<Upload>(`/uploads/${id}`)

export function createUpload(file: File): Promise<Upload> {
  const form = new FormData()
  form.append('file', file)
  return request<Upload>('/uploads', { method: 'POST', body: form })
}

export const deleteUpload = (id: number) => request<void>(`/uploads/${id}`, { method: 'DELETE' })
export const retryUpload = (id: number) => request<Upload>(`/uploads/${id}/retry`, { method: 'POST' })

export const attachLink = (uploadId: number, citationId: number, url: string) =>
  postJson<Upload>(`/uploads/${uploadId}/citations/${citationId}/attach`, { url })

export const searchCases = (grNo: string, year?: number) =>
  request<SearchResult>(`/cases${query({ gr_no: grNo, year })}`)

export const fetchCaseByUrl = (url: string) => postJson<CaseDetail>('/cases/fetch', { url })

export const getLibrary = (params: { q?: string; limit?: number; offset?: number }) =>
  request<CasePage>(`/library/cases${query(params)}`)

export const getCase = (id: number) => request<CaseDetail>(`/cases/${id}`)

export const getInsights = (id: number) => request<CaseInsights>(`/cases/${id}/insights`)


export const searchCatalog = (params: { q: string; year?: number; limit?: number; offset?: number }) =>
  request<CatalogSearch>(`/catalog/search${query(params)}`)

export const getCatalogStatus = () => request<CatalogStatus>('/catalog/status')

export const startCatalogBuild = () => request<CatalogBuild>('/catalog/build', { method: 'POST' })

// -- the finished reviewer and its digests --------------------------------------

export const getFinishedReviewer = (uploadId: number) => request<FinishedReviewer>(`/uploads/${uploadId}/document`)

/** The Word file is a plain download link, not a fetch: the browser saves it. */
export const finishedReviewerDownloadUrl = (uploadId: number) => `/api/uploads/${uploadId}/document.docx`

/** The whole decision as a Word file (the Court's text, footnotes and opinions), and every case a review cites as one file. */
export const caseDownloadUrl = (caseId: number) => `/api/cases/${caseId}/document.docx`
export const reviewCasesDownloadUrl = (uploadId: number) => `/api/uploads/${uploadId}/cases.docx`

export const getDigest = (digestId: number) => request<Digest>(`/digests/${digestId}`)

export const writeDigestField = (digestId: number, key: string, text: string) =>
  putJson<Digest>(`/digests/${digestId}/fields/${key}/text`, { text })

export const pasteDigestField = (digestId: number, key: string, text: string) =>
  postJson<Digest>(`/digests/${digestId}/fields/${key}/paste`, { text })

export const pickDigestPassage = (digestId: number, key: string, first: number, last: number) =>
  putJson<Digest>(`/digests/${digestId}/fields/${key}/passage`, { first, last })

export const resetDigestField = (digestId: number, key: string) =>
  request<Digest>(`/digests/${digestId}/fields/${key}/reset`, { method: 'POST' })

export const askDigestQuestion = (digestId: number, question: string) =>
  postJson<Digest>(`/digests/${digestId}/questions`, { question })

export const regenerateDigestAnswer = (digestId: number, keys: string[]) =>
  postJson<Digest>(`/digests/${digestId}/regenerate`, { keys })
