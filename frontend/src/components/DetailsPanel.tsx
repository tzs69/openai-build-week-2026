import { FileCode2, Network, X } from 'lucide-react'
import type {
  ArtifactReference,
  GraphReverseMap,
  GraphSelection,
  GraphWarning,
} from '../types/graphTypes'

interface DetailsPanelProps {
  selection: GraphSelection
  reverse: GraphReverseMap
  warnings: GraphWarning[]
  onClose: () => void
}

interface ArtifactListProps {
  artifacts: ArtifactReference[]
  reverse: GraphReverseMap
}

function ArtifactList({ artifacts, reverse }: ArtifactListProps) {
  return (
    <ul className="artifact-list">
      {artifacts.map((artifact) => {
        const reverseEntry = reverse.artifacts[artifact.path]
        const relatedEdgeCount = reverseEntry?.edges.length ?? 0

        return (
          <li className="artifact-item" key={`${artifact.path}:${artifact.symbols.join('|')}`}>
            <div className="artifact-item__path">
              <FileCode2 aria-hidden="true" size={13} />
              <code>{artifact.path}</code>
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
            {reverseEntry && (
              <p className="artifact-item__related">
                Reverse index: {reverseEntry.nodes.length} node
                {reverseEntry.nodes.length === 1 ? '' : 's'}, {relatedEdgeCount} edge
                {relatedEdgeCount === 1 ? '' : 's'}
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function Warnings({ warnings }: { warnings: GraphWarning[] }) {
  if (warnings.length === 0) {
    return null
  }

  return (
    <section className="warnings">
      <div className="detail-section__heading">
        <h3 className="detail-section__title">Generation warnings</h3>
        <span className="detail-section__count">{warnings.length}</span>
      </div>
      <ul className="warning-list">
        {warnings.map((warning) => {
          const message = typeof warning === 'string' ? warning : warning.message
          const evidence = typeof warning === 'string' ? [] : (warning.evidence ?? [])

          return (
            <li key={message}>
              <span>{message}</span>
              {evidence.length > 0 && (
                <div className="warning-list__evidence">
                  {evidence.map((item) => (
                    <code key={item.path}>{item.path}</code>
                  ))}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export function DetailsPanel({
  selection,
  reverse,
  warnings,
  onClose,
}: DetailsPanelProps) {
  if (!selection) {
    return (
      <aside className="details-panel is-empty" aria-label="Graph details">
        <div className="empty-selection">
          <div className="empty-selection__icon">
            <Network aria-hidden="true" size={20} />
          </div>
          <h2>Inspect the architecture</h2>
          <p>Select a component or relationship to view its code evidence.</p>
        </div>
        <div className="details-panel__body">
          <Warnings warnings={warnings} />
        </div>
      </aside>
    )
  }

  const isNode = selection.kind === 'node'
  const item = selection.item
  const artifacts = isNode ? selection.item.artifacts : selection.item.evidence

  return (
    <aside className="details-panel" aria-label={`${isNode ? 'Node' : 'Edge'} details`}>
      <header className="details-panel__header">
        <div>
          <p className="details-panel__kind">{isNode ? 'Component' : 'Relationship'}</p>
          <h2>{isNode ? selection.item.label : selection.item.type}</h2>
        </div>
        <button className="icon-button" type="button" onClick={onClose} title="Close details">
          <X aria-hidden="true" size={16} />
          <span className="sr-only">Close details</span>
        </button>
      </header>
      <div className="details-panel__body">
        <p className="details-panel__description">{item.description}</p>

        <div className="detail-grid">
          <div className="detail-grid__item">
            <span>ID</span>
            <code>{item.id}</code>
          </div>
          <div className="detail-grid__item">
            <span>Type</span>
            <strong>{item.type}</strong>
          </div>
          {!isNode && (
            <>
              <div className="detail-grid__item">
                <span>Source</span>
                <code>{selection.item.source}</code>
              </div>
              <div className="detail-grid__item">
                <span>Target</span>
                <code>{selection.item.target}</code>
              </div>
            </>
          )}
        </div>

        <section className="detail-section">
          <div className="detail-section__heading">
            <h3 className="detail-section__title">{isNode ? 'Artifacts' : 'Evidence'}</h3>
            <span className="detail-section__count">{artifacts.length}</span>
          </div>
          <ArtifactList artifacts={artifacts} reverse={reverse} />
        </section>

        <Warnings warnings={warnings} />
      </div>
    </aside>
  )
}
