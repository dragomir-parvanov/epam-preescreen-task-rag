import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { expect, test } from 'vitest'
import type { components } from './api/schema'
import App from './App'
import { server } from './test/server'

test('shows the status the backend reports on /health', async () => {
  server.use(
    http.get('*/api/health', () =>
      HttpResponse.json<components['schemas']['HealthResponse']>({ status: 'ok' }),
    ),
  )

  render(<App />)

  expect(await screen.findByText('ok')).toBeInTheDocument()
})
