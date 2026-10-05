/** The web host (Vercel) accepts about 4.5 MB per request, so files go a few at a time: at most `maxFiles` and about `maxBytes` per request.
 *  A file that is bigger than `maxBytes` on its own goes alone. Order is kept, so the batch lists the files as the student chose them. */
export function chunkFiles(files: File[], maxFiles = 10, maxBytes = 3_500_000): File[][] {
  const chunks: File[][] = []
  let current: File[] = []
  let size = 0
  for (const file of files) {
    if (current.length > 0 && (current.length >= maxFiles || size + file.size > maxBytes)) {
      chunks.push(current)
      current = []
      size = 0
    }
    current.push(file)
    size += file.size
  }
  if (current.length > 0) chunks.push(current)
  return chunks
}
