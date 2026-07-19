---
name: generate-hierarchical-graph
description: Generate and maintain a hierarchical, evidence-backed `.graph/graph.json` for codebase visualization and task-executor scoping. Use when asked to map repository architecture, create a nested component graph, refresh graph.json, or prepare architecture context for planning and execution agents.
---

# Generate Hierarchical Graph

## Purpose

Create one canonical `.graph/graph.json`. Nodes and edges describe the visual architecture; node scope and edge evidence connect that architecture to exact code for later task executors.

The `hgraph` CLI owns storage, schema validation, and projection. This skill owns only the LLM's analysis workflow. Do not generate `graph_reverse.json`, Mermaid, warnings, or speculative relationships.

## Prerequisite

```bash
command -v hgraph
```

If unavailable and the repository contains `hierarchical-graph/`, install it:

```bash
python3 -m pip install -e ./hierarchical-graph
```

If an older offline pip cannot provision its build environment, retry with:

```bash
python3 -m pip install --no-use-pep517 -e ./hierarchical-graph
```

If neither is available, stop and tell the user that `hgraph` must be installed. Read [REFERENCE.md](REFERENCE.md) before the first scan or when deciding node granularity.

## Workflow

1. Inspect manifests, source roots, entrypoints, runtime boundaries, and integrations.
2. Initialize once with detected repository metadata.
3. Create top-level runtime or deployable nodes.
4. Analyze every node recursively and add meaningful children parent-first.
5. Add evidence-backed architectural relationships.
6. Run `hgraph tree`, inspect the hierarchy, then run `hgraph validate`.
7. Run `hgraph project --depth 2` to preview a depth-limited consumer view.

```bash
hgraph init --repo . --language python --framework fastapi --source-root backend/
hgraph put-node --repo . --parent null --input -
hgraph put-edge --repo . --input -
hgraph show --repo . <node-id>
hgraph tree --repo .
hgraph validate --repo .
hgraph project --repo . --depth 2
```

For verified stale entries only:

```bash
hgraph delete-node --repo . <node-id>
hgraph delete-edge --repo . <edge-id>
```

## Granularity rules

- Recurse through repository → runtime/deployable → domain/feature → cohesive module.
- Stop at cohesive modules by default.
- Promote a class only when it owns lifecycle or state, exposes an architectural boundary, represents an integration, has distinct external relationships, or is independently useful for planning.
- Put ordinary classes, functions, DTOs, models, utilities, helpers, and UI elements in `scope.artifacts[].symbols`.
- Model responsibilities, not the raw directory tree or every import and call.
- Prefer 3–12 children per parent. Never exceed 15; introduce a real intermediate boundary or retain details as symbols.
- Use globally unique, stable, semantic kebab-case IDs. Reparent with `parent_id`; do not rename IDs because nesting changes.
- Omit uncertain nodes and edges. Every relationship needs file and symbol evidence.
- Use `primary` for artifacts owned by a node and `shared` where changing the artifact can affect multiple nodes.

## Completion criteria

- `.graph/graph.json` is the only persisted graph artifact.
- `hgraph validate` exits successfully.
- Every non-external leaf maps to at least one concrete file.
- The tree preserves meaningful containment and its depth-two projection is understandable.
- Update existing graphs with upserts and explicit verified deletions; do not force reinitialize them.
