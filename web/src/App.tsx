import { useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'
import Login from './Login'
import Staff from './Staff'
import Student from './Student'
import type { Me } from './types'

export default function App() {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) return
    api<Me>('/api/me')
      .then(setMe)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const onLogout = () => setMe(null)
    window.addEventListener('sop:logout', onLogout)
    return () => window.removeEventListener('sop:logout', onLogout)
  }, [])

  function logout() {
    setToken(null)
    setMe(null)
  }

  if (loading) return <p className="center">Loading…</p>
  if (!me) return <Login onLogin={setMe} />

  return (
    <div>
      <header className="topbar">
        <h1>SOP Automator</h1>
        <div>
          <span className="who">{me.email} · {me.role}</span>
          <button className="link" onClick={logout}>Log out</button>
        </div>
      </header>
      {me.role === 'student' ? <Student /> : <Staff />}
    </div>
  )
}
