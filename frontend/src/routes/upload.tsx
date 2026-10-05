import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Search, Upload } from 'lucide-react'
import { z } from 'zod'

import { PageHeader } from '@/components/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { WelcomeCard } from '@/features/guide/WelcomeCard'
import { SearchCasesPanel } from '@/features/upload/SearchCasesPanel'
import { UploadForm } from '@/features/upload/UploadForm'
import { uploadCopy } from '@/lib/copy'

const searchSchema = z.object({ tab: z.enum(['upload', 'search']).optional().catch(undefined) })

export const Route = createFileRoute('/upload')({
  validateSearch: searchSchema,
  component: UploadPage,
})

/** The client's upload screen: Upload file | Search cases, Subject Tags, Topic scope, Generate. The student lands on the review afterwards. */
function UploadPage() {
  const tab = Route.useSearch().tab ?? 'upload'
  const navigate = useNavigate()
  const goToReview = (batchId: number) => void navigate({ to: '/reviews/$batchId', params: { batchId: String(batchId) } })

  return (
    <>
      <PageHeader title={uploadCopy.title} description={uploadCopy.description} />
      <WelcomeCard />
      <div className="max-w-3xl">
        <Tabs value={tab} onValueChange={(next) => void navigate({ to: '/upload', search: { tab: next === 'search' ? 'search' : undefined }, replace: true })}>
          <TabsList>
            <TabsTrigger value="upload">
              <Upload aria-hidden /> {uploadCopy.tabUpload}
            </TabsTrigger>
            <TabsTrigger value="search">
              <Search aria-hidden /> {uploadCopy.tabSearch}
            </TabsTrigger>
          </TabsList>
          <TabsContent value="upload" className="mt-6">
            <UploadForm onStarted={goToReview} />
          </TabsContent>
          <TabsContent value="search" className="mt-6">
            <SearchCasesPanel onStarted={goToReview} />
          </TabsContent>
        </Tabs>
      </div>
    </>
  )
}
