import { useEffect, useState } from 'react'

import { chapters, type ChapterId } from '@/copy'

/** The chapter being read: the last one whose top has passed the upper third of the window. The navbar marks it. */
export function useCurrentChapter(): ChapterId {
  const [current, setCurrent] = useState<ChapterId>(chapters[0].id)

  useEffect(() => {
    const sections = chapters.map((chapter) => document.getElementById(chapter.id)).filter((node): node is HTMLElement => node !== null)
    if (sections.length === 0 || typeof IntersectionObserver === 'undefined') return
    const visible = new Set<string>()
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) visible.add(entry.target.id)
          else visible.delete(entry.target.id)
        }
        const first = sections.find((node) => visible.has(node.id))
        if (first) setCurrent(first.id as ChapterId)
      },
      { rootMargin: '-30% 0px -60% 0px' },
    )
    sections.forEach((node) => observer.observe(node))
    return () => observer.disconnect()
  }, [])

  return current
}
