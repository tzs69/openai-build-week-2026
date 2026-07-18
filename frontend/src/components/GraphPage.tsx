import { AlertTriangle, GitFork, LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { FIXTURE_REPOSITORY_LABEL, loadGraphBundle } from '../data/graphData'
import type { GraphBundle, GraphSelection } from '../types/graphTypes'
import { ArchitectureGraph } from './ArchitectureGraph'
import { DetailsPanel } from './DetailsPanel'

function LoadingState() {
  return (
    <main className="status-screen" aria-live="polite">
      <div className="status-screen__content">
        <LoaderCircle aria-hidden="true" size={22} />
        <h1>Loading architecture</h1>
        <p>Reading the graph and reverse artifact index.</p>
      </div>
    </main>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <main className="status-screen status-screen--error" role="alert">
      <div className="status-screen__content">
        <AlertTriangle aria-hidden="true" size={22} />
        <h1>Architecture unavailable</h1>
        <p>{message}</p>
      </div>
    </main>
  )
}

export function GraphPage() {
  const [bundle, setBundle] = useState<GraphBundle | null>(null)
  const [selection, setSelection] = useState<GraphSelection>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    loadGraphBundle()
      .then((loadedBundle) => {
        if (!controller.signal.aborted) {
          setBundle(loadedBundle)
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Failed to load graph fixtures')
        }
      })

    return () => controller.abort()
  }, [])

  if (error) {
    return <ErrorState message={error} />
  }

  if (!bundle) {
    return <LoadingState />
  }

  const { graph, reverse } = bundle
  const repositoryLabel =
    graph.metadata.repository ??
    (graph.metadata.repository_root && graph.metadata.repository_root !== '.'
      ? graph.metadata.repository_root
      : FIXTURE_REPOSITORY_LABEL)

  return (
    <main className="graph-page">
      <header className="topbar">
        <div className="topbar__identity">
          <span className="topbar__mark">
            <GitFork aria-hidden="true" size={16} />
          </span>
          <div className="topbar__titles">
            <p className="topbar__eyebrow">Merge Marshal</p>
            <h1 title={repositoryLabel}>{repositoryLabel}</h1>
          </div>
        </div>
        <div className="topbar__stats" aria-label="Graph metadata">
          <span className="topbar__stat">
            Schema <strong>v{graph.metadata.schema_version}</strong>
          </span>
          <span className="topbar__stat">
            Nodes <strong>{graph.nodes.length}</strong>
          </span>
          <span className="topbar__stat">
            Edges <strong>{graph.edges.length}</strong>
          </span>
        </div>
      </header>
      <div className="workspace">
        <ArchitectureGraph
          graph={graph}
          selection={selection}
          onSelectionChange={setSelection}
        />
        <DetailsPanel
          selection={selection}
          reverse={reverse}
          warnings={graph.warnings}
          onClose={() => setSelection(null)}
        />
      </div>
    </main>
  )
}
