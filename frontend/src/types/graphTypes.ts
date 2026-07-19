export interface GraphArtifactMetadata {
  repo_name: string
  repo_root: string
  languages: string[]
  frameworks: string[]
  source_roots: string[]
}

export interface ArtifactReference {
  path: string
  symbols: string[]
  ownership?: string
}

export interface GraphArtifactNode {
  id: string
  label: string
  type: string
  description: string
  scope: {
    artifacts: ArtifactReference[]
  }
  parent_id: string | null
}

export interface GraphArtifactEdge {
  id: string
  source: string
  target: string
  type: string
  label: string
  evidence: ArtifactReference[]
}

export interface StructuredGraphWarning {
  type?: string
  message: string
  evidence?: ArtifactReference[]
}

export type GraphWarning = string | StructuredGraphWarning

export interface GraphArtifact {
  schema_version: string
  metadata: GraphArtifactMetadata
  nodes: GraphArtifactNode[]
  edges: GraphArtifactEdge[]
  warnings?: GraphWarning[]
}

// Presentation types keep the graph renderer independent from artifact storage shape.
export interface GraphMetadata extends GraphArtifactMetadata {
  schema_version: string
  repository: string
}

export interface ArchitectureNode {
  id: string
  label: string
  type: string
  description: string
  artifacts: ArtifactReference[]
}

export interface ArchitectureEdge {
  id: string
  source: string
  target: string
  type: string
  description: string
  evidence: ArtifactReference[]
}

export interface ArchitectureGraph {
  metadata: GraphMetadata
  nodes: ArchitectureNode[]
  edges: ArchitectureEdge[]
  warnings: GraphWarning[]
}

export interface ArtifactNodeReference {
  id: string
  symbols: string[]
}

export interface ArtifactIndexEntry {
  nodes: ArtifactNodeReference[]
  edges: string[]
}

export interface ArtifactIndex {
  artifacts: Record<string, ArtifactIndexEntry>
}

export interface GraphBundle {
  graph: ArchitectureGraph
  artifactIndex: ArtifactIndex
}

export type GraphSelection =
  | { kind: 'node'; item: ArchitectureNode }
  | { kind: 'edge'; item: ArchitectureEdge }
  | null
