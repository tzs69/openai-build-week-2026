import { AlertTriangle, ChevronRight, GitFork, LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useRef } from 'react'
import { loadGraphProjection } from '../api/graphClient'
import { createRun, loadRun } from '../api/runClient'
import type {
  ArchitectureGraph as ArchitectureGraphData,
  ArchitectureNode,
  GraphSelection,
} from '../types/graphTypes'
import type { RunSnapshot } from '../types/coordinationTypes'
import { ArchitectureGraph } from './ArchitectureGraph'
import { CoordinationPanel } from './CoordinationPanel'
import { DetailsPanel } from './DetailsPanel'

interface Breadcrumb {
  id: string | null
  label: string
}

const INITIAL_TRAIL: Breadcrumb[] = [{ id: null, label: 'Architecture' }]

function LoadingState() {
  return (
    <main className="status-screen" aria-live="polite">
      <div className="status-screen__content">
        <LoaderCircle aria-hidden="true" size={22} />
        <h1>Loading architecture</h1>
        <p>Requesting a validated projection from Merge Marshal.</p>
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
  const [graph, setGraph] = useState<ArchitectureGraphData | null>(null)
  const [selection, setSelection] = useState<GraphSelection>(null)
  const [run, setRun] = useState<RunSnapshot | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [trail, setTrail] = useState<Breadcrumb[]>(INITIAL_TRAIL)
  const [error, setError] = useState<string | null>(null)
  const runId = useRef<string | null>(null)
  const activeRoot = trail.at(-1)?.id ?? null

  useEffect(() => {
    const controller = new AbortController()
    setError(null)

    const runRequest = runId.current
      ? loadRun(runId.current, { root: activeRoot, depth: 1, signal: controller.signal })
      : createRun({ root: activeRoot, depth: 1, signal: controller.signal })

    Promise.all([
      loadGraphProjection({ root: activeRoot, depth: 1, signal: controller.signal }),
      runRequest,
    ])
      .then(([projection, snapshot]) => {
        if (!controller.signal.aborted) {
          setGraph(projection)
          setRun(snapshot)
          runId.current = snapshot.run_id
          setSelectedTaskId((current) => current ?? snapshot.tasks[0]?.id ?? null)
          setSelection(null)
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Failed to load architecture')
        }
      })

    return () => controller.abort()
  }, [activeRoot])

  const exploreNode = (node: ArchitectureNode) => {
    if (node.id === activeRoot || node.proposed) {
      return
    }
    setGraph(null)
    setTrail((current) => [...current, { id: node.id, label: node.label }])
  }

  const openBreadcrumb = (index: number) => {
    if (index === trail.length - 1) {
      return
    }
    setGraph(null)
    setTrail((current) => current.slice(0, index + 1))
  }

  if (error) {
    return <ErrorState message={error} />
  }

  if (!graph || !run || !selectedTaskId) {
    return <LoadingState />
  }

  return (
    <main className="graph-page">
      <header className="topbar">
        <div className="topbar__identity">
          <span className="topbar__mark">
            <GitFork aria-hidden="true" size={16} />
          </span>
          <div className="topbar__titles">
            <p className="topbar__eyebrow">Merge Marshal</p>
            <h1 title={graph.metadata.repo_name}>{graph.metadata.repo_name}</h1>
          </div>
        </div>
        <div className="topbar__stats" aria-label="Graph metadata">
          <span className="topbar__stat">
            Schema <strong>v{graph.schema_version}</strong>
          </span>
          <span className="topbar__stat">
            Nodes <strong>{graph.nodes.length}</strong>
          </span>
          <span className="topbar__stat">
            Edges <strong>{graph.edges.length}</strong>
          </span>
          <span className="topbar__stat">
            Tasks <strong>{run.tasks.length}</strong>
          </span>
        </div>
      </header>
      <div className="workspace">
        <CoordinationPanel
          run={run}
          selectedTaskId={selectedTaskId}
          onSelectTask={setSelectedTaskId}
        />
        <section className="graph-column" aria-label="Architecture explorer">
          <nav className="graph-toolbar" aria-label="Graph hierarchy">
            {trail.map((crumb, index) => (
              <span className="breadcrumb" key={crumb.id ?? 'architecture'}>
                {index > 0 && <ChevronRight aria-hidden="true" size={13} />}
                <button
                  className={index === trail.length - 1 ? 'is-current' : ''}
                  type="button"
                  onClick={() => openBreadcrumb(index)}
                  aria-current={index === trail.length - 1 ? 'page' : undefined}
                >
                  {crumb.label}
                </button>
              </span>
            ))}
            <span className="graph-toolbar__depth">Depth {graph.projection.depth}</span>
          </nav>
          <ArchitectureGraph
            graph={graph}
            selection={selection}
            onSelectionChange={setSelection}
            onExploreNode={exploreNode}
            run={run}
            selectedTaskId={selectedTaskId}
          />
        </section>
        <DetailsPanel
          selection={selection}
          onExploreNode={exploreNode}
          onClose={() => setSelection(null)}
          impacts={run.impacts}
          tasks={run.tasks}
          selectedTaskId={selectedTaskId}
        />
      </div>
    </main>
  )
}
