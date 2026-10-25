export type Role = 'admin' | 'instructor' | 'student'
export type RunStatus = 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled'

export interface Me {
  id: number
  email: string
  role: Role
}

export interface RunEvent {
  step: number | null
  event: string
  detail: Record<string, unknown>
  user_id: number | null
  at: string
}

export interface Run {
  id: number
  public_id: string
  workflow_id: number
  status: RunStatus
  current_step: number
  input: { client_name: string; cuts: number; payment: string }
  context: Record<string, unknown>
  created_at: string
  events: RunEvent[]
}

export interface RunSummary {
  id: number
  status: RunStatus
  current_step: number
  client_name: string
  created_at: string
}

export interface Checkin {
  student: string
  checked_in_at: string
  clients_today: number
}

export interface SopSummary {
  id: number
  title: string
  latest_workflow_id: number | null
  latest_version: number | null
  prompt_version: string | null
}
