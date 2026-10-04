import { describe, expect, it } from 'vitest'

import { lawphilLinkSchema } from '@/features/reviews/lawphilLink'

const accepts = (url: string) => lawphilLinkSchema.safeParse({ url }).success

describe('the Lawphil link a student pastes', () => {
  it('accepts the real address of GR 180046', () => {
    expect(accepts('https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html')).toBe(true)
    expect(accepts('  https://www.lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html  ')).toBe(true)
  })

  it.each([
    ['', 'nothing pasted'],
    ['https://example.com/judjuris/a.html', 'another site'],
    ['http://lawphil.net/judjuris/a.html', 'not https'],
    ['https://lawphil.net/judjuris/a.pdf', 'not a case page'],
    ['https://lawphil.net.evil.com/judjuris/a.html', 'a look-alike address'],
    ['lawphil.net/judjuris/a.html', 'no scheme'],
  ])('refuses %j (%s)', (url) => {
    expect(accepts(url)).toBe(false)
  })

  it('says what is wrong in plain words', () => {
    const result = lawphilLinkSchema.safeParse({ url: 'https://example.com/x.html' })
    expect(result.success ? '' : result.error.issues[0].message).toMatch(/Lawphil case link/)
  })
})
