import { postJson, putJson, query, request } from './client'
import type {
  AiProviderId,
  BatchDigestFilter,
  Bulk,
  BulkItems,
  BulkItemStatus,
  CaseDetail,
  CaseDigest,
  CaseQuestion,
  CaseSummary,
  DesktopSettings,
  DigestLevel,
  Health,
  SubjectChoice,
  SubjectCount,
  CatalogBuild,
  CatalogSearch,
  CaseInsights,
  CasePage,
  SearchResult,
  Upload,
} from './types'

export const getUpload = (id: number) => request<Upload>(`/uploads/${id}`)

export const searchCases = (grNo: string, year?: number) =>
  request<SearchResult>(`/cases${query({ gr_no: grNo, year })}`)

export const fetchCaseByUrl = (url: string) => postJson<CaseDetail>('/cases/fetch', { url })

export const getLibrary = (params: { q?: string; batch_id?: number; digest_state?: BatchDigestFilter; subject_id?: number; no_subject?: boolean; limit?: number; offset?: number }) =>
  request<CasePage>(`/library/cases${query({ ...params, no_subject: params.no_subject ? 'true' : undefined })}`)

/** The filter rail: every subject with how many cases are filed under it, and those with none yet. */
export const getSubjectCounts = () => request<SubjectCount[]>('/library/subjects')
/** The subjects, for a picker. */
export const getSubjectList = () => request<SubjectChoice[]>('/library/subject-list')
/** Set a case's tags (an empty list clears them). Only students label cases. */
export const setCaseSubjects = (caseId: number, subjectIds: number[]) => putJson<CaseSummary>(`/cases/${caseId}/subjects`, { subject_ids: subjectIds })

/** The case digest in the client's format, for a topic scope ("" = the standard digest). State "none" = nobody has asked for it yet. */
export const getCaseDigest = (caseId: number, scope = '', batchId: number | null = null) =>
  request<CaseDigest>(`/cases/${caseId}/case-digest${query({ scope: scope || undefined, batch_id: batchId ?? undefined })}`)
export const requestCaseDigest = (caseId: number, regenerate = false, scope = '', batchId: number | null = null) =>
  request<CaseDigest>(`/cases/${caseId}/case-digest${query({ regenerate: regenerate ? 'true' : undefined, scope: scope || undefined, batch_id: batchId ?? undefined })}`, {
    method: 'POST',
  })
/** The digest as a Word file, a plain download link: the browser saves it. In a review, the student's section edits are in it. */
export const caseDigestDownloadUrl = (caseId: number, level: DigestLevel, scope = '', batchId: number | null = null) =>
  `/api/cases/${caseId}/case-digest.docx${query({ level, scope: scope || undefined, batch_id: batchId ?? undefined })}`
/** The student's own text for one section, kept in their review only (the shared digest is not changed); delete = put back the AI version. */
export const editDigestSection = (batchId: number, digestId: number, section: string, text: string) =>
  putJson<void>(`/bulk/${batchId}/digests/${digestId}/sections/${section}`, { text })
export const putBackDigestSection = (batchId: number, digestId: number, section: string) =>
  request<void>(`/bulk/${batchId}/digests/${digestId}/sections/${section}`, { method: 'DELETE' })

/** Questions asked about a case in the AI assistant panel, in one review (upload). */
export const askAboutCase = (caseId: number, question: string, batchId: number | null) =>
  postJson<CaseQuestion>(`/cases/${caseId}/questions`, { question, batch_id: batchId })
export const getCaseQuestions = (caseId: number, batchId: number | null) => request<CaseQuestion[]>(`/cases/${caseId}/questions${query({ batch_id: batchId ?? undefined })}`)

export const getCase = (id: number) => request<CaseDetail>(`/cases/${id}`)

export const getInsights = (id: number) => request<CaseInsights>(`/cases/${id}/insights`)


export const searchCatalog = (params: { q: string; year?: number; limit?: number; offset?: number }) =>
  request<CatalogSearch>(`/catalog/search${query(params)}`)


export const startCatalogBuild = () => request<CatalogBuild>('/catalog/build', { method: 'POST' })

// -- the finished reviewer and its digests --------------------------------------

/** The whole decision as a Word file (the Court's text, footnotes and opinions), and every case a review cites as one file. */
export const caseDownloadUrl = (caseId: number) => `/api/cases/${caseId}/document.docx`

// -- bulk upload ----------------------------------------------------------------

/** `sourceUrl` (Individual only): the exact Lawphil page picked, so a decision is never swapped for its Resolution with the same number. */
export const startBulk = (text: string, subjectIds: number[], topicScope: string, kind: 'individual' | 'bulk' = 'bulk', sourceUrl?: string) =>
  postJson<Bulk>('/bulk', { text, subject_ids: subjectIds, topic_scope: topicScope, kind, ...(sourceUrl ? { source_url: sourceUrl } : {}) })
/** Decision files, a few at a time (the web host limits one request to about 4 MB). */
export function addBulkFiles(batchId: number, files: File[]): Promise<BulkItems> {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  return request<BulkItems>(`/bulk/${batchId}/files`, { method: 'POST', body: form })
}
export const getBulk = (id: number) => request<Bulk>(`/bulk/${id}`)
export const getBulkItems = (id: number, params: { status?: BulkItemStatus; limit?: number; offset?: number }) =>
  request<BulkItems>(`/bulk/${id}/items${query(params)}`)
export const getRecentBulk = (limit = 10, offset = 0) => request<Bulk[]>(`/bulk${query({ limit, offset })}`)
export const deleteBulk = (id: number) => request<void>(`/bulk/${id}`, { method: 'DELETE' })
export const retryBulk = (id: number) => postJson<{ requeued: number }>(`/bulk/${id}/retry`, {})

export const getHealth = () => request<Health>('/health')

/** The desktop app's Settings: the AI key (never sent back, only whether one is set), backup and restore. */
export const getDesktopSettings = () => request<DesktopSettings>('/desktop/settings')
export const saveAiKey = (key: string, provider: AiProviderId = 'gemini') => putJson<DesktopSettings>('/desktop/ai-key', { key, provider })
export const saveAiProvider = (provider: AiProviderId) => putJson<DesktopSettings>('/desktop/ai-provider', { provider })
export const saveOpenRouterModel = (model: string) => putJson<DesktopSettings>('/desktop/openrouter-model', { model })
export const saveOnlyChosen = (only: boolean) => putJson<DesktopSettings>('/desktop/ai-only-chosen', { only })
export const backupUrl = '/api/desktop/backup'
export function restoreBackup(file: File): Promise<DesktopSettings> {
  const form = new FormData()
  form.append('file', file)
  return request<DesktopSettings>('/desktop/restore', { method: 'POST', body: form })
}
