import dagre, {
  type EdgeLabel,
  type GraphLabel,
  type NodeLabel,
  type Point,
} from '@dagrejs/dagre'
import type { ArchitectureEdge, ArchitectureNode } from '../types/graphTypes'

export const NODE_WIDTH = 220
export const NODE_HEIGHT = 102

export interface NodePosition {
  x: number
  y: number
}

export interface EdgeRoute {
  points: Point[]
  labelPosition: Point
}

export interface GraphLayout {
  nodePositions: Map<string, NodePosition>
  edgeRoutes: Map<string, EdgeRoute>
}

function edgeLabelWidth(type: string): number {
  return Math.max(44, type.length * 7 + 18)
}

export function layoutGraph(
  nodes: ArchitectureNode[],
  edges: ArchitectureEdge[],
): GraphLayout {
  const graph = new dagre.graphlib.Graph<GraphLabel, NodeLabel, EdgeLabel>({
    multigraph: true,
  })

  graph.setGraph({
    rankdir: 'LR',
    ranker: 'network-simplex',
    acyclicer: 'greedy',
    ranksep: 120,
    nodesep: 76,
    edgesep: 38,
    marginx: 36,
    marginy: 36,
  })
  graph.setDefaultEdgeLabel(() => ({}))

  for (const node of nodes) {
    graph.setNode(node.id, {
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    })
  }

  for (const edge of edges) {
    graph.setEdge(
      edge.source,
      edge.target,
      {
        width: edgeLabelWidth(edge.type),
        height: 24,
        labelpos: 'c',
        labeloffset: 12,
      },
      edge.id,
    )
  }

  dagre.layout(graph)

  const nodePositions = new Map<string, NodePosition>()
  for (const node of nodes) {
    const layoutNode = graph.node(node.id)
    nodePositions.set(node.id, {
      x: (layoutNode.x ?? 0) - NODE_WIDTH / 2,
      y: (layoutNode.y ?? 0) - NODE_HEIGHT / 2,
    })
  }

  const edgeRoutes = new Map<string, EdgeRoute>()
  for (const edge of edges) {
    const layoutEdge = graph.edge({ v: edge.source, w: edge.target, name: edge.id })
    const points = layoutEdge.points ?? []
    const midpoint = points[Math.floor(points.length / 2)] ?? { x: 0, y: 0 }

    edgeRoutes.set(edge.id, {
      points,
      labelPosition: {
        x: layoutEdge.x ?? midpoint.x,
        y: layoutEdge.y ?? midpoint.y,
      },
    })
  }

  return { nodePositions, edgeRoutes }
}
