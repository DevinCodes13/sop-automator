import { useEffect, useState } from 'react'

type Health = { api: string; db: string }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setHealth)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <main style={{ fontFamily: 'system-ui', padding: '2rem' }}>
      <h1>SOP Automator</h1>
      {error && <p role="alert">Error: {error}</p>}
      {!health && !error && <p>Checking system status…</p>}
      {health && (
        <ul>
          <li>API: {health.api}</li>
          <li>Database: {health.db}</li>
        </ul>
      )}
    </main>
  )
}
