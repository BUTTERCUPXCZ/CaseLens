import { queryOptions } from '@tanstack/react-query'

import {
  getCase,
  getCatalogStatus,
  getDigest,
  getFinishedReviewer,
  getInsights,
  getLibrary,
  getUpload,
  getUploads,
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
  library: (q: string, page: number) => ['library', q, page] as const,
  case: (id: number) => ['case', id] as const,
  insights: (id: number) => ['insights', id] as const,
  search: (grNo: string, year: number | undefined) => ['search', grNo, year ?? null] as const,
  catalog: (q: string, year: number | undefined, page: number) => ['catalog', q, year ?? null, page] as const,
  catalogStatus: ['catalog-status'] as const,
  finishedReviewer: (uploadId: number) => ['finished-reviewer', uploadId] as const,
  digest: (id: number) => ['digest', id] as const,
}

export const uploadsQuery = (limit = 20) =>
  queryOptions({ queryKey: [...keys.uploads, limit], queryFn: () => getUploads(limit) })

/** Polls while any citation is still being checked, and stops by itself when it is done. */
export const uploadQuery = (id: number) =>
  queryOptions({
    queryKey: keys.upload(id),
    queryFn: () => getUpload(id),
    refetchInterval: (query) => (query.state.data?.status === 'processing' ? POLL_MS : false),
  })

export const PAGE_SIZE = 20

export const libraryQuery = (q: string, page: number) =>
  queryOptions({
    queryKey: keys.library(q, page),
    queryFn: () => getLibrary({ q, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    placeholderData: (previous) => previous, // keep the old rows on screen while the next page loads
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

export const catalogStatusQuery = () =>
  queryOptions({
    queryKey: keys.catalogStatus,
    queryFn: getCatalogStatus,
    refetchInterval: (query) => (query.state.data?.state === 'building' ? CATALOG_POLL_MS : false),
  })

/** The reviewer with its digest boxes in place. Asks again while any box is still being written. */
export const finishedReviewerQuery = (uploadId: number) =>
  queryOptions({
    queryKey: keys.finishedReviewer(uploadId),
    queryFn: () => getFinishedReviewer(uploadId),
    refetchInterval: (query) => (query.state.data && !query.state.data.all_ready ? POLL_MS : false),
  })

/** One digest box. Asks again while its Court text is final but an explanation is still being written. */
export const digestQuery = (id: number) =>
  queryOptions({
    queryKey: keys.digest(id),
    queryFn: () => getDigest(id),
    refetchInterval: (query) => {
      const digest = query.state.data
      return digest && (digest.status === 'pending' || digest.fields.some((f) => f.state === 'pending')) ? POLL_MS : false
    },
  })
