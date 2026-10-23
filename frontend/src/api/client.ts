import createFetchClient from "openapi-fetch";
import createQueryClient from "openapi-react-query";
import type { paths } from "./schema";

// The backend is served under /api by the Vite dev proxy and by nginx in Docker.
export const fetchClient = createFetchClient<paths>({
  baseUrl: new URL("/api", window.location.origin).href,
});

// TanStack Query hooks typed from the backend's OpenAPI schema, e.g. `api.useQuery('get', '/health')`.
export const api = createQueryClient(fetchClient);
