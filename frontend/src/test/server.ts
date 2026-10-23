import { setupServer } from 'msw/node'

// Shared mock of the backend's HTTP boundary; tests add handlers with `server.use`.
export const server = setupServer()
