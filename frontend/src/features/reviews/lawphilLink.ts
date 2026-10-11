import { z } from 'zod'

/** A decision's own page, on Lawphil (https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html) or on the
 *  SC E-Library (https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/60169). */
export const DECISION_LINK =
  /^https:\/\/((www\.)?lawphil\.net\/judjuris\/.+\.html|elibrary\.judiciary\.gov\.ph\/thebookshelf\/showdocs\/1\/\d+)$/i

export const lawphilLinkSchema = z.object({
  url: z
    .string()
    .trim()
    .min(1, "Paste the case's link here (Lawphil or SC E-Library).")
    .refine(
      (value) => DECISION_LINK.test(value),
      "That doesn't look like a decision link. Use a Lawphil link (https://lawphil.net/judjuris/... .html) or an SC E-Library link (https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/...).",
    ),
})
