import type { ArchitectureGraph } from '../types/graphTypes'

export interface GraphQuery {
  root?: string | null
  depth?: number
  signal?: AbortSignal
}

function validateProjection(graph: ArchitectureGraph): void {
  if (
    graph.schema_version !== '1.0' ||
    !graph.metadata ||
    !graph.projection ||
    !Array.isArray(graph.nodes) ||
    !Array.isArray(graph.edges)
  ) {
    throw new Error('Graph response does not match the canonical projection contract')
  }

  const nodeIds = new Set(graph.nodes.map((node) => node.id))
  if (nodeIds.size !== graph.nodes.length) {
    throw new Error('Graph response contains duplicate node IDs')
  }

  const edgeIds = new Set(graph.edges.map((edge) => edge.id))
  if (edgeIds.size !== graph.edges.length) {
    throw new Error('Graph response contains duplicate edge IDs')
  }

  for (const node of graph.nodes) {
    if (!node.scope || !Array.isArray(node.scope.artifacts)) {
      throw new Error(`Node ${node.id} has invalid executor scope`)
    }
  }

  for (const edge of graph.edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      throw new Error(`Edge ${edge.id} references a missing projected node`)
    }
  }
}

export async function loadGraphProjection({
  root = null,
  depth = 1,
  signal,
}: GraphQuery = {}): Promise<ArchitectureGraph> {
  const parameters = new URLSearchParams({ depth: String(depth) })
  if (root) {
    parameters.set('root', root)
  }

  const response = await fetch(`/api/graph?${parameters}`, { signal })
  if (!response.ok) {
    let detail = ''
    try {
      const payload = (await response.json()) as { detail?: unknown }
      detail = typeof payload.detail === 'string' ? `: ${payload.detail}` : ''
    } catch {
      detail = ''
    }
    throw new Error(`Unable to load architecture (${response.status})${detail}`)
  }

  const graph = (await response.json()) as ArchitectureGraph
  validateProjection(graph)
  return graph
}
