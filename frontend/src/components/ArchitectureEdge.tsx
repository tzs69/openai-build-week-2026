import { BaseEdge, EdgeLabelRenderer, type EdgeProps, type XYPosition } from '@xyflow/react'
import type { ArchitectureFlowEdge } from '../data/graphAdapter'

function pointToward(from: XYPosition, to: XYPosition, distance: number): XYPosition {
  const deltaX = to.x - from.x
  const deltaY = to.y - from.y
  const length = Math.hypot(deltaX, deltaY) || 1
  const scale = Math.min(distance, length / 2) / length

  return {
    x: from.x + deltaX * scale,
    y: from.y + deltaY * scale,
  }
}

function roundedPath(points: XYPosition[], radius = 10): string {
  if (points.length < 2) {
    return ''
  }

  let path = `M ${points[0].x} ${points[0].y}`

  for (let index = 1; index < points.length - 1; index += 1) {
    const previous = points[index - 1]
    const current = points[index]
    const next = points[index + 1]
    const cornerStart = pointToward(current, previous, radius)
    const cornerEnd = pointToward(current, next, radius)

    path += ` L ${cornerStart.x} ${cornerStart.y}`
    path += ` Q ${current.x} ${current.y} ${cornerEnd.x} ${cornerEnd.y}`
  }

  const lastPoint = points.at(-1)!
  return `${path} L ${lastPoint.x} ${lastPoint.y}`
}

export function ArchitectureEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
  style,
  data,
  selected,
  interactionWidth,
}: EdgeProps<ArchitectureFlowEdge>) {
  const routePoints = data?.routePoints ?? []
  const points = routePoints.length >= 2
    ? routePoints
    : [{ x: sourceX, y: sourceY }, { x: targetX, y: targetY }]
  const path = roundedPath(points)
  const labelPosition = data?.labelPosition ?? {
    x: (sourceX + targetX) / 2,
    y: (sourceY + targetY) / 2,
  }

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        interactionWidth={interactionWidth}
        style={style}
      />
      <EdgeLabelRenderer>
        <span
          className={`architecture-edge__label${selected ? ' is-selected' : ''}`}
          data-edge-label={id}
          style={{
            transform: `translate(-50%, -50%) translate(${labelPosition.x}px, ${labelPosition.y}px)`,
          }}
        >
          {data?.architectureEdge.type}
        </span>
      </EdgeLabelRenderer>
    </>
  )
}
