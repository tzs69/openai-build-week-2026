export type TaskStatus = 'PLANNED' | 'READY' | 'BLOCKED'
export type ResourceInteraction = 'produce' | 'consume' | 'mutate' | 'retire'
export type ImpactClassification = 'direct' | 'downstream' | 'uncertain'

export interface Task {
  id: string
  title: string
  instructions: string
  color: string
  status: TaskStatus
  blocked_by: string[]
  requires_replan: boolean
}

export interface EffectTarget {
  node_id: string | null
  path: string | null
  symbol: string | null
}

export interface ProposedNode {
  id: string
  parent_id: string
  label: string
  type: string
  description: string
}

export interface ProposedEdge {
  id: string
  source: string
  target: string
  type: string
  label: string
}

export interface ArchitectureChange {
  action: 'create' | 'update' | 'move' | 'remove'
  node: ProposedNode | null
  edge: ProposedEdge | null
}

export interface ChangeEffect {
  effect_id: string
  kind: string
  interaction: ResourceInteraction
  resource_id: string
  target: EffectTarget
  details: Record<string, unknown>
  intent: string
  confidence: number
  architecture_change: ArchitectureChange | null
}

export interface ChangeContract {
  task_id: string
  version: number
  summary: string
  effects: ChangeEffect[]
  diagram_impact_claims: Array<{
    node_id: string
    classification: ImpactClassification
    reason: string
  }>
  tests_required: string[]
}

export interface ImpactEvidence {
  kind: 'declared_target' | 'graph_edge' | 'planner_claim'
  description: string
  edge_id: string | null
  path: string | null
  symbols: string[]
}

export interface DiagramImpact {
  task_id: string
  effect_id: string
  interaction: ResourceInteraction
  canonical_node_id: string
  visible_node_id: string | null
  classification: ImpactClassification
  reason: string
  confidence: number
  evidence: ImpactEvidence[]
  proposed_node: ProposedNode | null
  proposed_edge: ProposedEdge | null
}

export interface Conflict {
  id: string
  task_ids: string[]
  type: string
  severity: 'hard' | 'medium' | 'uncertain'
  blocking: boolean
  resource_id: string | null
  blocker_task_id: string | null
  blocked_task_id: string | null
  reason: string
}

export interface Dependency {
  predecessor_task_id: string
  successor_task_id: string
  type: 'produces_for' | 'replan_after'
  reason: string
  replan_required: boolean
}

export interface ExecutionBatch {
  index: number
  task_ids: string[]
  conditional: boolean
  condition: string | null
}

export interface RunSnapshot {
  run_id: string
  status: 'PLANNED'
  projection: { root: string | null; depth: number }
  tasks: Task[]
  contracts: ChangeContract[]
  impacts: DiagramImpact[]
  conflicts: Conflict[]
  dependencies: Dependency[]
  execution_batches: ExecutionBatch[]
}
