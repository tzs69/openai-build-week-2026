import { FileCode2, FolderTree, Network, X } from 'lucide-react'
import type {
  ArchitectureNode,
  ArtifactReference,
  GraphSelection,
} from '../types/graphTypes'
import type { DiagramImpact, Task } from '../types/coordinationTypes'

interface DetailsPanelProps {
  selection: GraphSelection
  onClose: () => void
  onExploreNode: (node: ArchitectureNode) => void
  impacts: DiagramImpact[]
  tasks: Task[]
  selectedTaskId: string
}

function ArtifactList({ artifacts }: { artifacts: ArtifactReference[] }) {
  return (
    <ul className="artifact-list">
      {artifacts.map((artifact) => (
        <li className="artifact-item" key={`${artifact.path}:${artifact.symbols.join('|')}`}>
          <div className="artifact-item__path">
            <FileCode2 aria-hidden="true" size={13} />
            <code>{artifact.path}</code>
            {artifact.ownership && (
              <span className={`ownership ownership--${artifact.ownership}`}>
                {artifact.ownership}
              </span>
            )}
          </div>
          {artifact.symbols.length > 0 && (
            <div className="symbol-list" aria-label="Symbols">
              {artifact.symbols.map((symbol) => (
                <code className="symbol" key={symbol}>
                  {symbol}
                </code>
              ))}
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}

export function DetailsPanel({
  selection,
  onClose,
  onExploreNode,
  impacts,
  tasks,
  selectedTaskId,
}: DetailsPanelProps) {
  if (!selection) {
    return (
      <aside className="details-panel is-empty" aria-label="Graph details">
        <div className="empty-selection">
          <div className="empty-selection__icon">
            <Network aria-hidden="true" size={20} />
          </div>
          <h2>Inspect the architecture</h2>
          <p>Select a component or relationship to view its verified code evidence.</p>
        </div>
      </aside>
    )
  }

  const isNode = selection.kind === 'node'
  const item = selection.item
  const artifacts = isNode ? selection.item.scope.artifacts : selection.item.evidence
  const description = isNode ? selection.item.description : selection.item.label
  const selectedTask = tasks.find((task) => task.id === selectedTaskId)
  const relevantImpacts = impacts.filter((impact) => {
    if (impact.task_id !== selectedTaskId) {
      return false
    }
    if (isNode) {
      return (
        impact.visible_node_id === selection.item.id ||
        impact.proposed_node?.id === selection.item.id
      )
    }
    const canonicalEdgeIds = new Set([
      selection.item.id,
      ...(selection.item.aggregated_edge_ids ?? []),
    ])
    return (
      impact.proposed_edge?.id === selection.item.id ||
      impact.evidence.some(
        (evidence) => evidence.edge_id && canonicalEdgeIds.has(evidence.edge_id),
      )
    )
  })

  return (
    <aside className="details-panel" aria-label={`${isNode ? 'Node' : 'Edge'} details`}>
      <header className="details-panel__header">
        <div>
          <p className="details-panel__kind">
            {item.proposed ? 'Proposed change' : isNode ? 'Component' : 'Relationship'}
          </p>
          <h2>{isNode ? selection.item.label : selection.item.type}</h2>
        </div>
        <button className="icon-button" type="button" onClick={onClose} title="Close details">
          <X aria-hidden="true" size={16} />
          <span className="sr-only">Close details</span>
        </button>
      </header>
      <div className="details-panel__body">
        <p className="details-panel__description">{description}</p>

        <div className="detail-grid">
          <div className="detail-grid__item">
            <span>ID</span>
            <code>{item.id}</code>
          </div>
          <div className="detail-grid__item">
            <span>Type</span>
            <strong>{item.type}</strong>
          </div>
          {isNode ? (
            <div className="detail-grid__item">
              <span>Parent</span>
              <code>{selection.item.parent_id ?? 'top level'}</code>
            </div>
          ) : (
            <>
              <div className="detail-grid__item">
                <span>Source</span>
                <code>{selection.item.source}</code>
              </div>
              <div className="detail-grid__item">
                <span>Target</span>
                <code>{selection.item.target}</code>
              </div>
              <div className="detail-grid__item">
                <span>Canonical edges</span>
                <strong>{selection.item.aggregated_edge_ids?.length ?? 1}</strong>
              </div>
            </>
          )}
        </div>

        {isNode && selection.item.type === 'component' && (
          <button
            className="explore-button"
            type="button"
            onClick={() => onExploreNode(selection.item)}
          >
            <FolderTree aria-hidden="true" size={14} />
            Explore this component
          </button>
        )}

        <section className="detail-section">
          <div className="detail-section__heading">
            <h3 className="detail-section__title">{isNode ? 'Executor scope' : 'Evidence'}</h3>
            <span className="detail-section__count">{artifacts.length}</span>
          </div>
          <ArtifactList artifacts={artifacts} />
          {item.proposed && artifacts.length === 0 && (
            <p className="proposed-empty">No verified artifact exists yet. This is a plan overlay.</p>
          )}
        </section>

        {relevantImpacts.length > 0 && selectedTask && (
          <section className="detail-section impact-evidence">
            <div className="detail-section__heading">
              <h3 className="detail-section__title">Task {selectedTask.id.replace('task-', '').toUpperCase()} impact</h3>
              <span className="detail-section__count">{relevantImpacts.length}</span>
            </div>
            <ul>
              {relevantImpacts.map((impact) => (
                <li key={`${impact.effect_id}:${impact.canonical_node_id}`}>
                  <div>
                    <span className={`impact-classification impact-classification--${impact.classification}`}>
                      {impact.classification}
                    </span>
                    <span className="impact-operation">{impact.interaction}</span>
                  </div>
                  <p>{impact.reason}</p>
                  {impact.evidence.map((evidence) => (
                    <small key={`${evidence.kind}:${evidence.edge_id ?? evidence.description}`}>
                      {evidence.description}
                    </small>
                  ))}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </aside>
  )
}
