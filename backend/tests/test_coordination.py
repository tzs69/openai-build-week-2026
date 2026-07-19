from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from hierarchical_graph.store import load_graph

from merge_marshal_api import create_app
from merge_marshal_api.coordination.engine import (
    InvalidContractError,
    build_dependencies,
    detect_conflicts,
    resolve_impacts,
    topological_batches,
    validate_contracts,
)
from merge_marshal_api.coordination.fixtures import demo_contracts, demo_tasks


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_REPOSITORY = PROJECT_ROOT / "demo" / "target-repo"


class CoordinationEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = load_graph(DEMO_REPOSITORY)
        self.contracts = demo_contracts()

    def test_demo_contracts_validate_including_proposed_architecture(self) -> None:
        validate_contracts(self.contracts, self.graph, DEMO_REPOSITORY)

        cache_effect = next(
            effect
            for contract in self.contracts
            for effect in contract.effects
            if effect.effect_id == "task-b-create-cache-node"
        )
        self.assertEqual(cache_effect.architecture_change.action, "create")
        self.assertEqual(
            cache_effect.architecture_change.node.id,
            "proposed-task-b-user-cache",
        )

    def test_contract_validation_rejects_unknown_graph_targets(self) -> None:
        invalid = self.contracts[0].model_copy(deep=True)
        invalid.effects[0].target.node_id = "not-a-real-node"

        with self.assertRaisesRegex(InvalidContractError, "unknown node"):
            validate_contracts([invalid], self.graph, DEMO_REPOSITORY)

    def test_conflict_and_dependency_are_derived_from_resource_interactions(self) -> None:
        conflicts = detect_conflicts(self.contracts, self.graph)
        dependencies = build_dependencies(self.contracts, conflicts)

        blocking = [conflict for conflict in conflicts if conflict.blocking]
        self.assertEqual(len(blocking), 1)
        self.assertEqual(blocking[0].type, "retired_resource_consumed")
        self.assertEqual(blocking[0].blocker_task_id, "task-a")
        self.assertEqual(blocking[0].blocked_task_id, "task-b")
        self.assertEqual(len(dependencies), 1)
        self.assertTrue(dependencies[0].replan_required)

    def test_schedule_keeps_the_stale_consumer_conditional(self) -> None:
        conflicts = detect_conflicts(self.contracts, self.graph)
        dependencies = build_dependencies(self.contracts, conflicts)
        batches = topological_batches(demo_tasks(), dependencies)

        self.assertEqual(batches[0].task_ids, ["task-a", "task-c"])
        self.assertFalse(batches[0].conditional)
        self.assertEqual(batches[1].task_ids, ["task-b"])
        self.assertTrue(batches[1].conditional)

    def test_impacts_are_mapped_to_the_requested_hierarchy_projection(self) -> None:
        top_level = resolve_impacts(self.contracts, self.graph, root=None, depth=1)
        drilled = resolve_impacts(
            self.contracts,
            self.graph,
            root="user-domain",
            depth=1,
        )

        top_schema = next(
            impact
            for impact in top_level
            if impact.effect_id == "task-a-retire-user-id"
            and impact.classification == "direct"
        )
        drilled_schema = next(
            impact
            for impact in drilled
            if impact.effect_id == "task-a-retire-user-id"
            and impact.classification == "direct"
        )
        self.assertEqual(top_schema.visible_node_id, "user-domain")
        self.assertEqual(drilled_schema.visible_node_id, "user-response-schema")

        proposed_edge = next(
            impact.proposed_edge
            for impact in drilled
            if impact.effect_id == "task-b-create-cache-edge"
        )
        self.assertEqual(proposed_edge.source, "user-service")
        self.assertEqual(proposed_edge.target, "proposed-task-b-user-cache")


class CoordinationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(DEMO_REPOSITORY))

    def test_creates_and_retrieves_an_in_memory_planning_run(self) -> None:
        created = self.client.post("/api/runs", params={"depth": 1})

        self.assertEqual(created.status_code, 201)
        payload = created.json()
        states = {task["id"]: task["status"] for task in payload["tasks"]}
        self.assertEqual(
            states,
            {"task-a": "READY", "task-b": "BLOCKED", "task-c": "READY"},
        )
        self.assertTrue(
            next(task for task in payload["tasks"] if task["id"] == "task-b")[
                "requires_replan"
            ]
        )

        retrieved = self.client.get(
            f"/api/runs/{payload['run_id']}",
            params={"root": "user-domain", "depth": 1},
        )
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(
            retrieved.json()["projection"],
            {"root": "user-domain", "depth": 1},
        )

    def test_unknown_run_returns_not_found(self) -> None:
        response = self.client.get("/api/runs/run-missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("does not exist", response.json()["detail"])

    def test_run_projection_rejects_an_unknown_root(self) -> None:
        response = self.client.post(
            "/api/runs", params={"root": "missing-domain", "depth": 1}
        )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
