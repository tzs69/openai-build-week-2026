from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from hierarchical_graph.project import build_projection
from hierarchical_graph.store import load_graph

from merge_marshal_api import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_REPOSITORY = PROJECT_ROOT / "demo" / "target-repo"


class GraphApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(DEMO_REPOSITORY))

    def test_serves_the_toolkit_depth_projection(self) -> None:
        response = self.client.get("/api/graph", params={"depth": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            build_projection(load_graph(DEMO_REPOSITORY), root=None, depth=1),
        )

    def test_serves_a_rooted_projection(self) -> None:
        response = self.client.get(
            "/api/graph",
            params={"root": "user-domain", "depth": 1},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["projection"], {"root": "user-domain", "depth": 1})
        self.assertEqual(
            {node["id"] for node in payload["nodes"]},
            {"user-domain", "user-endpoint", "user-service", "user-response-schema"},
        )

    def test_rejects_an_unknown_root(self) -> None:
        response = self.client.get(
            "/api/graph",
            params={"root": "missing-domain", "depth": 1},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("does not exist", response.json()["detail"])

    def test_rejects_an_unsupported_depth(self) -> None:
        response = self.client.get("/api/graph", params={"depth": 3})

        self.assertEqual(response.status_code, 422)

    def test_reports_a_missing_canonical_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path(directory)))
            response = client.get("/api/graph")

        self.assertEqual(response.status_code, 404)
        self.assertIn("does not exist", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
