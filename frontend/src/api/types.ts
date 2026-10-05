/** Friendly names for the shapes generated from the backend's OpenAPI document (schema.d.ts).
 *  Regenerate that file with `npm run api:types` when the backend changes. */
import type { components } from './schema'

type Schemas = components['schemas']

export type Upload = Schemas['UploadOut']
export type UploadSummary = Schemas['UploadSummaryOut']
export type Citation = Schemas['CitationOut']
export type CitationStatus = Citation['status']
export type Mismatch = Schemas['MismatchOut']

export type CaseSummary = Schemas['CaseSummaryOut']
export type CaseDetail = Schemas['CaseDetailOut']
export type CasePage = Schemas['CasePageOut']
export type Disposition = CaseSummary['disposition']
export type Footnote = Schemas['FootnoteOut']
export type CaseInsights = Schemas['InsightsOut']
export type SearchResult = Schemas['SearchOut']
export type Attribution = Schemas['Attribution']
export type CatalogSearch = Schemas['CatalogSearchOut']
export type CatalogItem = Schemas['CatalogItemOut']
export type CatalogStatus = Schemas['CatalogStatusOut']
export type CatalogBuild = Schemas['CatalogBuildOut']
export type FinishedReviewer = Schemas['FinishedReviewerOut']
export type Digest = Schemas['DigestOut']
export type DigestField = Schemas['DigestFieldOut']

export type SubjectCount = Schemas['SubjectCountOut']
export type SubjectChoice = Schemas['SubjectOut']
export type CaseDigest = Schemas['CaseDigestOut']
export type DigestBlock = Schemas['DigestBlockOut']
export type DigestLevel = 'short' | 'standard' | 'full'

export type Bulk = Schemas['BulkOut']
export type BulkItem = Schemas['BulkItemOut']
export type BulkItems = Schemas['BulkItemsOut']
export type BulkItemStatus = BulkItem['status']
export type CaseQuestion = Schemas['QuestionOut']
