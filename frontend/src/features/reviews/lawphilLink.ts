import { z } from 'zod'

/** Lawphil case pages look like https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html */
export const lawphilLinkSchema = z.object({
  url: z
    .string()
    .trim()
    .min(1, "Paste the case's Lawphil link here.")
    .refine(
      (value) => /^https:\/\/(www\.)?lawphil\.net\/judjuris\/.+\.html$/i.test(value),
      "That doesn't look like a Lawphil case link. It should start with https://lawphil.net/judjuris/ and end in .html",
    ),
})
