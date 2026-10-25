import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorMessage } from './api'
import type { Run, SopSummary } from './types'

export default function NewRun({ onStarted }: { onStarted: (id: number) => void }) {
  const [sops, setSops] = useState<SopSummary[]>([])
  const [workflowId, setWorkflowId] = useState<number | ''>('')
  const [clientName, setClientName] = useState('')
  const [cuts, setCuts] = useState(1)
  const [payment, setPayment] = useState<'cash' | 'card'>('cash')
  const [failures, setFailures] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<SopSummary[]>('/api/sops')
      .then((list) => {
        const ready = list.filter((s) => s.latest_workflow_id !== null)
        setSops(ready)
        const preferred = ready.find((s) => s.prompt_version === 'parse-v2') ?? ready[0]
        if (preferred?.latest_workflow_id) setWorkflowId(preferred.latest_workflow_id)
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (workflowId === '') return
    setBusy(true)
    setError(null)
    try {
      const run = await api<Run>('/api/runs', {
        method: 'POST',
        body: JSON.stringify({
          workflow_id: workflowId,
          client_name: clientName.trim(),
          cuts,
          payment,
          simulate_fhir_failures: failures,
        }),
      })
      setClientName('')
      onStarted(run.id)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <h2>New client</h2>
      <form onSubmit={submit}>
        <label>
          Procedure
          <select value={workflowId} onChange={(e) => setWorkflowId(Number(e.target.value))} required>
            {sops.map((s) => (
              <option key={s.id} value={s.latest_workflow_id ?? ''}>
                {s.title} (v{s.latest_version})
              </option>
            ))}
          </select>
        </label>
        <label>
          Client name (fake names only)
          <input value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="Test Client Three" required maxLength={200} />
        </label>
        <label>
          Number of cuts
          <input type="number" min={1} max={5} value={cuts} onChange={(e) => setCuts(Number(e.target.value))} />
        </label>
        <label>
          Payment
          <select value={payment} onChange={(e) => setPayment(e.target.value as 'cash' | 'card')}>
            <option value="cash">Cash</option>
            <option value="card">Card</option>
          </select>
        </label>
        <label>
          Demo: pretend server failures
          <select value={failures} onChange={(e) => setFailures(Number(e.target.value))}>
            <option value={0}>None</option>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3 (will fail)</option>
          </select>
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button disabled={busy || workflowId === ''}>{busy ? 'Starting…' : 'Start intake'}</button>
      </form>
    </section>
  )
}
