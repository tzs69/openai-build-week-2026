import type {
  ArchitectureGraph,
  ArtifactIndex,
  ArtifactIndexEntry,
  GraphArtifact,
  GraphArtifactNode,
  GraphBundle,
} from '../types/graphTypes'

const GRAPH_API_URL = '/api/graph'

interface ApiErrorPayload {
  detail?: {
    message?: string
    errors?: string[]
  }
}

async function responseError(response: Response, url: string): Promise<Error> {
  const fallback = `Unable to load ${url} (${response.status})`

  try {
    const payload = (await response.json()) as ApiErrorPayload
    const message = payload.detail?.message
    const firstError = payload.detail?.errors?.[0]
    if (message && firstError) {
      return new Error(`${message}: ${firstError}`)
    }
    return new Error(message ?? fallback)
  } catch {
    return new Error(fallback)
  }
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url)

  if (!response.ok) {
    throw await responseError(response, url)
  }

  return response.json() as Promise<T>
}

function validateGraphArtifact(graph: GraphArtifact): void {
  if (
    typeof graph.schema_version !== 'string' ||
    !graph.metadata ||
    !Array.isArray(graph.nodes) ||
    !Array.isArray(graph.edges)
  ) {
    throw new Error('graph.json does not match the expected graph artifact contract')
  }

  const nodeIds = new Set(graph.nodes.map((node) => node.id))
  const edgeIds = new Set(graph.edges.map((edge) => edge.id))

  if (nodeIds.size !== graph.nodes.length) {
    throw new Error('graph.json contains duplicate node IDs')
  }

  if (edgeIds.size !== graph.edges.length) {
    throw new Error('graph.json contains duplicate edge IDs')
  }

  for (const node of graph.nodes) {
    if (!node.scope || !Array.isArray(node.scope.artifacts)) {
      throw new Error(`Node ${node.id} has an invalid scope`)
    }

    if (node.parent_id !== null && !nodeIds.has(node.parent_id)) {
      throw new Error(`Node ${node.id} references a missing parent`)
    }
  }

  for (const edge of graph.edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      throw new Error(`Edge ${edge.id} references a missing node`)
    }
  }
}

function isParentOnlyContainer(
  node: GraphArtifactNode,
  parentIds: Set<string>,
  edgeEndpointIds: Set<string>,
): boolean {
  return (
    parentIds.has(node.id) &&
    node.scope.artifacts.length === 0 &&
    !edgeEndpointIds.has(node.id)
  )
}

function normalizeGraphArtifact(artifact: GraphArtifact): ArchitectureGraph {
  const parentIds = new Set(
    artifact.nodes.flatMap((node) => (node.parent_id ? [node.parent_id] : [])),
  )
  const edgeEndpointIds = new Set(
    artifact.edges.flatMap((edge) => [edge.source, edge.target]),
  )
  const visibleNodes = artifact.nodes.filter(
    (node) => !isParentOnlyContainer(node, parentIds, edgeEndpointIds),
  )
  const visibleNodeIds = new Set(visibleNodes.map((node) => node.id))

  return {
    metadata: {
      ...artifact.metadata,
      schema_version: artifact.schema_version,
      repository: artifact.metadata.repo_name,
    },
    nodes: visibleNodes.map((node) => ({
      id: node.id,
      label: node.label,
      type: node.type,
      description: node.description,
      artifacts: node.scope.artifacts,
    })),
    edges: artifact.edges
      .filter(
        (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target),
      )
      .map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        description: edge.label,
        evidence: edge.evidence,
      })),
    warnings: artifact.warnings ?? [],
  }
}

function getOrCreateIndexEntry(
  index: ArtifactIndex,
  path: string,
): ArtifactIndexEntry {
  const existing = index.artifacts[path]
  if (existing) {
    return existing
  }

  const created = { nodes: [], edges: [] }
  index.artifacts[path] = created
  return created
}

function buildArtifactIndex(artifact: GraphArtifact): ArtifactIndex {
  const index: ArtifactIndex = { artifacts: {} }

  for (const node of artifact.nodes) {
    for (const reference of node.scope.artifacts) {
      getOrCreateIndexEntry(index, reference.path).nodes.push({
        id: node.id,
        symbols: reference.symbols,
      })
    }
  }

  for (const edge of artifact.edges) {
    for (const evidence of edge.evidence) {
      const entry = getOrCreateIndexEntry(index, evidence.path)
      if (!entry.edges.includes(edge.id)) {
        entry.edges.push(edge.id)
      }
    }
  }

  return index
}

export async function loadGraphBundle(): Promise<GraphBundle> {
  const artifact = await fetchJson<GraphArtifact>(GRAPH_API_URL)
  validateGraphArtifact(artifact)

  return {
    graph: normalizeGraphArtifact(artifact),
    artifactIndex: buildArtifactIndex(artifact),
  }
}
