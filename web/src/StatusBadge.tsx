import type { RunStatus } from './types'

const LABELS: Record<RunStatus, string> = {
  running: 'Running',
  waiting_approval: 'Needs approval',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export default function StatusBadge({ status }: { status: RunStatus }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] ?? status}</span>
}
