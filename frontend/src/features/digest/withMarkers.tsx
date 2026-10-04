import type { ReactNode } from 'react'

/** The Court's footnote markers arrive as "[^3]". Show them as a small raised 3, like the printed decision. */
export function withMarkers(text: string): ReactNode[] {
  return text.split(/(\[\^\d+\])/g).map((part, index) => {
    const marker = /^\[\^(\d+)\]$/.exec(part)
    return marker ? (
      <sup key={index} className="text-muted-foreground">
        {marker[1]}
      </sup>
    ) : (
      part
    )
  })
}

/** Paragraphs of a field's text, split where the backend joined them (a blank line). */
export function paragraphsOf(text: string): string[] {
  return text.split('\n\n').filter((part) => part.trim() !== '')
}
