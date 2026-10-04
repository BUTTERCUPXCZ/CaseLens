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
export type Trends = Schemas['TrendsOut']
export type SearchResult = Schemas['SearchOut']
export type Attribution = Schemas['Attribution']
export type CatalogSearch = Schemas['CatalogSearchOut']
export type CatalogItem = Schemas['CatalogItemOut']
export type CatalogStatus = Schemas['CatalogStatusOut']
export type CatalogBuild = Schemas['CatalogBuildOut']
export type FinishedReviewer = Schemas['FinishedReviewerOut']
export type ReviewerBlock = Schemas['BlockOut']
export type BoxRef = Schemas['BoxRefOut']
export type Digest = Schemas['DigestOut']
export type DigestField = Schemas['DigestFieldOut']
export type DigestFieldOrigin = DigestField['origin']
