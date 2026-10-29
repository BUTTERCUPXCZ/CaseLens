import { useEffect, type CSSProperties } from 'react'

/** Shows each [data-reveal] element once its top comes up into the window, and anything already scrolled past (a nav link can
 *  jump over a whole part). Once shown it stays shown. Does nothing unless main.tsx turned the effect on with .js-reveal, so
 *  without it every element is simply visible. */
export function useReveal() {
  useEffect(() => {
    if (!document.documentElement.classList.contains('js-reveal')) return
    let pending = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]:not([data-revealed])'))
    let frame = 0

    const check = () => {
      frame = 0
      const line = window.innerHeight * 0.88
      pending = pending.filter((node) => {
        if (node.getBoundingClientRect().top > line) return true
        node.setAttribute('data-revealed', '')
        return false
      })
      if (pending.length === 0) stop()
    }
    const schedule = () => {
      if (!frame) frame = window.requestAnimationFrame(check)
    }
    const stop = () => {
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }

    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    check()
    return () => {
      stop()
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [])
}

/** The stagger index for the n-th of a group of siblings (read by the CSS as --i). */
export function stagger(i: number) {
  return { '--i': i } as CSSProperties
}
