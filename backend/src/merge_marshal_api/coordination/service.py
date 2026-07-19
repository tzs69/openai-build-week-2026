from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from ..graph_service import GraphService
from .engine import (
    assign_task_states,
    build_dependencies,
    detect_conflicts,
    resolve_impacts,
    topological_batches,
    validate_contracts,
)
from .fixtures import demo_contracts, demo_tasks
from .models import ChangeContract, Conflict, Dependency, ExecutionBatch, RunSnapshot, Task


class RunNotFoundError(Exception):
    """The requested in-memory coordination run does not exist."""


@dataclass(frozen=True)
class StoredRun:
    run_id: str
    tasks: list[Task]
    contracts: list[ChangeContract]
    conflicts: list[Conflict]
    dependencies: list[Dependency]
    batches: list[ExecutionBatch]


class CoordinationService:
    def __init__(self, graph_service: GraphService) -> None:
        self.graph_service = graph_service
        self._runs: dict[str, StoredRun] = {}
        self._lock = Lock()

    def create_run(self, root: str | None, depth: int) -> RunSnapshot:
        graph = self.graph_service.load()
        # Validate the requested view at the same boundary as GET /api/graph.
        self.graph_service.project(root=root, depth=depth)
        tasks = demo_tasks()
        contracts = demo_contracts()
        validate_contracts(contracts, graph, self.graph_service.repository)
        conflicts = detect_conflicts(contracts, graph)
        dependencies = build_dependencies(contracts, conflicts)
        tasks = assign_task_states(tasks, conflicts, dependencies)
        batches = topological_batches(tasks, dependencies)
        run_id = f"run-{uuid4().hex[:12]}"
        stored = StoredRun(
            run_id=run_id,
            tasks=tasks,
            contracts=contracts,
            conflicts=conflicts,
            dependencies=dependencies,
            batches=batches,
        )
        with self._lock:
            self._runs[run_id] = stored
        return self._snapshot(stored, graph, root, depth)

    def get_run(self, run_id: str, root: str | None, depth: int) -> RunSnapshot:
        with self._lock:
            stored = self._runs.get(run_id)
        if stored is None:
            raise RunNotFoundError(f"coordination run '{run_id}' does not exist")
        graph = self.graph_service.load()
        self.graph_service.project(root=root, depth=depth)
        return self._snapshot(stored, graph, root, depth)

    @staticmethod
    def _snapshot(
        stored: StoredRun,
        graph: dict,
        root: str | None,
        depth: int,
    ) -> RunSnapshot:
        return RunSnapshot(
            run_id=stored.run_id,
            projection={"root": root, "depth": depth},
            tasks=stored.tasks,
            contracts=stored.contracts,
            impacts=resolve_impacts(stored.contracts, graph, root, depth),
            conflicts=stored.conflicts,
            dependencies=stored.dependencies,
            execution_batches=stored.batches,
        )
