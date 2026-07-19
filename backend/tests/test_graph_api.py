from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import create_app
from merge_marshal_api.settings import BACKEND_PATH, DEFAULT_REPOSITORY_PATH, Settings


def graph_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "metadata": {
            "repo_name": "sample-repo",
            "repo_root": ".",
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "source_roots": ["src"],
        },
        "nodes": [
            {
                "id": "api",
                "parent_id": None,
                "label": "API",
                "type": "entrypoint",
                "description": "HTTP entrypoint",
                "scope": {
                    "artifacts": [
                        {
                            "path": "src/api.py",
                            "symbols": ["app"],
                            "ownership": "primary",
                        }
                    ]
                },
            },
            {
                "id": "database",
                "parent_id": None,
                "label": "Database",
                "type": "store",
                "description": "Persistence adapter",
                "scope": {
                    "artifacts": [
                        {
                            "path": "src/db.py",
                            "symbols": ["Database"],
                            "ownership": "primary",
                        }
                    ]
                },
            },
        ],
        "edges": [
            {
                "id": "api-reads-database",
                "source": "api",
                "target": "database",
                "type": "reads",
                "label": "Loads records",
                "evidence": [
                    {
                        "path": "src/api.py",
                        "symbols": ["list_records"],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "api.py").write_text("app = object()\n", encoding="utf-8")
    (source_root / "db.py").write_text("class Database: pass\n", encoding="utf-8")
    return tmp_path


def write_graph(repository: Path, payload: object) -> None:
    graph_directory = repository / ".graph"
    graph_directory.mkdir(exist_ok=True)
    (graph_directory / "graph.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def client_for(repository: Path) -> TestClient:
    app = create_app(Settings(repository_path=repository))
    return TestClient(app)


def test_relative_repository_setting_resolves_from_backend() -> None:
    settings = Settings(
        repository_path=Path("../example-repository"),
        _env_file=None,
    )

    assert settings.repository_path == (BACKEND_PATH / "../example-repository").resolve()


def test_settings_load_repository_from_dotenv(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "MERGE_MARSHAL_REPO_PATH=../dotenv-repository\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=dotenv_path)

    assert settings.repository_path == (BACKEND_PATH / "../dotenv-repository").resolve()


def test_settings_ignore_operating_system_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MERGE_MARSHAL_REPO_PATH", "../environment-repository")

    settings = Settings(_env_file=None)

    assert settings.repository_path == DEFAULT_REPOSITORY_PATH.resolve()


def test_health_endpoint_does_not_require_a_graph(repository: Path) -> None:
    response = client_for(repository).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_returns_valid_graph_without_caching(repository: Path) -> None:
    payload = graph_payload()
    write_graph(repository, payload)
    client = client_for(repository)

    response = client.get("/api/graph")

    assert response.status_code == 200
    assert response.json() == payload
    assert response.headers["cache-control"] == "no-store"

    payload["metadata"]["repo_name"] = "updated-repo"  # type: ignore[index]
    write_graph(repository, payload)
    updated_response = client.get("/api/graph")

    assert updated_response.status_code == 200
    assert updated_response.json()["metadata"]["repo_name"] == "updated-repo"


def test_reports_missing_graph(repository: Path) -> None:
    response = client_for(repository).get("/api/graph")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "graph_not_found"


def test_reports_malformed_json(repository: Path) -> None:
    graph_directory = repository / ".graph"
    graph_directory.mkdir()
    (graph_directory / "graph.json").write_text("{not-json", encoding="utf-8")

    response = client_for(repository).get("/api/graph")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "graph_invalid"
    assert "invalid JSON" in response.json()["detail"]["errors"][0]


def test_reports_contract_and_relationship_errors(repository: Path) -> None:
    payload = graph_payload()
    payload["nodes"][0]["unsupported"] = True  # type: ignore[index]
    write_graph(repository, payload)

    response = client_for(repository).get("/api/graph")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "graph_invalid"
    assert any("unsupported" in error for error in detail["errors"])


def test_reports_missing_edge_endpoints(repository: Path) -> None:
    payload = graph_payload()
    payload["edges"][0]["target"] = "missing-node"  # type: ignore[index]
    write_graph(repository, payload)

    response = client_for(repository).get("/api/graph")

    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert any("missing target 'missing-node'" in error for error in errors)


def test_reports_missing_repository_artifacts(repository: Path) -> None:
    payload = graph_payload()
    payload["nodes"][1]["scope"]["artifacts"][0]["path"] = "src/missing.py"  # type: ignore[index]
    write_graph(repository, payload)

    response = client_for(repository).get("/api/graph")

    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert any("src/missing.py" in error for error in errors)
