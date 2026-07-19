from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .model import IDENTIFIER_RE, SCHEMA_VERSION, GraphError, unique
from .project import build_projection, descendant_ids
from .store import atomic_write, graph_path, load_graph, repo_path
from .validate import (
    raise_for_errors,
    validate_edge,
    validate_graph,
    validate_metadata,
    validate_node,
)


def read_payload(input_value: str) -> dict[str, Any]:
    if input_value == "-":
        raw = sys.stdin.read()
        source = "stdin"
    else:
        source_path = Path(input_value)
        source = str(source_path)
        try:
            raw = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise GraphError(f"cannot read {source}: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GraphError(f"invalid JSON from {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise GraphError(f"payload from {source} must be a JSON object")
    return value


def parse_parent(value: str) -> str | None:
    if value.lower() in {"null", "none"}:
        return None
    if not IDENTIFIER_RE.fullmatch(value):
        raise GraphError("--parent must be 'null' or a semantic kebab-case node ID")
    return value


def command_init(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    if not repo.is_dir():
        raise GraphError(f"repository does not exist or is not a directory: {repo}")
    destination = graph_path(repo)
    if destination.exists() and not args.force:
        raise GraphError(f"{destination} already exists; update it or pass --force")
    graph = {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "repo_name": args.repo_name or repo.name,
            "repo_root": ".",
            "languages": unique(args.language),
            "frameworks": unique(args.framework),
            "source_roots": unique(args.source_root),
        },
        "nodes": [],
        "edges": [],
    }
    metadata_errors: list[str] = []
    validate_metadata(graph["metadata"], repo, metadata_errors)
    raise_for_errors(metadata_errors, "invalid metadata")
    atomic_write(repo, graph)
    print(f"initialized {destination}")


def command_put_node(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    payload = read_payload(args.input)
    parent_id = parse_parent(args.parent)
    if "parent_id" in payload and payload["parent_id"] != parent_id:
        raise GraphError("payload parent_id must match --parent")
    node = dict(payload)
    node["parent_id"] = parent_id
    node_errors: list[str] = []
    validate_node(node, 0, repo, node_errors)
    raise_for_errors(node_errors, "invalid node")

    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise GraphError("graph nodes collection is invalid; run validate")
    nodes_by_id = {
        item.get("id"): item for item in nodes if isinstance(item, dict)
    }
    if parent_id is not None and parent_id not in nodes_by_id:
        raise GraphError(f"parent node '{parent_id}' does not exist")
    node_id = node["id"]
    candidate_nodes = [
        item
        for item in nodes
        if not (isinstance(item, dict) and item.get("id") == node_id)
    ]
    candidate_nodes.append(node)
    graph["nodes"] = candidate_nodes

    candidate_by_id = {
        item["id"]: item
        for item in candidate_nodes
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    visited: set[str] = set()
    current: str | None = node_id
    while current is not None and current in candidate_by_id:
        if current in visited:
            raise GraphError(f"upsert would create a containment cycle involving '{current}'")
        visited.add(current)
        next_parent = candidate_by_id[current].get("parent_id")
        current = next_parent if isinstance(next_parent, str) else None

    atomic_write(repo, graph)
    print(f"wrote node {node_id}")


def command_put_edge(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    edge = read_payload(args.input)
    edge_errors: list[str] = []
    validate_edge(edge, 0, repo, edge_errors)
    raise_for_errors(edge_errors, "invalid edge")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise GraphError("graph collections are invalid; run validate")
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    if edge["source"] not in node_ids:
        raise GraphError(f"source node '{edge['source']}' does not exist")
    if edge["target"] not in node_ids:
        raise GraphError(f"target node '{edge['target']}' does not exist")
    graph["edges"] = [
        item
        for item in edges
        if not (isinstance(item, dict) and item.get("id") == edge["id"])
    ] + [edge]
    atomic_write(repo, graph)
    print(f"wrote edge {edge['id']}")


def command_show(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node = next(
        (
            item
            for item in nodes
            if isinstance(item, dict) and item.get("id") == args.node_id
        ),
        None,
    )
    if node is None:
        raise GraphError(f"node '{args.node_id}' does not exist")
    result = {
        "node": node,
        "children": sorted(
            item["id"]
            for item in nodes
            if isinstance(item, dict) and item.get("parent_id") == args.node_id
        ),
        "incoming_edges": sorted(
            item["id"]
            for item in edges
            if isinstance(item, dict) and item.get("target") == args.node_id
        ),
        "outgoing_edges": sorted(
            item["id"]
            for item in edges
            if isinstance(item, dict) and item.get("source") == args.node_id
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


def command_tree(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise GraphError("graph nodes collection is invalid; run validate")
    nodes_by_id = {
        node["id"]: node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    children: dict[str | None, list[str]] = defaultdict(list)
    for node_id, node in nodes_by_id.items():
        parent = node.get("parent_id")
        children[parent if isinstance(parent, str) else None].append(node_id)
    for child_ids in children.values():
        child_ids.sort()

    lines: list[str] = []

    def walk(node_id: str, prefix: str, last: bool, active: set[str]) -> None:
        node = nodes_by_id[node_id]
        branch = "└── " if last else "├── "
        lines.append(
            f"{prefix}{branch}{node_id} [{node.get('type', '?')}] {node.get('label', '')}"
        )
        if node_id in active:
            lines.append(f"{prefix}    <cycle>")
            return
        next_active = active | {node_id}
        child_ids = children.get(node_id, [])
        child_prefix = prefix + ("    " if last else "│   ")
        for index, child_id in enumerate(child_ids):
            walk(child_id, child_prefix, index == len(child_ids) - 1, next_active)

    roots = children.get(None, [])
    for index, root_id in enumerate(roots):
        walk(root_id, "", index == len(roots) - 1, set())
    print("\n".join(lines) if lines else "(empty graph)")


def command_validate(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    errors = validate_graph(graph, repo)
    if errors:
        for error in errors:
            print(f"error: {error}")
        raise GraphError(f"validation failed with {len(errors)} error(s)")
    print(
        f"valid: {graph_path(repo)} ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)"
    )


def command_project(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    raise_for_errors(validate_graph(graph, repo), "graph is invalid")
    result = build_projection(graph, args.root, args.depth)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def command_delete_node(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise GraphError("graph collections are invalid; run validate")
    nodes_by_id = {
        node["id"]: node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    if args.node_id not in nodes_by_id:
        raise GraphError(f"node '{args.node_id}' does not exist")
    children = [
        node["id"]
        for node in nodes_by_id.values()
        if node.get("parent_id") == args.node_id
    ]
    incident = [
        edge.get("id")
        for edge in edges
        if isinstance(edge, dict)
        and (edge.get("source") == args.node_id or edge.get("target") == args.node_id)
    ]
    if (children or incident) and not args.cascade:
        details = []
        if children:
            details.append(f"children: {', '.join(sorted(children))}")
        if incident:
            details.append(
                f"edges: {', '.join(sorted(str(item) for item in incident))}"
            )
        raise GraphError(
            f"node '{args.node_id}' is still referenced ({'; '.join(details)}); "
            "pass --cascade explicitly"
        )
    removed = (
        descendant_ids(nodes_by_id, args.node_id) if args.cascade else {args.node_id}
    )
    graph["nodes"] = [
        node
        for node in nodes
        if not (isinstance(node, dict) and node.get("id") in removed)
    ]
    graph["edges"] = [
        edge
        for edge in edges
        if not (
            isinstance(edge, dict)
            and (edge.get("source") in removed or edge.get("target") in removed)
        )
    ]
    atomic_write(repo, graph)
    print(f"deleted {len(removed)} node(s)")


def command_delete_edge(args: argparse.Namespace) -> None:
    repo = repo_path(args.repo)
    graph = load_graph(repo)
    edges = graph.get("edges")
    if not isinstance(edges, list):
        raise GraphError("graph edges collection is invalid; run validate")
    retained = [
        edge
        for edge in edges
        if not (isinstance(edge, dict) and edge.get("id") == args.edge_id)
    ]
    if len(retained) == len(edges):
        raise GraphError(f"edge '{args.edge_id}' does not exist")
    graph["edges"] = retained
    atomic_write(repo, graph)
    print(f"deleted edge {args.edge_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hgraph",
        description="Build and validate .graph/graph.json for a repository",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize graph.json")
    init_parser.add_argument("--repo", default=".")
    init_parser.add_argument("--repo-name")
    init_parser.add_argument("--language", action="append", default=[])
    init_parser.add_argument("--framework", action="append", default=[])
    init_parser.add_argument("--source-root", action="append", default=[])
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(handler=command_init)

    node_parser = subparsers.add_parser("put-node", help="insert or update a node")
    node_parser.add_argument("--repo", default=".")
    node_parser.add_argument("--parent", required=True)
    node_parser.add_argument("--input", required=True)
    node_parser.set_defaults(handler=command_put_node)

    edge_parser = subparsers.add_parser("put-edge", help="insert or update an edge")
    edge_parser.add_argument("--repo", default=".")
    edge_parser.add_argument("--input", required=True)
    edge_parser.set_defaults(handler=command_put_edge)

    show_parser = subparsers.add_parser("show", help="show a node and its relationships")
    show_parser.add_argument("--repo", default=".")
    show_parser.add_argument("node_id")
    show_parser.set_defaults(handler=command_show)

    tree_parser = subparsers.add_parser("tree", help="print the node hierarchy")
    tree_parser.add_argument("--repo", default=".")
    tree_parser.set_defaults(handler=command_tree)

    validate_parser = subparsers.add_parser("validate", help="validate the canonical graph")
    validate_parser.add_argument("--repo", default=".")
    validate_parser.set_defaults(handler=command_validate)

    project_parser = subparsers.add_parser("project", help="emit a depth-limited projection")
    project_parser.add_argument("--repo", default=".")
    project_parser.add_argument("--root")
    project_parser.add_argument("--depth", type=int, default=2)
    project_parser.set_defaults(handler=command_project)

    delete_node_parser = subparsers.add_parser("delete-node", help="delete a node")
    delete_node_parser.add_argument("--repo", default=".")
    delete_node_parser.add_argument("node_id")
    delete_node_parser.add_argument("--cascade", action="store_true")
    delete_node_parser.set_defaults(handler=command_delete_node)

    delete_edge_parser = subparsers.add_parser("delete-edge", help="delete an edge")
    delete_edge_parser.add_argument("--repo", default=".")
    delete_edge_parser.add_argument("edge_id")
    delete_edge_parser.set_defaults(handler=command_delete_edge)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "depth", 0) < 0:
        parser.error("--depth must be zero or greater")
    try:
        args.handler(args)
    except GraphError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def entrypoint() -> None:
    raise SystemExit(main())

