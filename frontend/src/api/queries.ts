import { queryOptions } from '@tanstack/react-query'

import type { BatchDigestFilter } from './types'

import {
  getBulk,
  getBulkItems,
  getCase,
  getCaseDigest,
  getCaseQuestions,
  getDesktopSettings,
  getAiInfo,
  getHealth,
  getRecentBulk,
  getSubjectCounts,
  getSubjectList,
  getInsights,
  getLibrary,
  getUpload,
  searchCases,
  searchCatalog,
} from './endpoints'

/** While the backend is still fetching from Lawphil, ask again every few seconds. */
export const POLL_MS = 3000
/** A search that is still "pending" after this many answers (about two minutes) is treated as
 *  not found: the backend has had time to look in every nearby month. */
export const MAX_SEARCH_POLLS = 40

export const keys = {
  uploads: ['uploads'] as const,
  upload: (id: number) => ['upload', id] as const,
  library: (q: string, page: number, subject: SubjectFilter) => ['library', q, page, subject] as const,
  batchCases: (id: number, page: number, state: BatchDigestFilter | undefined = undefined, q = '') => ['library', 'batch', id, page, state ?? null, q.trim().toLowerCase()] as const,
  subjects: ['subjects'] as const,
  subjectList: ['subject-list'] as const,
  caseDigest: (id: number, scope = '', batchId: number | null = null) => ['case-digest', id, scope.trim().toLowerCase(), batchId] as const,
  caseQuestions: (id: number, batchId: number | null) => ['case-questions', id, batchId] as const,
  bulk: (id: number) => ['bulk', id] as const,
  bulkItems: (id: number, status: string | undefined, page: number) => ['bulk-items', id, status ?? null, page] as const,
  recentBulk: ['bulk-recent'] as const,
  reviews: (page: number) => ['bulk-recent', page] as const,
  case: (id: number) => ['case', id] as const,
  insights: (id: number) => ['insights', id] as const,
  search: (grNo: string, year: number | undefined) => ['search', grNo, year ?? null] as const,
  catalog: (q: string, year: number | undefined, page: number) => ['catalog', q, year ?? null, page] as const,
  catalogStatus: ['catalog-status'] as const,
  finishedReviewer: (uploadId: number) => ['finished-reviewer', uploadId] as const,
  digest: (id: number) => ['digest', id] as const,
  health: ['health'] as const,
  aiInfo: ['ai-info'] as const,
  desktopSettings: ['desktop-settings'] as const,
}

/** Polls while any citation is still being checked, and stops by itself when it is done. */
export const uploadQuery = (id: number) =>
  queryOptions({
    queryKey: keys.upload(id),
    queryFn: () => getUpload(id),
    refetchInterval: (query) => (query.state.data?.status === 'processing' ? POLL_MS : false),
  })

export const PAGE_SIZE = 20

/** Which subject the library shows: every case, the cases with no subject yet ("none"), or one subject by its id. */
export type SubjectFilter = number | 'none' | undefined

export const libraryQuery = (q: string, page: number, subject: SubjectFilter = undefined) =>
  queryOptions({
    queryKey: keys.library(q, page, subject),
    queryFn: () =>
      getLibrary({
        q,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        subject_id: typeof subject === 'number' ? subject : undefined,
        no_subject: subject === 'none' ? true : undefined,
      }),
    placeholderData: (previous) => previous, // keep the old rows on screen while the next page loads
  })

/** The filter rail's subjects with their counts. */
export const subjectCountsQuery = () => queryOptions({ queryKey: keys.subjects, queryFn: getSubjectCounts, staleTime: 15_000 })
/** The subjects for a picker (they hardly ever change). */
export const subjectListQuery = () => queryOptions({ queryKey: keys.subjectList, queryFn: getSubjectList, staleTime: Infinity })

/** The case digest. While it is being written, ask again every few seconds; it stops by itself when it is ready or has failed. */
export const CASE_DIGEST_POLL_MS = 4000
export const caseDigestQuery = (id: number, scope = '', batchId: number | null = null) =>
  queryOptions({
    queryKey: keys.caseDigest(id, scope, batchId),
    queryFn: () => getCaseDigest(id, scope, batchId),
    refetchInterval: (query) => (query.state.data?.state === 'pending' ? CASE_DIGEST_POLL_MS : false),
  })

/** The questions asked about a case in one review; asked again every few seconds while one is being answered. */
export const QUESTION_POLL_MS = 2500
export const caseQuestionsQuery = (id: number, batchId: number | null) =>
  queryOptions({
    queryKey: keys.caseQuestions(id, batchId),
    queryFn: () => getCaseQuestions(id, batchId),
    refetchInterval: (query) => (query.state.data?.some((q) => q.state === 'pending') ? QUESTION_POLL_MS : false),
  })

export const caseQuery = (id: number) =>
  queryOptions({ queryKey: keys.case(id), queryFn: () => getCase(id), staleTime: Infinity })

export const insightsQuery = (id: number) =>
  queryOptions({ queryKey: keys.insights(id), queryFn: () => getInsights(id), staleTime: Infinity })


/** A G.R. search the backend may still be working on ("pending"): keep asking until it is found. */
export const searchQuery = (grNo: string, year: number | undefined) =>
  queryOptions({
    queryKey: keys.search(grNo, year),
    queryFn: () => searchCases(grNo, year),
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' && query.state.dataUpdateCount < MAX_SEARCH_POLLS ? POLL_MS : false,
    staleTime: 0,
  })

export const CATALOG_PAGE_SIZE = 20
/** While the case list is still being prepared, check its progress this often. */
export const CATALOG_POLL_MS = 4000

/** Search by case name or G.R. number. While the case list is being prepared the results (and the
 *  progress shown with them) are refreshed, so what the student sees grows without reloading. */
export const catalogSearchQuery = (q: string, year: number | undefined, page: number) =>
  queryOptions({
    queryKey: keys.catalog(q, year, page),
    queryFn: () => searchCatalog({ q, year, limit: CATALOG_PAGE_SIZE, offset: page * CATALOG_PAGE_SIZE }),
    placeholderData: (previous) => previous,
    refetchInterval: (query) => (query.state.data?.catalog.state === 'building' ? CATALOG_POLL_MS : false),
  })

/** A bulk upload's progress: asked again while anything is waiting for Lawphil or its digest is being written. */
export const BULK_POLL_MS = 3000
export const bulkQuery = (id: number) =>
  queryOptions({
    queryKey: keys.bulk(id),
    queryFn: () => getBulk(id),
    refetchInterval: (query) => {
      const bulk = query.state.data
      return !bulk || !bulk.finished || bulk.counts.digests_pending > 0 ? BULK_POLL_MS : false
    },
  })

export const BULK_PAGE_SIZE = 25
export const bulkItemsQuery = (id: number, status: string | undefined, page: number, live: boolean) =>
  queryOptions({
    queryKey: keys.bulkItems(id, status, page),
    queryFn: () => getBulkItems(id, { status: status as never, limit: BULK_PAGE_SIZE, offset: page * BULK_PAGE_SIZE }),
    refetchInterval: live ? BULK_POLL_MS : false,
    placeholderData: (previous) => previous,
  })

/** What a bulk upload gave: its main cases, each once. Asked again while the upload or its digests are still being worked on. */
export const batchCasesQuery = (id: number, page: number, live: boolean, state?: BatchDigestFilter, q = '') =>
  queryOptions({
    queryKey: keys.batchCases(id, page, state, q),
    queryFn: () => getLibrary({ batch_id: id, digest_state: state, q: q.trim() || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    refetchInterval: live ? BULK_POLL_MS : false,
    placeholderData: (previous) => previous,
  })

/** "My uploads": the uploads, newest first, a page at a time. Asked again while any is still being worked on. */
export const REVIEWS_PAGE_SIZE = 20
export const reviewsQuery = (page: number) =>
  queryOptions({
    queryKey: keys.reviews(page),
    queryFn: () => getRecentBulk(REVIEWS_PAGE_SIZE, page * REVIEWS_PAGE_SIZE),
    placeholderData: (previous) => previous,
    refetchInterval: (query) => (query.state.data?.some((b) => !b.finished || b.counts.digests_pending > 0) ? BULK_POLL_MS : false),
  })

/** Which kind of CaseLens this is (the website or the desktop app). It never changes while the app runs. */
export const healthQuery = () => queryOptions({ queryKey: keys.health, queryFn: getHealth, staleTime: Infinity })

export const aiInfoQuery = () => queryOptions({ queryKey: keys.aiInfo, queryFn: getAiInfo })

export const desktopSettingsQuery = () => queryOptions({ queryKey: keys.desktopSettings, queryFn: getDesktopSettings })
