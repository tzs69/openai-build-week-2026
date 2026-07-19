import { MarkerType, type Edge, type Node, type XYPosition } from '@xyflow/react'
import type { ArchitectureEdge, ArchitectureGraph, ArchitectureNode } from '../types/graphTypes'
import type { DiagramImpact, Task } from '../types/coordinationTypes'
import { layoutGraph, NODE_HEIGHT, NODE_WIDTH, type NodePosition } from './layout'

export type HandleSide = 'left' | 'right' | 'top' | 'bottom'

interface NodeHandles {
  source: HandleSide[]
  target: HandleSide[]
}

export type ArchitectureNodeData = {
  architectureNode: ArchitectureNode
  handles: NodeHandles
  impacts: Array<{ impact: DiagramImpact; task: Task }>
  activeTaskId: string | null
} & Record<string, unknown>

export type ArchitectureEdgeData = {
  architectureEdge: ArchitectureEdge
  routePoints: XYPosition[]
  labelPosition: XYPosition
} & Record<string, unknown>

export type ArchitectureFlowNode = Node<ArchitectureNodeData, 'architecture'>
export type ArchitectureFlowEdge = Edge<ArchitectureEdgeData, 'architecture'>

export interface FlowElements {
  nodes: ArchitectureFlowNode[]
  edges: ArchitectureFlowEdge[]
}

function addHandle(
  handleMap: Map<string, { source: Set<HandleSide>; target: Set<HandleSide> }>,
  nodeId: string,
  kind: 'source' | 'target',
  side: HandleSide,
) {
  const handles = handleMap.get(nodeId) ?? {
    source: new Set<HandleSide>(),
    target: new Set<HandleSide>(),
  }
  handles[kind].add(side)
  handleMap.set(nodeId, handles)
}

function getHandleSide(
  nodePosition: NodePosition,
  routePoint: XYPosition,
): HandleSide {
  const centerX = nodePosition.x + NODE_WIDTH / 2
  const centerY = nodePosition.y + NODE_HEIGHT / 2
  const horizontalDistance = Math.abs(routePoint.x - centerX) / (NODE_WIDTH / 2)
  const verticalDistance = Math.abs(routePoint.y - centerY) / (NODE_HEIGHT / 2)

  if (horizontalDistance >= verticalDistance) {
    return routePoint.x >= centerX ? 'right' : 'left'
  }

  return routePoint.y >= centerY ? 'bottom' : 'top'
}

export function graphToFlowElements(graph: ArchitectureGraph): FlowElements {
  const layout = layoutGraph(graph.nodes, graph.edges)
  const handleMap = new Map<
    string,
    { source: Set<HandleSide>; target: Set<HandleSide> }
  >()
  const sidesByEdge = new Map<
    string,
    { sourceSide: HandleSide; targetSide: HandleSide }
  >()

  for (const edge of graph.edges) {
    const route = layout.edgeRoutes.get(edge.id)
    const sourcePosition = layout.nodePositions.get(edge.source)
    const targetPosition = layout.nodePositions.get(edge.target)
    const firstPoint = route?.points[0]
    const lastPoint = route?.points.at(-1)

    if (!sourcePosition || !targetPosition || !firstPoint || !lastPoint) {
      continue
    }

    const sourceSide = getHandleSide(sourcePosition, firstPoint)
    const targetSide = getHandleSide(targetPosition, lastPoint)
    sidesByEdge.set(edge.id, { sourceSide, targetSide })
    addHandle(handleMap, edge.source, 'source', sourceSide)
    addHandle(handleMap, edge.target, 'target', targetSide)
  }

  const nodes: ArchitectureFlowNode[] = graph.nodes.map((node) => {
    const handles = handleMap.get(node.id)

    return {
      id: node.id,
      type: 'architecture',
      position: layout.nodePositions.get(node.id) ?? { x: 0, y: 0 },
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      data: {
        architectureNode: node,
        impacts: [],
        activeTaskId: null,
        handles: {
          source: [...(handles?.source ?? [])],
          target: [...(handles?.target ?? [])],
        },
      },
    }
  })

  const edges: ArchitectureFlowEdge[] = graph.edges.map((edge) => {
    const route = layout.edgeRoutes.get(edge.id)
    const sides = sidesByEdge.get(edge.id) ?? {
      sourceSide: 'right' as const,
      targetSide: 'left' as const,
    }

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: `source-${sides.sourceSide}`,
      targetHandle: `target-${sides.targetSide}`,
      type: 'architecture',
      data: {
        architectureEdge: edge,
        routePoints: route?.points ?? [],
        labelPosition: route?.labelPosition ?? { x: 0, y: 0 },
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        color: edge.proposed ? '#6854c7' : '#79847d',
      },
      className: edge.proposed ? 'is-proposed-edge' : undefined,
      style: edge.proposed
        ? { stroke: '#6854c7', strokeDasharray: '7 5', strokeWidth: 2 }
        : undefined,
      interactionWidth: 18,
    }
  })

  return { nodes, edges }
}
