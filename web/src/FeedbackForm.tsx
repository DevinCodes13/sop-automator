import { useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorMessage } from './api'

type Props = { workflowId: number; runId: number; step: number; onClose: () => void }

export default function FeedbackForm({ workflowId, runId, step, onClose }: Props) {
  const [reason, setReason] = useState('')
  const [approval, setApproval] = useState<'' | 'yes' | 'no'>('')
  const [handler, setHandler] = useState('')
  const [saved, setSaved] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = await api<{ id: number }>(`/api/workflows/${workflowId}/feedback`, {
        method: 'POST',
        body: JSON.stringify({
          run_id: runId,
          step_number: step,
          reason: reason.trim(),
          expected_needs_approval: approval === '' ? null : approval === 'yes',
          expected_handler: handler || null,
        }),
      })
      setSaved(res.id)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (saved !== null) {
    return (
      <div className="feedback">
        <p className="ok" role="status">
          Thanks! Saved as feedback #{saved}.{' '}
          <button type="button" className="link" onClick={onClose}>Close</button>
        </p>
      </div>
    )
  }

  return (
    <div className="feedback">
      <form onSubmit={submit}>
        <label>
          What's wrong with step {step}?
          <input value={reason} onChange={(e) => setReason(e.target.value)} required minLength={3} maxLength={500} placeholder="This step shouldn't need approval" />
        </label>
        <label>
          Should it need approval?
          <select value={approval} onChange={(e) => setApproval(e.target.value as '' | 'yes' | 'no')}>
            <option value="">No change</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </label>
        <label>
          Right helper
          <select value={handler} onChange={(e) => setHandler(e.target.value)}>
            <option value="">No change</option>
            <option value="manual">manual</option>
            <option value="record_client">record_client</option>
            <option value="assign_student">assign_student</option>
          </select>
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row gap">
          <button disabled={busy}>{busy ? 'Sending…' : 'Send feedback'}</button>
          <button type="button" className="secondary" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  )
}
