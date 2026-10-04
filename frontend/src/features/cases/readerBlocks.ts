/** Turns the Court's plain text (one paragraph per line, footnote markers as `[^12]`) into
 *  blocks a reader can scan: caption, party block, section headings, paragraphs, signatures.
 *
 *  Nothing is added, removed or reworded. Each line becomes exactly one block, and only its
 *  styling differs. The rules were written by reading real decisions (GR 180046, 173931,
 *  183905), so they are deliberately simple. */
export type Block =
  | { kind: 'caption'; text: string }
  | { kind: 'parties'; text: string }
  | { kind: 'title'; text: string }
  | { kind: 'ponente'; text: string }
  | { kind: 'heading'; text: string }
  | { kind: 'signature'; text: string }
  | { kind: 'notice'; text: string }
  | { kind: 'paragraph'; text: string }

const SPACED_TITLE = /^(?:[A-Z] ){3,}[A-Z]$/ // "D E C I S I O N"
const SIGNATURE = /\b(?:Associate|Chief) Justice\b/
const END_PUNCTUATION = /[.:;,)"”’]$/
const MIN_FOLLOWING_LINE = 30
const NOT_A_HEADING = /^(?:\(Sgd\.\)|x x x|SO ORDERED|WE CONCUR|By the President)/i

export function toBlocks(fullText: string): Block[] {
  const lines = fullText.split('\n')
  const titleIndex = lines.findIndex((line) => SPACED_TITLE.test(line))
  const blocks: Block[] = []

  lines.forEach((line, index) => {
    if (line.trim() === '') return

    // Everything before the spaced title is the caption; the long line right before it is the parties.
    if (titleIndex >= 0 && index < titleIndex) {
      blocks.push(index === titleIndex - 1 ? { kind: 'parties', text: line } : { kind: 'caption', text: line })
    } else if (index === titleIndex) {
      blocks.push({ kind: 'title', text: line.replace(/ /g, '') })
    } else if (titleIndex >= 0 && index === titleIndex + 1 && /, (?:C\.)?J\.:?$/.test(line)) {
      blocks.push({ kind: 'ponente', text: line })
    } else if (/^(?:C E R T I F I C A T I O N|A T T E S T A T I O N)$/.test(line)) {
      blocks.push({ kind: 'notice', text: line.replace(/ /g, '') })
    } else if (SIGNATURE.test(line) || /^WE CONCUR/i.test(line)) {
      blocks.push({ kind: 'signature', text: line })
    } else if (isHeading(line, lines[index + 1])) {
      blocks.push({ kind: 'heading', text: line })
    } else {
      blocks.push({ kind: 'paragraph', text: line })
    }
  })
  return blocks
}

/** A short line without sentence punctuation that introduces a longer paragraph. */
function isHeading(line: string, next: string | undefined): boolean {
  if (line.length > 80 || END_PUNCTUATION.test(line) || NOT_A_HEADING.test(line)) return false
  if (!/^[A-Z0-9]/.test(line)) return false
  // A real sentence follows (not another short line such as a signature or a name).
  return next !== undefined && next.length >= Math.min(line.length, MIN_FOLLOWING_LINE)
}

/** "…the CHED.[^3] On 19 June" -> text and footnote markers in order. */
export type Piece = { kind: 'text'; text: string } | { kind: 'marker'; number: number }

export function splitMarkers(text: string): Piece[] {
  const pieces: Piece[] = []
  let last = 0
  for (const match of text.matchAll(/\[\^(\d+)\]/g)) {
    if (match.index > last) pieces.push({ kind: 'text', text: text.slice(last, match.index) })
    pieces.push({ kind: 'marker', number: Number(match[1]) })
    last = match.index + match[0].length
  }
  if (last < text.length) pieces.push({ kind: 'text', text: text.slice(last) })
  return pieces
}
