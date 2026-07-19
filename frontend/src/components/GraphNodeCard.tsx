import {
  Box,
  Cable,
  Database,
  FileCode2,
  Globe2,
  HardDrive,
  Settings2,
  TerminalSquare,
  Workflow,
  type LucideIcon,
} from 'lucide-react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { CSSProperties } from 'react'
import type { ArchitectureFlowNode, HandleSide } from '../data/graphAdapter'

const iconByType: Record<string, LucideIcon> = {
  entrypoint: TerminalSquare,
  component: Box,
  service: Workflow,
  worker: Workflow,
  queue: Cable,
  store: Database,
  external: Globe2,
  config: Settings2,
  shared: HardDrive,
}

const positionBySide: Record<HandleSide, Position> = {
  left: Position.Left,
  right: Position.Right,
  top: Position.Top,
  bottom: Position.Bottom,
}

export function GraphNodeCard({ data, selected }: NodeProps<ArchitectureFlowNode>) {
  const node = data.architectureNode
  const Icon = iconByType[node.type] ?? FileCode2
  const activeImpacts = data.impacts.filter(
    ({ task }) => task.id === data.activeTaskId,
  )
  const impactRank = { direct: 0, downstream: 1, uncertain: 2 }
  const primaryImpact = [...activeImpacts].sort(
    (first, second) =>
      impactRank[first.impact.classification] - impactRank[second.impact.classification],
  )[0]
  const impactedTasks = [...new Map(data.impacts.map((item) => [item.task.id, item.task])).values()]
  const impactClasses = primaryImpact
    ? ` has-impact impact-${primaryImpact.impact.classification} operation-${primaryImpact.impact.interaction}`
    : ''
  const style = primaryImpact
    ? ({ '--impact-color': primaryImpact.task.color } as CSSProperties)
    : undefined

  return (
    <article
      className={`architecture-node node-type-${node.type}${node.proposed ? ' is-proposed' : ''}${impactClasses}${selected ? ' is-selected' : ''}`}
      aria-label={`${node.label}, ${node.type}`}
      style={style}
    >
      {data.handles.target.map((side) => (
        <Handle
          className="architecture-node__handle"
          id={`target-${side}`}
          key={`target-${side}`}
          type="target"
          position={positionBySide[side]}
        />
      ))}
      <div className="architecture-node__meta">
        <span className="architecture-node__type">
          <Icon aria-hidden="true" size={12} strokeWidth={2} />
          {node.type}
        </span>
        <code className="architecture-node__id">{node.id}</code>
      </div>
      <h2>{node.label}</h2>
      <p>{node.description}</p>
      {impactedTasks.length > 0 && (
        <div className="node-impact-markers" aria-label="Planned task impacts">
          {impactedTasks.map((task) => (
            <span
              key={task.id}
              style={{ backgroundColor: task.color }}
              title={`Task ${task.id.replace('task-', '').toUpperCase()}`}
            >
              {task.id.replace('task-', '').toUpperCase()}
            </span>
          ))}
        </div>
      )}
      {data.handles.source.map((side) => (
        <Handle
          className="architecture-node__handle"
          id={`source-${side}`}
          key={`source-${side}`}
          type="source"
          position={positionBySide[side]}
        />
      ))}
    </article>
  )
}
