from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .model import GRAPH_RELATIVE_PATH, GraphError


def repo_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def graph_path(repo: Path) -> Path:
    return repo / GRAPH_RELATIVE_PATH


def load_graph(repo: Path) -> dict[str, Any]:
    path = graph_path(repo)
    if not path.is_file():
        raise GraphError(f"{path} does not exist; run init first")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GraphError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GraphError(f"{path} must contain a JSON object")
    return value


def atomic_write(repo: Path, graph: dict[str, Any]) -> None:
    destination = graph_path(repo)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".graph.json.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()

