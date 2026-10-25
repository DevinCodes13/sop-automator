import { useState } from 'react'
import { api, errorMessage } from './api'

export default function Student() {
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function checkIn() {
    setBusy(true)
    setError(null)
    try {
      const res = await api<{ already_checked_in: boolean }>('/api/checkins/me', { method: 'POST' })
      setMessage(res.already_checked_in ? "You're already checked in for today." : "You're checked in. Have a great day!")
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="center">
      <section className="card login">
        <h2>Daily check-in</h2>
        <p className="muted">Tap once when you arrive.</p>
        <button onClick={checkIn} disabled={busy}>{busy ? 'Checking in…' : 'Check in'}</button>
        {message && <p className="ok" role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>
    </main>
  )
}
