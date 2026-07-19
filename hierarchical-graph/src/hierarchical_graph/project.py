from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from .model import GraphError


def descendant_ids(
    nodes_by_id: dict[str, dict[str, Any]], root: str | None
) -> set[str]:
    if root is None:
        return set(nodes_by_id)
    children: dict[str, list[str]] = defaultdict(list)
    for node_id, node in nodes_by_id.items():
        parent = node.get("parent_id")
        if isinstance(parent, str):
            children[parent].append(node_id)
    result: set[str] = set()
    pending = [root]
    while pending:
        node_id = pending.pop()
        if node_id in result:
            continue
        result.add(node_id)
        pending.extend(children.get(node_id, []))
    return result


def build_projection(
    graph: dict[str, Any], root: str | None, depth: int
) -> dict[str, Any]:
    nodes = graph["nodes"]
    edges = graph["edges"]
    nodes_by_id = {node["id"]: node for node in nodes}
    if root is not None and root not in nodes_by_id:
        raise GraphError(f"root node '{root}' does not exist")
    universe = descendant_ids(nodes_by_id, root)

    visible: set[str] = set()
    if root is None:
        seeds = [node_id for node_id, node in nodes_by_id.items() if node["parent_id"] is None]
    else:
        seeds = [root]
    pending = [(node_id, 0) for node_id in seeds]
    while pending:
        node_id, node_depth = pending.pop(0)
        if node_id in visible or node_id not in universe or node_depth > depth:
            continue
        visible.add(node_id)
        if node_depth < depth:
            pending.extend(
                (child_id, node_depth + 1)
                for child_id, node in nodes_by_id.items()
                if node.get("parent_id") == node_id
            )

    def visible_ancestor(node_id: str) -> str | None:
        if node_id not in universe:
            return None
        current: str | None = node_id
        while current is not None:
            if current in visible:
                return current
            parent = nodes_by_id[current].get("parent_id")
            current = parent if isinstance(parent, str) else None
        return None

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        source = visible_ancestor(edge["source"])
        target = visible_ancestor(edge["target"])
        if source is None or target is None or source == target:
            continue
        grouped[(source, target, edge["type"])].append(edge)

    projected_edges: list[dict[str, Any]] = []
    for (source, target, edge_type), original_edges in sorted(grouped.items()):
        unchanged = (
            len(original_edges) == 1
            and original_edges[0]["source"] == source
            and original_edges[0]["target"] == target
        )
        evidence: list[dict[str, Any]] = []
        seen_evidence: set[str] = set()
        for edge in original_edges:
            for item in edge["evidence"]:
                key = json.dumps(item, sort_keys=True)
                if key not in seen_evidence:
                    seen_evidence.add(key)
                    evidence.append(item)
        projected_edges.append(
            {
                "id": (
                    original_edges[0]["id"]
                    if unchanged
                    else f"projected-{source}-{edge_type.replace('_', '-')}-{target}"
                ),
                "source": source,
                "target": target,
                "type": edge_type,
                "label": (
                    original_edges[0]["label"]
                    if len(original_edges) == 1
                    else f"{len(original_edges)} {edge_type.replace('_', ' ')} relationships"
                ),
                "evidence": evidence,
                "aggregated_edge_ids": sorted(edge["id"] for edge in original_edges),
            }
        )

    return {
        "schema_version": graph["schema_version"],
        "metadata": graph["metadata"],
        "projection": {"root": root, "depth": depth},
        "nodes": [node for node in nodes if node["id"] in visible],
        "edges": projected_edges,
    }

