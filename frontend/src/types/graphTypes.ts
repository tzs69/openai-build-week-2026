export interface GraphMetadata {
  schema_version: string
  generated_at: string
  repository?: string
  repository_root?: string
  description?: string
  language?: string
  runtime?: string
  frameworks?: string[]
  source?: string
}

export interface ArtifactReference {
  path: string
  symbols: string[]
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

export interface StructuredGraphWarning {
  message: string
  evidence?: ArtifactReference[]
}

export type GraphWarning = string | StructuredGraphWarning

export interface ArchitectureGraph {
  metadata: GraphMetadata
  nodes: ArchitectureNode[]
  edges: ArchitectureEdge[]
  warnings: GraphWarning[]
}

export interface ReverseNodeReference {
  id: string
  symbols: string[]
}

export interface ReverseArtifactEntry {
  nodes: ReverseNodeReference[]
  edges: string[]
}

export interface GraphReverseMap {
  metadata: {
    schema_version: string
    generated_at: string
    source?: string
    source_graph?: string
  }
  artifacts: Record<string, ReverseArtifactEntry>
}

export interface GraphBundle {
  graph: ArchitectureGraph
  reverse: GraphReverseMap
}

export type GraphSelection =
  | { kind: 'node'; item: ArchitectureNode }
  | { kind: 'edge'; item: ArchitectureEdge }
  | null
