import { notFound } from '@tanstack/react-router'

import { ApiError } from './client'

/** A page for something that does not exist (the API answered 404) should say "we can't find
 *  that", not show a generic failure. Any other error is passed on unchanged. */
export async function orNotFound<T>(request: Promise<T>): Promise<T> {
  try {
    return await request
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) throw notFound()
    throw error
  }
}
