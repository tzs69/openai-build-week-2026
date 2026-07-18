import { useMemo } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  type EdgeMouseHandler,
  type NodeMouseHandler,
} from '@xyflow/react'
import {
  graphToFlowElements,
  type ArchitectureFlowEdge,
  type ArchitectureFlowNode,
  type ArchitectureNodeData,
} from '../data/graphAdapter'
import type { ArchitectureGraph, GraphSelection } from '../types/graphTypes'
import { ArchitectureEdge } from './ArchitectureEdge'
import { GraphNodeCard } from './GraphNodeCard'

interface ArchitectureGraphProps {
  graph: ArchitectureGraph
  selection: GraphSelection
  onSelectionChange: (selection: GraphSelection) => void
}

const nodeTypes = { architecture: GraphNodeCard }
const edgeTypes = { architecture: ArchitectureEdge }

const minimapNodeColor: Record<string, string> = {
  entrypoint: '#237a57',
  component: '#286c99',
  service: '#286c99',
  worker: '#9b5b24',
  queue: '#8a4f86',
  store: '#397881',
  external: '#a3413a',
  config: '#687145',
  shared: '#6b6259',
}

export function ArchitectureGraph({
  graph,
  selection,
  onSelectionChange,
}: ArchitectureGraphProps) {
  const elements = useMemo(() => graphToFlowElements(graph), [graph])

  const nodes = useMemo(
    () =>
      elements.nodes.map((node) => ({
        ...node,
        selected: selection?.kind === 'node' && selection.item.id === node.id,
      })),
    [elements.nodes, selection],
  )

  const edges = useMemo(
    () =>
      elements.edges.map((edge) => ({
        ...edge,
        selected: selection?.kind === 'edge' && selection.item.id === edge.id,
      })),
    [elements.edges, selection],
  )

  const handleNodeClick: NodeMouseHandler<ArchitectureFlowNode> = (_, flowNode) => {
    onSelectionChange({ kind: 'node', item: flowNode.data.architectureNode })
  }

  const handleEdgeClick: EdgeMouseHandler<ArchitectureFlowEdge> = (_, flowEdge) => {
    const edge = flowEdge.data?.architectureEdge
    if (edge) {
      onSelectionChange({ kind: 'edge', item: edge })
    }
  }

  return (
    <div className="graph-canvas" aria-label="Architecture graph">
      <ReactFlow<ArchitectureFlowNode, ArchitectureFlowEdge>
        className="graph-canvas__flow"
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={() => onSelectionChange(null)}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        fitView
        fitViewOptions={{ padding: 0.08, maxZoom: 1 }}
        minZoom={0.08}
        maxZoom={1.6}
      >
        <Background color="#cdd3cd" gap={22} size={1} variant={BackgroundVariant.Dots} />
        <Controls position="bottom-left" showInteractive={false} />
        <MiniMap
          position="top-left"
          pannable
          zoomable
          nodeColor={(node) => {
            const data = node.data as ArchitectureNodeData | undefined
            return minimapNodeColor[data?.architectureNode.type ?? ''] ?? '#647169'
          }}
          nodeStrokeWidth={0}
          maskColor="rgba(238, 241, 237, 0.76)"
        />
      </ReactFlow>
    </div>
  )
}
