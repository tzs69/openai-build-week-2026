"""Pydantic contracts and structural validation for graph API payloads."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Reusable scalar contracts keep identifier and string rules consistent throughout
# the graph instead of repeating Field constraints on every model.
Identifier = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"),
]
NonEmptyString = Annotated[str, Field(min_length=1)]
NodeType = Literal[
    "entrypoint",
    "component",
    "service",
    "store",
    "queue",
    "worker",
    "scheduler",
    "external",
    "shared",
    "config",
]
EdgeType = Literal[
    "calls",
    "depends_on",
    "reads",
    "writes",
    "publishes",
    "subscribes",
    "serves",
    "uses",
    "configures",
]


class StrictModel(BaseModel):
    """Base contract that rejects coercion and unknown schema fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


def require_unique(values: list[str], field_name: str) -> list[str]:
    """Reject repeated values in fields that behave as ordered sets."""
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


class GraphMetadata(StrictModel):
    repo_name: NonEmptyString
    repo_root: Literal["."]
    languages: list[NonEmptyString]
    frameworks: list[NonEmptyString]
    source_roots: list[NonEmptyString]

    @field_validator("languages", "frameworks", "source_roots")
    @classmethod
    def validate_string_sets(cls, values: list[str], info: object) -> list[str]:
        field_name = getattr(info, "field_name", "value")
        return require_unique(values, field_name)


class ArtifactReference(StrictModel):
    path: NonEmptyString
    symbols: list[NonEmptyString]
    ownership: Literal["primary", "shared"]

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, values: list[str]) -> list[str]:
        return require_unique(values, "symbols")


class EvidenceReference(StrictModel):
    path: NonEmptyString
    symbols: Annotated[list[NonEmptyString], Field(min_length=1)]

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, values: list[str]) -> list[str]:
        return require_unique(values, "symbols")


class NodeScope(StrictModel):
    artifacts: list[ArtifactReference]


class GraphNode(StrictModel):
    id: Identifier
    parent_id: Identifier | None
    label: NonEmptyString
    type: NodeType
    description: NonEmptyString
    scope: NodeScope


class GraphEdge(StrictModel):
    id: Identifier
    source: Identifier
    target: Identifier
    type: EdgeType
    label: NonEmptyString
    evidence: Annotated[list[EvidenceReference], Field(min_length=1)]


def _duplicate_id_errors(nodes: list[GraphNode], edges: list[GraphEdge]) -> list[str]:
    """Report duplicate IDs before relationships are resolved by ID."""
    errors: list[str] = []
    duplicate_nodes = sorted(
        node_id
        for node_id, count in Counter(node.id for node in nodes).items()
        if count > 1
    )
    duplicate_edges = sorted(
        edge_id
        for edge_id, count in Counter(edge.id for edge in edges).items()
        if count > 1
    )
    if duplicate_nodes:
        errors.append(f"duplicate node IDs: {', '.join(duplicate_nodes)}")
    if duplicate_edges:
        errors.append(f"duplicate edge IDs: {', '.join(duplicate_edges)}")
    return errors


def _index_unique_nodes(nodes: list[GraphNode]) -> dict[str, GraphNode]:
    """Build a safe relationship index, excluding ambiguous duplicate IDs."""
    node_counts = Counter(node.id for node in nodes)
    return {node.id: node for node in nodes if node_counts[node.id] == 1}


def _validate_containment(
    nodes: list[GraphNode],
    nodes_by_id: dict[str, GraphNode],
) -> list[str]:
    """Validate parent references, direct-child limits, and containment cycles."""
    errors: list[str] = []
    children_by_parent: dict[str | None, list[str]] = defaultdict(list)

    # Parent references must point to another unambiguous node in this graph.
    for node in nodes:
        if node.parent_id == node.id:
            errors.append(f"node '{node.id}' cannot parent itself")
        elif node.parent_id is not None and node.parent_id not in nodes_by_id:
            errors.append(
                f"node '{node.id}' references missing parent '{node.parent_id}'"
            )
        children_by_parent[node.parent_id].append(node.id)

    # Keep each visual grouping small enough for downstream graph renderers.
    for parent_id, children in children_by_parent.items():
        if len(children) > 15:
            label = parent_id if parent_id is not None else "<root>"
            errors.append(f"parent '{label}' has more than 15 direct children")

    # Walk each parent chain independently; revisiting a node proves a cycle.
    for start_id in nodes_by_id:
        visited: set[str] = set()
        current: str | None = start_id
        while current is not None and current in nodes_by_id:
            if current in visited:
                errors.append(f"containment cycle involving '{current}'")
                break
            visited.add(current)
            current = nodes_by_id[current].parent_id

    return errors


def _validate_edge_endpoints(
    edges: list[GraphEdge],
    nodes_by_id: dict[str, GraphNode],
) -> list[str]:
    """Ensure every edge resolves to concrete source and target nodes."""
    errors: list[str] = []
    for edge in edges:
        if edge.source not in nodes_by_id:
            errors.append(
                f"edge '{edge.id}' references missing source '{edge.source}'"
            )
        if edge.target not in nodes_by_id:
            errors.append(
                f"edge '{edge.id}' references missing target '{edge.target}'"
            )
    return errors


class GraphArtifact(StrictModel):
    """Canonical graph document returned by the API."""

    schema_version: Literal["1.0"]
    metadata: GraphMetadata
    nodes: Annotated[list[GraphNode], Field(min_length=1)]
    edges: list[GraphEdge]

    @model_validator(mode="after")
    def validate_graph_relationships(self) -> "GraphArtifact":
        nodes_by_id = _index_unique_nodes(self.nodes)
        errors = _duplicate_id_errors(self.nodes, self.edges)
        errors.extend(_validate_containment(self.nodes, nodes_by_id))
        errors.extend(_validate_edge_endpoints(self.edges, nodes_by_id))

        if errors:
            # Preserve discovery order while suppressing repeated cycle/reference errors.
            raise ValueError("; ".join(dict.fromkeys(errors)))
        return self


class ApiErrorDetail(StrictModel):
    """Stable machine-readable error body nested under FastAPI's `detail` key."""

    code: str
    message: str
    errors: list[str] = Field(default_factory=list)


class ApiErrorResponse(StrictModel):
    detail: ApiErrorDetail


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
