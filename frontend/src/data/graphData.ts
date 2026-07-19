import type {
  ArchitectureGraph,
  GraphBundle,
  GraphReverseMap,
} from '../types/graphTypes'

const FIXTURE_BASE_URL = '/fixtures/test-repo-1'
export const FIXTURE_REPOSITORY_LABEL = 'test_repo_1'

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Unable to load ${url} (${response.status})`)
  }

  return response.json() as Promise<T>
}

function validateGraph(graph: ArchitectureGraph): void {
  if (!graph.metadata || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) {
    throw new Error('graph.json does not match the expected graph contract')
  }

  const nodeIds = new Set(graph.nodes.map((node) => node.id))
  const edgeIds = new Set(graph.edges.map((edge) => edge.id))

  if (nodeIds.size !== graph.nodes.length) {
    throw new Error('graph.json contains duplicate node IDs')
  }

  if (edgeIds.size !== graph.edges.length) {
    throw new Error('graph.json contains duplicate edge IDs')
  }

  for (const edge of graph.edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      throw new Error(`Edge ${edge.id} references a missing node`)
    }
  }

  graph.warnings ??= []
}

function validateReverseMap(reverse: GraphReverseMap): void {
  if (!reverse.metadata || !reverse.artifacts || Array.isArray(reverse.artifacts)) {
    throw new Error('graph_reverse.json does not match the expected reverse-map contract')
  }
}

export async function loadGraphBundle(): Promise<GraphBundle> {
  const [graph, reverse] = await Promise.all([
    fetchJson<ArchitectureGraph>(`${FIXTURE_BASE_URL}/graph.json`),
    fetchJson<GraphReverseMap>(`${FIXTURE_BASE_URL}/graph_reverse.json`),
  ])

  validateGraph(graph)
  validateReverseMap(reverse)

  return { graph, reverse }
}
