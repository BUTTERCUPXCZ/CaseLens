import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import caseDetail from '../fixtures/api/case-180046.json'
import digestErmita from '../fixtures/api/digest-ermita.json'
import catalogErmita from '../fixtures/api/catalog-search-ermita.json'
import catalogStatus from '../fixtures/api/catalog-status-ready.json'
import insights from '../fixtures/api/insights-180046.json'
import caseDigestMarcos from '../fixtures/api/case-digest-marcos.json'
import library from '../fixtures/api/library.json'
import librarySubjects from '../fixtures/api/library-subjects.json'
import subjectList from '../fixtures/api/subject-list.json'
import needsALook from '../fixtures/api/upload-needs-a-look.json'
import uploads from '../fixtures/api/uploads.json'

// The app calls relative URLs (/api/...); the test browser resolves them against its own origin.
const API = `${window.location.origin}/api`

/** The backend, replayed from real captured responses (tests/fixtures/api/*.json).
 *  Tests override single handlers with `server.use(...)` for the cases they need. */
export const handlers = [
  http.get(`${API}/uploads`, () => HttpResponse.json(uploads)),
  http.get(`${API}/uploads/:id`, () => HttpResponse.json(needsALook)),
  http.post(`${API}/uploads`, () => HttpResponse.json(needsALook)),
  http.get(`${API}/library/cases`, () => HttpResponse.json(library)),
  http.get(`${API}/library/subjects`, () => HttpResponse.json(librarySubjects)),
  http.get(`${API}/library/subject-list`, () => HttpResponse.json(subjectList)),
  http.get(`${API}/cases/:id/case-digest`, () => HttpResponse.json(caseDigestMarcos)),
  http.get(`${API}/cases/:id`, () => HttpResponse.json(caseDetail)),
  http.get(`${API}/cases/:id/insights`, () => HttpResponse.json(insights)),
  http.get(`${API}/catalog/search`, () => HttpResponse.json(catalogErmita)),
  http.get(`${API}/catalog/status`, () => HttpResponse.json(catalogStatus)),
  // Digest 9 is the real Ermita digest. 10 and 11 reuse its shape under other case names (synthetic) so each box is distinct.
  http.get(`${API}/digests/:id`, ({ params }) => {
    const id = Number(params.id)
    return HttpResponse.json(id === 9 ? digestErmita : { ...digestErmita, id, case_title: `Other Case ${id} vs. People`, gr_no: String(100000 + id) })
  }),
]

export const server = setupServer(...handlers)
export { API, http, HttpResponse }
