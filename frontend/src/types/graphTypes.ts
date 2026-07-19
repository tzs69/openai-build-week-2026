export interface GraphMetadata {
  repo_name: string
  repo_root: string
  languages: string[]
  frameworks: string[]
  source_roots: string[]
}

export type ArtifactOwnership = 'primary' | 'shared'

export interface ArtifactReference {
  path: string
  symbols: string[]
  ownership?: ArtifactOwnership
}

export interface ArchitectureNode {
  id: string
  parent_id: string | null
  label: string
  type: string
  description: string
  scope: {
    artifacts: ArtifactReference[]
  }
  proposed?: boolean
  proposed_by_task_id?: string
}

export interface ArchitectureEdge {
  id: string
  source: string
  target: string
  type: string
  label: string
  evidence: ArtifactReference[]
  aggregated_edge_ids?: string[]
  proposed?: boolean
  proposed_by_task_id?: string
}

export interface GraphProjectionMetadata {
  root: string | null
  depth: number
}

export interface ArchitectureGraph {
  schema_version: string
  metadata: GraphMetadata
  projection: GraphProjectionMetadata
  nodes: ArchitectureNode[]
  edges: ArchitectureEdge[]
}

export type GraphSelection =
  | { kind: 'node'; item: ArchitectureNode }
  | { kind: 'edge'; item: ArchitectureEdge }
  | null
