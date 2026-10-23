import { useEffect, useState } from 'react'
import { api } from './api/client'

type BackendStatus = 'checking' | 'ok' | 'unavailable'

function App() {
  const [status, setStatus] = useState<BackendStatus>('checking')

  useEffect(() => {
    api
      .GET('/health')
      .then(({ data }) => {
        setStatus(data?.status ?? 'unavailable')
      })
      .catch(() => {
        setStatus('unavailable')
      })
  }, [])

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-900">
      <p className="text-lg">
        Backend status: <span className="font-mono font-semibold">{status}</span>
      </p>
    </main>
  )
}

export default App
