from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hierarchical_graph import store
from hierarchical_graph.validate import validate_graph


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PACKAGE_ROOT / "references" / "python-agent-app"


class HGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        (self.repo / "backend" / "orchestration").mkdir(parents=True)
        (self.repo / "backend" / "conflicts").mkdir(parents=True)
        (self.repo / "backend" / "orchestration" / "planner.py").write_text(
            "def plan_change(): pass\n", encoding="utf-8"
        )
        (self.repo / "backend" / "orchestration" / "decompose.py").write_text(
            "def decompose_request(): pass\n", encoding="utf-8"
        )
        (self.repo / "backend" / "conflicts" / "detector.py").write_text(
            "class ConflictDetector: pass\n", encoding="utf-8"
        )
        result = self.run_cli(
            "init",
            "--repo",
            str(self.repo),
            "--language",
            "python",
            "--source-root",
            "backend/",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(
        self, *arguments: str, payload: dict | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-m", "hierarchical_graph", *arguments],
            input=json.dumps(payload) if payload is not None else None,
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )

    def put_node(
        self,
        node_id: str,
        parent: str | None,
        *,
        path: str | None,
        node_type: str = "component",
        symbols: list[str] | None = None,
        ownership: str = "primary",
    ) -> subprocess.CompletedProcess[str]:
        artifacts = []
        if path is not None:
            artifacts.append(
                {
                    "path": path,
                    "symbols": symbols or [],
                    "ownership": ownership,
                }
            )
        return self.run_cli(
            "put-node",
            "--repo",
            str(self.repo),
            "--parent",
            parent or "null",
            "--input",
            "-",
            payload={
                "id": node_id,
                "label": node_id.replace("-", " ").title(),
                "type": node_type,
                "description": f"Responsibility for {node_id}.",
                "scope": {"artifacts": artifacts},
            },
        )

    def put_edge(
        self, edge_id: str, source: str, target: str, evidence_path: str
    ) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "put-edge",
            "--repo",
            str(self.repo),
            "--input",
            "-",
            payload={
                "id": edge_id,
                "source": source,
                "target": target,
                "type": "calls",
                "label": "Calls target",
                "evidence": [
                    {"path": evidence_path, "symbols": ["call_target"]}
                ],
            },
        )

    def read_graph(self) -> dict:
        return json.loads(
            (self.repo / ".graph" / "graph.json").read_text(encoding="utf-8")
        )

    def test_reference_fixture_and_selective_class_granularity(self) -> None:
        app = FIXTURE_ROOT / "app"
        graph = json.loads(
            (FIXTURE_ROOT / "expected_out" / "graph.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validate_graph(graph, app), [])
        node_ids = {node["id"] for node in graph["nodes"]}
        self.assertIn("conflict-detector", node_ids)
        self.assertNotIn("change-contract", node_ids)
        shared_symbols = {
            symbol
            for node in graph["nodes"]
            for artifact in node["scope"]["artifacts"]
            if artifact["ownership"] == "shared"
            for symbol in artifact["symbols"]
        }
        self.assertIn("ChangeContract", shared_symbols)
        self.assertEqual(set(graph), {"schema_version", "metadata", "nodes", "edges"})

    def test_cli_builds_valid_graph_and_exposes_scope(self) -> None:
        self.assertEqual(self.put_node("backend", None, path="backend/").returncode, 0)
        result = self.put_node(
            "planner-execution",
            "backend",
            path="backend/orchestration/planner.py",
            node_type="service",
            symbols=["plan_change"],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        validation = self.run_cli("validate", "--repo", str(self.repo))
        self.assertEqual(validation.returncode, 0, validation.stderr)

        tree = self.run_cli("tree", "--repo", str(self.repo))
        self.assertIn("planner-execution", tree.stdout)
        shown = self.run_cli(
            "show", "--repo", str(self.repo), "planner-execution"
        )
        artifact = json.loads(shown.stdout)["node"]["scope"]["artifacts"][0]
        self.assertEqual(artifact["path"], "backend/orchestration/planner.py")
        self.assertEqual(artifact["symbols"], ["plan_change"])

    def test_cycle_rejection_and_safe_deletion(self) -> None:
        self.assertEqual(self.put_node("backend", None, path="backend/").returncode, 0)
        self.assertEqual(
            self.put_node(
                "planner-execution",
                "backend",
                path="backend/orchestration/planner.py",
                node_type="service",
            ).returncode,
            0,
        )
        cycle = self.put_node("backend", "planner-execution", path="backend/")
        self.assertNotEqual(cycle.returncode, 0)
        backend = next(
            node for node in self.read_graph()["nodes"] if node["id"] == "backend"
        )
        self.assertIsNone(backend["parent_id"])

        edge = self.put_edge(
            "planner-calls-backend",
            "planner-execution",
            "backend",
            "backend/orchestration/planner.py",
        )
        self.assertEqual(edge.returncode, 0, edge.stderr)
        refused = self.run_cli(
            "delete-node", "--repo", str(self.repo), "backend"
        )
        self.assertNotEqual(refused.returncode, 0)
        cascaded = self.run_cli(
            "delete-node", "--repo", str(self.repo), "backend", "--cascade"
        )
        self.assertEqual(cascaded.returncode, 0, cascaded.stderr)
        self.assertEqual(self.read_graph()["nodes"], [])
        self.assertEqual(self.read_graph()["edges"], [])

    def test_init_refuses_overwrite_and_edge_deletion_is_explicit(self) -> None:
        second_init = self.run_cli("init", "--repo", str(self.repo))
        self.assertNotEqual(second_init.returncode, 0)
        self.assertIn("already exists", second_init.stderr)

        self.assertEqual(self.put_node("backend", None, path="backend/").returncode, 0)
        self.assertEqual(
            self.put_node(
                "planner-execution",
                "backend",
                path="backend/orchestration/planner.py",
                node_type="service",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.put_edge(
                "backend-calls-planner",
                "backend",
                "planner-execution",
                "backend/orchestration/planner.py",
            ).returncode,
            0,
        )
        deleted = self.run_cli(
            "delete-edge", "--repo", str(self.repo), "backend-calls-planner"
        )
        self.assertEqual(deleted.returncode, 0, deleted.stderr)
        self.assertEqual(self.read_graph()["edges"], [])

    def test_projection_lifts_and_aggregates_hidden_edges(self) -> None:
        self.assertEqual(self.put_node("backend", None, path="backend/").returncode, 0)
        self.assertEqual(
            self.put_node(
                "agent-orchestration", "backend", path="backend/orchestration/"
            ).returncode,
            0,
        )
        self.assertEqual(
            self.put_node(
                "planner-execution",
                "agent-orchestration",
                path="backend/orchestration/planner.py",
                node_type="service",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.put_node(
                "task-decomposition",
                "agent-orchestration",
                path="backend/orchestration/decompose.py",
                node_type="service",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.put_node(
                "model-provider", None, path=None, node_type="external"
            ).returncode,
            0,
        )
        self.assertEqual(
            self.put_edge(
                "planner-calls-provider",
                "planner-execution",
                "model-provider",
                "backend/orchestration/planner.py",
            ).returncode,
            0,
        )
        self.assertEqual(
            self.put_edge(
                "decomposition-calls-provider",
                "task-decomposition",
                "model-provider",
                "backend/orchestration/decompose.py",
            ).returncode,
            0,
        )

        projection = self.run_cli(
            "project", "--repo", str(self.repo), "--depth", "1"
        )
        self.assertEqual(projection.returncode, 0, projection.stderr)
        result = json.loads(projection.stdout)
        self.assertEqual(
            {node["id"] for node in result["nodes"]},
            {"backend", "agent-orchestration", "model-provider"},
        )
        self.assertEqual(len(result["edges"]), 1)
        projected_edge = result["edges"][0]
        self.assertEqual(projected_edge["source"], "agent-orchestration")
        self.assertEqual(projected_edge["target"], "model-provider")
        self.assertEqual(
            projected_edge["aggregated_edge_ids"],
            ["decomposition-calls-provider", "planner-calls-provider"],
        )

    def test_validation_rejects_warnings_and_invalid_edges(self) -> None:
        self.assertEqual(self.put_node("backend", None, path="backend/").returncode, 0)
        graph = self.read_graph()
        graph["warnings"] = []
        (self.repo / ".graph" / "graph.json").write_text(
            json.dumps(graph), encoding="utf-8"
        )
        validation = self.run_cli("validate", "--repo", str(self.repo))
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("unsupported keys: warnings", validation.stdout)

        missing_target = self.put_edge(
            "backend-calls-missing",
            "backend",
            "missing-node",
            "backend/orchestration/planner.py",
        )
        self.assertNotEqual(missing_target.returncode, 0)

    def test_atomic_write_uses_replace(self) -> None:
        graph = self.read_graph()
        original_replace = os.replace
        with mock.patch.object(store.os, "replace", wraps=original_replace) as replace:
            store.atomic_write(self.repo, graph)
        replace.assert_called_once()
        self.assertEqual(list((self.repo / ".graph").glob(".graph.json.*.tmp")), [])

    def test_executor_scope_is_recoverable_from_graph_alone(self) -> None:
        graph = json.loads(
            (FIXTURE_ROOT / "expected_out" / "graph.json").read_text(encoding="utf-8")
        )
        target = next(
            node for node in graph["nodes"] if node["id"] == "conflict-detector"
        )
        primary = [
            artifact["path"]
            for artifact in target["scope"]["artifacts"]
            if artifact["ownership"] == "primary"
        ]
        shared = [
            artifact["path"]
            for artifact in target["scope"]["artifacts"]
            if artifact["ownership"] == "shared"
        ]
        adjacent = {
            edge["source"] if edge["target"] == target["id"] else edge["target"]
            for edge in graph["edges"]
            if target["id"] in {edge["source"], edge["target"]}
        }
        self.assertEqual(primary, ["backend/conflicts/detector.py"])
        self.assertEqual(shared, ["backend/contracts/models.py"])
        self.assertEqual(adjacent, {"planner-execution"})


if __name__ == "__main__":
    unittest.main()
