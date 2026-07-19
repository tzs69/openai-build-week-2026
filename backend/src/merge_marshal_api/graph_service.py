from __future__ import annotations

from pathlib import Path
from typing import Any

from hierarchical_graph.model import GraphError
from hierarchical_graph.project import build_projection
from hierarchical_graph.store import graph_path, load_graph
from hierarchical_graph.validate import validate_graph


class GraphNotFoundError(Exception):
    """The configured repository has no canonical graph."""


class InvalidGraphError(Exception):
    """The configured canonical graph failed validation."""


class UnknownGraphRootError(Exception):
    """A projection root does not exist in the canonical graph."""


class GraphService:
    def __init__(self, repository: Path) -> None:
        self.repository = repository.resolve()

    def load(self) -> dict[str, Any]:
        try:
            graph = load_graph(self.repository)
        except GraphError as exc:
            raise GraphNotFoundError(str(exc)) from exc

        errors = validate_graph(graph, self.repository)
        if errors:
            details = "; ".join(errors)
            raise InvalidGraphError(
                f"{graph_path(self.repository)} is invalid: {details}"
            )

        return graph

    def project(self, root: str | None, depth: int) -> dict[str, Any]:
        graph = self.load()

        try:
            return build_projection(graph, root=root, depth=depth)
        except GraphError as exc:
            raise UnknownGraphRootError(str(exc)) from exc
