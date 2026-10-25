import { useCallback, useEffect, useState } from 'react'
import { api, errorMessage } from './api'
import NewRun from './NewRun'
import RunDetail from './RunDetail'
import StatusBadge from './StatusBadge'
import type { Checkin, RunSummary } from './types'

export default function Staff() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [checkins, setCheckins] = useState<Checkin[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [r, c] = await Promise.all([
        api<RunSummary[]>('/api/runs'),
        api<Checkin[]>('/api/checkins/today'),
      ])
      setRuns(r)
      setCheckins(c)
      setError(null)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 5000)
    return () => clearInterval(timer)
  }, [refresh])

  return (
    <main className="grid">
      <div className="col">
        <NewRun onStarted={(id) => { setSelected(id); refresh() }} />

        <section className="card">
          <h2>Today's students</h2>
          {checkins.length === 0 ? (
            <p className="muted">No students checked in yet.</p>
          ) : (
            <table>
              <thead>
                <tr><th>Student</th><th>Checked in</th><th>Clients</th></tr>
              </thead>
              <tbody>
                {checkins.map((c) => (
                  <tr key={c.student}>
                    <td>{c.student}</td>
                    <td>{new Date(c.checked_in_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</td>
                    <td>{c.clients_today}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="card">
          <h2>Runs</h2>
          {error && <p className="error" role="alert">{error}</p>}
          {runs.length === 0 ? (
            <p className="muted">No runs yet.</p>
          ) : (
            <ul className="runs">
              {runs.map((r) => (
                <li key={r.id}>
                  <button
                    className={`run-item${r.id === selected ? ' selected' : ''}`}
                    onClick={() => setSelected(r.id)}
                    aria-current={r.id === selected}
                  >
                    <span>#{r.id} · {r.client_name}</span>
                    <StatusBadge status={r.status} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="col">
        {selected ? (
          <RunDetail key={selected} id={selected} onChange={refresh} />
        ) : (
          <section className="card"><p className="muted">Pick a run to see its steps.</p></section>
        )}
      </div>
    </main>
  )
}
