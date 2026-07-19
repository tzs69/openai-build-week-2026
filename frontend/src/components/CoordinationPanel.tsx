import {
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  GitCompareArrows,
  Layers3,
  Sparkles,
} from 'lucide-react'
import type { RunSnapshot } from '../types/coordinationTypes'

interface CoordinationPanelProps {
  run: RunSnapshot
  selectedTaskId: string
  onSelectTask: (taskId: string) => void
}

const interactionSymbol = {
  produce: '+',
  consume: '→',
  mutate: '~',
  retire: '−',
}

function shortTaskId(taskId: string) {
  return taskId.replace('task-', '').toUpperCase()
}

export function CoordinationPanel({
  run,
  selectedTaskId,
  onSelectTask,
}: CoordinationPanelProps) {
  const selectedTask = run.tasks.find((task) => task.id === selectedTaskId) ?? run.tasks[0]
  const contract = run.contracts.find((item) => item.task_id === selectedTask.id)
  const conflicts = run.conflicts.filter((item) => item.task_ids.includes(selectedTask.id))

  return (
    <aside className="coordination-panel" aria-label="Coordination plan">
      <header className="coordination-panel__header">
        <div>
          <p>Planning run</p>
          <h2>Change coordination</h2>
        </div>
        <span className="run-status">
          <Sparkles aria-hidden="true" size={11} />
          {run.status}
        </span>
      </header>

      <div className="coordination-panel__scroll">
        <section className="plan-section" aria-labelledby="tasks-heading">
          <div className="plan-section__heading">
            <h3 id="tasks-heading">Tasks</h3>
            <span>{run.tasks.length}</span>
          </div>
          <div className="task-list">
            {run.tasks.map((task) => (
              <button
                aria-pressed={task.id === selectedTask.id}
                className={`task-card${task.id === selectedTask.id ? ' is-selected' : ''}`}
                key={task.id}
                onClick={() => onSelectTask(task.id)}
                style={{ '--task-color': task.color } as React.CSSProperties}
                type="button"
              >
                <span className="task-card__identity">{shortTaskId(task.id)}</span>
                <span className="task-card__content">
                  <strong>{task.title}</strong>
                  <small>{task.instructions}</small>
                  <span className={`task-state task-state--${task.status.toLowerCase()}`}>
                    {task.status === 'READY' ? (
                      <CheckCircle2 aria-hidden="true" size={11} />
                    ) : (
                      <AlertOctagon aria-hidden="true" size={11} />
                    )}
                    {task.status}
                    {task.requires_replan && ' · replan required'}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="plan-section" aria-labelledby="schedule-heading">
          <div className="plan-section__heading">
            <h3 id="schedule-heading">Derived schedule</h3>
            <Layers3 aria-hidden="true" size={13} />
          </div>
          <div className="batch-list">
            {run.execution_batches.map((batch, index) => (
              <div className={`batch${batch.conditional ? ' is-conditional' : ''}`} key={batch.index}>
                <span className="batch__number">{batch.index}</span>
                <div>
                  <strong>{batch.task_ids.map(shortTaskId).join(' + ')}</strong>
                  <small>{batch.condition ?? 'Ready together'}</small>
                </div>
                {index < run.execution_batches.length - 1 && (
                  <ArrowRight aria-hidden="true" className="batch__arrow" size={12} />
                )}
              </div>
            ))}
          </div>
        </section>

        {contract && (
          <section className="plan-section" aria-labelledby="contract-heading">
            <div className="plan-section__heading">
              <h3 id="contract-heading">Task {shortTaskId(selectedTask.id)} contract</h3>
              <span>v{contract.version}</span>
            </div>
            <p className="contract-summary">{contract.summary}</p>
            <ul className="effect-list">
              {contract.effects.map((effect) => (
                <li key={effect.effect_id}>
                  <span className={`effect-operation effect-operation--${effect.interaction}`}>
                    {interactionSymbol[effect.interaction]}
                  </span>
                  <div>
                    <strong>{effect.interaction.replace('_', ' ')}</strong>
                    <p>{effect.intent}</p>
                    <code>
                      {effect.target.symbol ?? effect.target.path ?? effect.resource_id}
                    </code>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {conflicts.length > 0 && (
          <section className="plan-section" aria-labelledby="conflicts-heading">
            <div className="plan-section__heading">
              <h3 id="conflicts-heading">Coordination evidence</h3>
              <GitCompareArrows aria-hidden="true" size={13} />
            </div>
            <ul className="conflict-list">
              {conflicts.map((conflict) => (
                <li className={conflict.blocking ? 'is-blocking' : ''} key={conflict.id}>
                  <strong>{conflict.blocking ? 'Blocking conflict' : 'Review warning'}</strong>
                  <p>{conflict.reason}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="impact-legend" aria-label="Impact legend">
          <span><i className="legend-swatch is-direct" /> Direct</span>
          <span><i className="legend-swatch is-downstream" /> Downstream</span>
          <span><i className="legend-swatch is-uncertain" /> Uncertain</span>
          <span><i className="legend-swatch is-proposed" /> Proposed</span>
        </section>
      </div>
    </aside>
  )
}
