from __future__ import annotations

from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .model import (
    ARTIFACT_KEYS,
    EDGE_KEYS,
    EDGE_TYPES,
    EVIDENCE_KEYS,
    IDENTIFIER_RE,
    METADATA_KEYS,
    NODE_KEYS,
    NODE_TYPES,
    OWNERSHIP_TYPES,
    SCHEMA_VERSION,
    SCOPE_KEYS,
    TOP_LEVEL_KEYS,
    GraphError,
    unique,
)


def exact_keys(
    value: dict[str, Any], expected: set[str], context: str, errors: list[str]
) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing:
        errors.append(f"{context}: missing keys: {', '.join(missing)}")
    if extra:
        errors.append(f"{context}: unsupported keys: {', '.join(extra)}")


def nonempty_string(value: Any, context: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{context}: must be a non-empty string")


def identifier(value: Any, context: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        errors.append(f"{context}: must be a semantic kebab-case identifier")


def string_set(
    value: Any, context: str, errors: list[str], require_nonempty: bool = False
) -> None:
    if not isinstance(value, list):
        errors.append(f"{context}: must be an array")
        return
    if require_nonempty and not value:
        errors.append(f"{context}: must contain at least one item")
    for index, item in enumerate(value):
        nonempty_string(item, f"{context}[{index}]", errors)
    hashable_items = [item for item in value if isinstance(item, str)]
    if len(hashable_items) != len(set(hashable_items)):
        errors.append(f"{context}: must not contain duplicates")


def validate_relative_path(
    value: Any,
    context: str,
    repo: Path,
    errors: list[str],
    *,
    concrete_file: bool = False,
) -> None:
    nonempty_string(value, context, errors)
    if not isinstance(value, str) or not value:
        return
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(f"{context}: must be a repository-relative path without '..'")
        return
    resolved = repo.joinpath(*candidate.parts)
    if not resolved.exists():
        errors.append(f"{context}: path does not exist: {value}")
    elif concrete_file and not resolved.is_file():
        errors.append(f"{context}: evidence must reference a concrete file: {value}")


def validate_metadata(value: Any, repo: Path, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("metadata: must be an object")
        return
    exact_keys(value, METADATA_KEYS, "metadata", errors)
    nonempty_string(value.get("repo_name"), "metadata.repo_name", errors)
    if value.get("repo_root") != ".":
        errors.append("metadata.repo_root: must equal '.'")
    string_set(value.get("languages"), "metadata.languages", errors)
    string_set(value.get("frameworks"), "metadata.frameworks", errors)
    string_set(value.get("source_roots"), "metadata.source_roots", errors)
    source_roots = value.get("source_roots")
    if isinstance(source_roots, list):
        for index, source_root in enumerate(source_roots):
            validate_relative_path(
                source_root, f"metadata.source_roots[{index}]", repo, errors
            )


def validate_artifact(
    value: Any, context: str, repo: Path, errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{context}: must be an object")
        return
    exact_keys(value, ARTIFACT_KEYS, context, errors)
    validate_relative_path(value.get("path"), f"{context}.path", repo, errors)
    string_set(value.get("symbols"), f"{context}.symbols", errors)
    if value.get("ownership") not in OWNERSHIP_TYPES:
        errors.append(
            f"{context}.ownership: must be one of {', '.join(sorted(OWNERSHIP_TYPES))}"
        )


def validate_node(value: Any, index: int, repo: Path, errors: list[str]) -> None:
    context = f"nodes[{index}]"
    if not isinstance(value, dict):
        errors.append(f"{context}: must be an object")
        return
    exact_keys(value, NODE_KEYS, context, errors)
    identifier(value.get("id"), f"{context}.id", errors)
    parent_id = value.get("parent_id")
    if parent_id is not None:
        identifier(parent_id, f"{context}.parent_id", errors)
    nonempty_string(value.get("label"), f"{context}.label", errors)
    if value.get("type") not in NODE_TYPES:
        errors.append(f"{context}.type: must be one of {', '.join(sorted(NODE_TYPES))}")
    nonempty_string(value.get("description"), f"{context}.description", errors)
    scope = value.get("scope")
    if not isinstance(scope, dict):
        errors.append(f"{context}.scope: must be an object")
        return
    exact_keys(scope, SCOPE_KEYS, f"{context}.scope", errors)
    artifacts = scope.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append(f"{context}.scope.artifacts: must be an array")
        return
    for artifact_index, artifact in enumerate(artifacts):
        validate_artifact(
            artifact, f"{context}.scope.artifacts[{artifact_index}]", repo, errors
        )


def validate_evidence(
    value: Any, context: str, repo: Path, errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{context}: must be an object")
        return
    exact_keys(value, EVIDENCE_KEYS, context, errors)
    validate_relative_path(
        value.get("path"), f"{context}.path", repo, errors, concrete_file=True
    )
    string_set(value.get("symbols"), f"{context}.symbols", errors, require_nonempty=True)


def validate_edge(value: Any, index: int, repo: Path, errors: list[str]) -> None:
    context = f"edges[{index}]"
    if not isinstance(value, dict):
        errors.append(f"{context}: must be an object")
        return
    exact_keys(value, EDGE_KEYS, context, errors)
    identifier(value.get("id"), f"{context}.id", errors)
    identifier(value.get("source"), f"{context}.source", errors)
    identifier(value.get("target"), f"{context}.target", errors)
    if value.get("type") not in EDGE_TYPES:
        errors.append(f"{context}.type: must be one of {', '.join(sorted(EDGE_TYPES))}")
    nonempty_string(value.get("label"), f"{context}.label", errors)
    evidence = value.get("evidence")
    if not isinstance(evidence, list):
        errors.append(f"{context}.evidence: must be an array")
        return
    if not evidence:
        errors.append(f"{context}.evidence: must contain at least one item")
    for evidence_index, item in enumerate(evidence):
        validate_evidence(item, f"{context}.evidence[{evidence_index}]", repo, errors)


def validate_graph(graph: dict[str, Any], repo: Path) -> list[str]:
    errors: list[str] = []
    exact_keys(graph, TOP_LEVEL_KEYS, "graph", errors)
    if graph.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: must equal '{SCHEMA_VERSION}'")
    validate_metadata(graph.get("metadata"), repo, errors)

    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        errors.append("nodes: must be an array")
        nodes = []
    if not nodes:
        errors.append("nodes: must contain at least one node")
    for index, node in enumerate(nodes):
        validate_node(node, index, repo, errors)

    edges = graph.get("edges")
    if not isinstance(edges, list):
        errors.append("edges: must be an array")
        edges = []
    for index, edge in enumerate(edges):
        validate_edge(edge, index, repo, errors)

    typed_nodes = [node for node in nodes if isinstance(node, dict)]
    typed_edges = [edge for edge in edges if isinstance(edge, dict)]
    node_ids = [node.get("id") for node in typed_nodes if isinstance(node.get("id"), str)]
    edge_ids = [edge.get("id") for edge in typed_edges if isinstance(edge.get("id"), str)]
    duplicate_nodes = sorted({item for item in node_ids if node_ids.count(item) > 1})
    duplicate_edges = sorted({item for item in edge_ids if edge_ids.count(item) > 1})
    if duplicate_nodes:
        errors.append(f"nodes: duplicate IDs: {', '.join(duplicate_nodes)}")
    if duplicate_edges:
        errors.append(f"edges: duplicate IDs: {', '.join(duplicate_edges)}")

    nodes_by_id = {
        node["id"]: node
        for node in typed_nodes
        if isinstance(node.get("id"), str) and node_ids.count(node["id"]) == 1
    }
    children_by_parent: dict[str | None, list[str]] = defaultdict(list)
    for node_id, node in nodes_by_id.items():
        parent_id = node.get("parent_id")
        if parent_id == node_id:
            errors.append(f"node '{node_id}': cannot parent itself")
        elif parent_id is not None and parent_id not in nodes_by_id:
            errors.append(f"node '{node_id}': parent '{parent_id}' does not exist")
        children_by_parent[parent_id].append(node_id)

    for parent_id, child_ids in children_by_parent.items():
        if len(child_ids) > 15:
            parent_label = parent_id if parent_id is not None else "<root>"
            errors.append(
                f"parent '{parent_label}': has {len(child_ids)} direct children; maximum is 15"
            )

    for start_id in nodes_by_id:
        visited: set[str] = set()
        current: str | None = start_id
        while current is not None and current in nodes_by_id:
            if current in visited:
                errors.append(f"hierarchy: containment cycle involving '{current}'")
                break
            visited.add(current)
            parent = nodes_by_id[current].get("parent_id")
            current = parent if isinstance(parent, str) else None

    for node_id, node in nodes_by_id.items():
        is_leaf = not children_by_parent.get(node_id)
        if is_leaf and node.get("type") != "external":
            artifacts = node.get("scope", {}).get("artifacts", [])
            concrete = False
            if isinstance(artifacts, list):
                for artifact in artifacts:
                    if not isinstance(artifact, dict):
                        continue
                    path_value = artifact.get("path")
                    if isinstance(path_value, str) and path_value:
                        candidate = PurePosixPath(path_value)
                        if not candidate.is_absolute() and ".." not in candidate.parts:
                            concrete = repo.joinpath(*candidate.parts).is_file()
                    if concrete:
                        break
            if not concrete:
                errors.append(
                    f"node '{node_id}': non-external leaf must reference a concrete file"
                )

    for edge in typed_edges:
        edge_id = edge.get("id", "<invalid>")
        source = edge.get("source")
        target = edge.get("target")
        if isinstance(source, str) and source not in nodes_by_id:
            errors.append(f"edge '{edge_id}': source '{source}' does not exist")
        if isinstance(target, str) and target not in nodes_by_id:
            errors.append(f"edge '{edge_id}': target '{target}' does not exist")

    return unique(errors)


def raise_for_errors(errors: list[str], prefix: str) -> None:
    if errors:
        details = "\n".join(f"  - {error}" for error in errors)
        raise GraphError(f"{prefix}:\n{details}")

