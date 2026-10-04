import { afterEach, describe, expect, it } from 'vitest'

import { setTheme } from '@/lib/theme'

afterEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('dark')
})

describe('the theme the student picks', () => {
  it('switches the page and is remembered', () => {
    setTheme('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('caselens-theme')).toBe('dark')

    setTheme('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('caselens-theme')).toBe('light')
  })
})
