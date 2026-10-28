import { useCallback, useEffect, useState } from 'react'
import { api, errorMessage } from './api'
import FeedbackForm from './FeedbackForm'
import StatusBadge from './StatusBadge'
import type { Run, RunEvent } from './types'

const FINAL = new Set(['completed', 'failed', 'cancelled'])

const EVENT_LABELS: Record<string, string> = {
  run_started: 'Run started',
  step_started: 'Started',
  step_done: 'Done',
  waiting_approval: 'Waiting for approval',
  approved: 'Approved',
  step_failed: 'Failed',
  retry: 'Retry',
  run_completed: 'Run completed',
  cancelled: 'Cancelled',
}

function describe(e: RunEvent): string {
  if (e.event === 'step_started') return `helper: ${String(e.detail.handler ?? 'manual')}`
  return Object.entries(e.detail)
    .filter(([key]) => key !== 'action')
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ')
}

export default function RunDetail({ id, onChange }: { id: number; onChange: () => void }) {
  const [run, setRun] = useState<Run | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feedbackRow, setFeedbackRow] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      setRun(await api<Run>(`/api/runs/${id}`))
      setError(null)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const status = run?.status
  useEffect(() => {
    if (!status || FINAL.has(status)) return
    const timer = setInterval(load, 3000)
    return () => clearInterval(timer)
  }, [status, load])

  async function act(path: string, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return
    setBusy(true)
    setError(null)
    try {
      setRun(await api<Run>(`/api/runs/${id}/${path}`, { method: 'POST' }))
      onChange()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (!run) {
    return (
      <section className="card">
        {error ? <p className="error" role="alert">{error}</p> : <p className="muted">Loading run…</p>}
      </section>
    )
  }

  const waiting = run.status === 'waiting_approval'
    ? [...run.events].reverse().find((e) => e.event === 'waiting_approval')
    : undefined

  return (
    <section className="card">
      <div className="row between">
        <h2>Run #{run.id}</h2>
        <StatusBadge status={run.status} />
      </div>

      <dl className="facts">
        <div><dt>Client</dt><dd>{run.input.client_name}</dd></div>
        <div><dt>Cuts</dt><dd>{run.input.cuts}</dd></div>
        <div><dt>Payment</dt><dd>{run.input.payment}</dd></div>
        <div><dt>FHIR patient</dt><dd>{String(run.context.patient_id ?? '—')}</dd></div>
        <div><dt>Student</dt><dd>{run.context.student_id ? `#${String(run.context.student_id)}` : '—'}</dd></div>
      </dl>

      {waiting && (
        <div className="banner" role="status">
          <strong>Step {waiting.step} needs approval:</strong> {String(waiting.detail.action ?? '')}
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}

      <div className="row gap">
        {run.status === 'waiting_approval' && (
          <button onClick={() => act('approve')} disabled={busy}>Approve step {run.current_step}</button>
        )}
        {run.status === 'failed' && (
          <button onClick={() => act('retry')} disabled={busy}>Retry</button>
        )}
        {run.status === 'completed' && (
          <button className="secondary" onClick={() => act('retry?from_start=true')} disabled={busy}>Re-run from start</button>
        )}
        {(run.status === 'waiting_approval' || run.status === 'failed' || run.status === 'running') && (
          <button className="danger" onClick={() => act('cancel', `Cancel run #${run.id}?`)} disabled={busy}>Cancel run</button>
        )}
      </div>

      <h3>Diary</h3>
      <ol className="diary">
        {run.events.map((e, i) => (
          <li key={i} className={`ev-${e.event}`}>
            <time>{new Date(e.at).toLocaleTimeString()}</time>
            <span className="step">{e.step ? `Step ${e.step}` : ''}</span>
            <span className="what">
              {EVENT_LABELS[e.event] ?? e.event}
              {e.event === 'step_started' ? `: ${String(e.detail.action ?? '')}` : ''}
              {e.event === 'step_started' && e.step !== null && (
                <button
                  type="button"
                  className="thumb"
                  title="This step is wrong"
                  aria-label={`Flag step ${e.step} as wrong`}
                  onClick={() => setFeedbackRow(feedbackRow === i ? null : i)}
                >
                  👎
                </button>
              )}
            </span>
            <span className="detail">{describe(e)}</span>
            {feedbackRow === i && e.step !== null && (
              <FeedbackForm workflowId={run.workflow_id} runId={run.id} step={e.step} onClose={() => setFeedbackRow(null)} />
            )}
          </li>
        ))}
      </ol>
    </section>
  )
}
