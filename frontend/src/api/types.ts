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

/** An upload's case list can be narrowed to the cases whose digest is ready, still being written, or failed. */
export type BatchDigestFilter = 'ready' | 'writing' | 'failed'

/** The desktop app only (its routes are not in the web version's OpenAPI document). */
export type Health = { status: string; database: 'postgresql' | 'sqlite'; desktop?: boolean }
export type AiProviderId = 'groq' | 'deepseek' | 'openrouter' | 'gemini'
export type AiProvider = { id: AiProviderId; name: string; model: string; key_set: boolean; problem?: 'invalid' | 'credit' | null }
export type DesktopSettings = {
  ai_key_set: boolean
  data_dir: string
  restore_pending: boolean
  app_version?: string | null
  ai_out_of_credit?: boolean
  ai_key_invalid?: boolean
  ai_provider?: AiProviderId
  providers?: AiProvider[]
  ai_only_chosen?: boolean
  openrouter_model?: string
  openrouter_models?: { id: string; name: string; free: boolean }[]
}
