import type { RunSnapshot } from '../types/coordinationTypes'

interface RunQuery {
  root?: string | null
  depth?: number
  signal?: AbortSignal
}

function queryString(root: string | null, depth: number): string {
  const parameters = new URLSearchParams({ depth: String(depth) })
  if (root) {
    parameters.set('root', root)
  }
  return parameters.toString()
}

function validateRun(run: RunSnapshot): void {
  if (
    !run.run_id ||
    run.status !== 'PLANNED' ||
    !run.projection ||
    !Array.isArray(run.tasks) ||
    !Array.isArray(run.contracts) ||
    !Array.isArray(run.impacts) ||
    !Array.isArray(run.conflicts) ||
    !Array.isArray(run.dependencies) ||
    !Array.isArray(run.execution_batches)
  ) {
    throw new Error('Run response does not match the coordination contract')
  }
}

async function requestRun(url: string, init: RequestInit): Promise<RunSnapshot> {
  const response = await fetch(url, init)
  if (!response.ok) {
    let detail = ''
    try {
      const payload = (await response.json()) as { detail?: unknown }
      detail = typeof payload.detail === 'string' ? `: ${payload.detail}` : ''
    } catch {
      detail = ''
    }
    throw new Error(`Unable to load coordination run (${response.status})${detail}`)
  }
  const run = (await response.json()) as RunSnapshot
  validateRun(run)
  return run
}

export function createRun({ root = null, depth = 1, signal }: RunQuery = {}) {
  return requestRun(`/api/runs?${queryString(root, depth)}`, {
    method: 'POST',
    signal,
  })
}

export function loadRun(
  runId: string,
  { root = null, depth = 1, signal }: RunQuery = {},
) {
  return requestRun(`/api/runs/${encodeURIComponent(runId)}?${queryString(root, depth)}`, {
    method: 'GET',
    signal,
  })
}
