"""Load graph artifacts and validate their references against a repository."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from .models import GraphArtifact


class GraphServiceError(Exception):
    """Base class for graph loading failures."""


class GraphNotFoundError(GraphServiceError):
    """Raised when the configured repository has no graph artifact."""


class GraphUnreadableError(GraphServiceError):
    """Raised when graph.json exists but cannot be read from disk."""


class InvalidGraphError(GraphServiceError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def format_validation_errors(error: ValidationError) -> list[str]:
    """Flatten Pydantic's structured errors into API-friendly messages."""
    messages: list[str] = []
    for item in error.errors(include_url=False):
        location = ".".join(str(part) for part in item["loc"])
        prefix = f"{location}: " if location else ""
        messages.append(f"{prefix}{item['msg']}")
    return messages


def resolve_reference(
    repository_path: Path,
    value: str,
    context: str,
    errors: list[str],
    *,
    require_file: bool = False,
) -> Path | None:
    """
    Validate one graph path using this process:

    1. Require a repository-relative POSIX path without ``..`` traversal
    2. Resolve the path and confirm it remains inside the repository
    3. Confirm the path exists and, when requested, is a concrete file
    4. Append contextual failures to ``errors`` and return the resolved path
    """
    candidate = PurePosixPath(value)
    # Graph paths are portable POSIX paths and may never escape the repo root.
    if "\\" in value or candidate.is_absolute() or ".." in candidate.parts:
        errors.append(
            f"{context}: must be a repository-relative POSIX path without '..'"
        )
        return None

    resolved = repository_path.joinpath(*candidate.parts).resolve()
    try:
        resolved.relative_to(repository_path)
    except ValueError:
        errors.append(f"{context}: resolves outside the configured repository")
        return None

    if not resolved.exists():
        errors.append(f"{context}: path does not exist: {value}")
    elif require_file and not resolved.is_file():
        errors.append(f"{context}: must reference a concrete file: {value}")
    return resolved


def validate_repository_references(
    graph: GraphArtifact,
    repository_path: Path,
) -> list[str]:
    """
    Validate graph references against the configured repository's filesystem.
    
    Process flow:
     1. Validate every metadata source root
     2. Index child nodes to distinguish containers from leaf nodes
     3. Validate node artifacts and require files for non-external leaves
     4. Validate every edge evidence path as a concrete file
     5. Return all discovered errors with duplicates removed
    """
    errors: list[str] = []
    children_by_parent: dict[str | None, list[str]] = defaultdict(list)
    for index, source_root in enumerate(graph.metadata.source_roots):
        resolve_reference(
            repository_path,
            source_root,
            f"metadata.source_roots[{index}]",
            errors,
        )

    for node in graph.nodes:
        children_by_parent[node.parent_id].append(node.id)

    for node_index, node in enumerate(graph.nodes):
        concrete_artifact_found = False
        for artifact_index, artifact in enumerate(node.scope.artifacts):
            resolved = resolve_reference(
                repository_path,
                artifact.path,
                f"nodes[{node_index}].scope.artifacts[{artifact_index}].path",
                errors,
            )
            concrete_artifact_found = concrete_artifact_found or bool(
                resolved and resolved.is_file()
            )

        # Container nodes may own only children; executable leaf nodes need a file.
        is_leaf = not children_by_parent.get(node.id)
        if is_leaf and node.type != "external" and not concrete_artifact_found:
            errors.append(
                f"node '{node.id}': non-external leaf must reference a concrete file"
            )

    for edge_index, edge in enumerate(graph.edges):
        for evidence_index, evidence in enumerate(edge.evidence):
            resolve_reference(
                repository_path,
                evidence.path,
                f"edges[{edge_index}].evidence[{evidence_index}].path",
                errors,
                require_file=True,
            )

    return list(dict.fromkeys(errors))


class GraphService:
    """Read and validate the canonical graph for one configured repository."""

    def __init__(self, repository_path: Path) -> None:
        self.repository_path = repository_path.resolve()
        self.graph_path = self.repository_path / ".graph" / "graph.json"

    def load_graph(self) -> GraphArtifact:
        """Load graph.json and enforce schema, relationships, and file evidence."""
        if not self.graph_path.is_file():
            raise GraphNotFoundError(
                f"No graph artifact found at {self.graph_path}"
            )

        try:
            raw_text = self.graph_path.read_text(encoding="utf-8")
        except OSError as error:
            raise GraphUnreadableError(
                f"Unable to read graph artifact at {self.graph_path}: {error}"
            ) from error

        # Parsing and model validation stay separate so clients receive precise errors.
        # Parsing
        try:
            raw_graph: Any = json.loads(raw_text)
        except json.JSONDecodeError as error:
            raise InvalidGraphError(
                [
                    "graph.json contains invalid JSON "
                    f"at line {error.lineno}, column {error.colno}"
                ]
            ) from error

        # Model Validation
        try:
            graph = GraphArtifact.model_validate(raw_graph)
        except ValidationError as error:
            raise InvalidGraphError(format_validation_errors(error)) from error

        reference_errors = validate_repository_references(
            graph,
            self.repository_path,
        )
        if reference_errors:
            raise InvalidGraphError(reference_errors)
        return graph
