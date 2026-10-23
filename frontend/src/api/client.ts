import createClient from 'openapi-fetch'
import type { paths } from './schema'

// The backend is served under /api by the Vite dev proxy and by nginx in Docker.
export const api = createClient<paths>({
  baseUrl: new URL('/api', window.location.origin).href,
})
