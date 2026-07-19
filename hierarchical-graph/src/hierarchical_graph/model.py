from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = "1.0"
GRAPH_RELATIVE_PATH = Path(".graph") / "graph.json"
IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
NODE_TYPES = {
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
}
EDGE_TYPES = {
    "calls",
    "depends_on",
    "reads",
    "writes",
    "publishes",
    "subscribes",
    "serves",
    "uses",
    "configures",
}
OWNERSHIP_TYPES = {"primary", "shared"}
TOP_LEVEL_KEYS = {"schema_version", "metadata", "nodes", "edges"}
METADATA_KEYS = {"repo_name", "repo_root", "languages", "frameworks", "source_roots"}
NODE_KEYS = {"id", "parent_id", "label", "type", "description", "scope"}
SCOPE_KEYS = {"artifacts"}
ARTIFACT_KEYS = {"path", "symbols", "ownership"}
EDGE_KEYS = {"id", "source", "target", "type", "label", "evidence"}
EVIDENCE_KEYS = {"path", "symbols"}


class GraphError(Exception):
    """A user-facing graph operation error."""


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))

