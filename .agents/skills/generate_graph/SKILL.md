---
name: generate-graph
description: Generate a centralized architecture graph for a repository. Use when asked to inspect a codebase and produce a canonical graph.json source of truth, graph_reverse.json reverse mapping, or architecture map for downstream coding, planning, visualization, or conflict-detection agents.
---

# Generate Graph

## Purpose

Generate a lightweight, machine-readable architecture map for the current repository.

The canonical output is `.graph/graph.json`. Any lookup files or visualizations must be generated from it.

Do not produce architecture documentation as the primary artifact. Produce an operational architecture IR that other agents can consume for planning, coding, visualization, and conflict detection.

## Output Contract

Write outputs under the repository root:

```text
.graph/
  graph.json
  graph_reverse.json
  architecture.mmd
```

Use these contract examples when uncertain about output shape:

```text
schemas/graph.example.json
schemas/graph_reverse.example.json
schemas/architecture.example.mmd
```

Use these labeled examples when uncertain about semantic grouping:

```text
references/*/app/
references/*/expected_out/graph.json
references/*/expected_out/graph_reverse.json
references/*/expected_out/architecture.mmd
```

Read reference examples before generating a graph for an unfamiliar framework, ambiguous repository structure, or first-time run.

## Core Rules

- Treat `.graph/graph.json` as the single source of truth.
- Generate `.graph/graph_reverse.json` from `.graph/graph.json`.
- Do not invent files, symbols, services, databases, queues, or external systems.
- Prefer 8-20 high-level architecture nodes for real repositories.
- For tiny repositories, fewer nodes are acceptable.
- Prefer architectural correctness over completeness.
- Exclude tests, DTOs, generated files, small utilities, and trivial helpers unless they define an architectural boundary.
- Every non-external node must map to at least one real artifact.
- Every edge must include evidence when possible.
- Put uncertainty in `warnings`; do not hide weak inferences.

## Workflow

### 1. Inspect Repository Shape

Read manifests and top-level structure first.

Look for:

```text
package.json
pyproject.toml
requirements.txt
go.mod
pom.xml
build.gradle
Cargo.toml
docker-compose.yml
Dockerfile
serverless.yml
template.yaml
```

Then inspect likely source roots:

```text
src/
app/
backend/
server/
api/
services/
workers/
cmd/
internal/
lib/
```

Identify language, framework, runtime, and deployment shape.

### 2. Identify Entrypoints

Find where execution enters the system.

Examples:

```text
HTTP app bootstrap
route registration
server handlers
CLI commands
queue consumers
cron jobs
serverless handlers
main functions
frontend route/page roots
```

Entrypoints usually become nodes or evidence for nodes.

### 3. Identify Architectural Boundaries

Group files by responsibility, not by raw folder structure alone.

Common boundaries:

```text
API layer
domain service
repository/store
database/session layer
background worker
scheduler
queue/event bus
external integration client
auth/session layer
configuration/runtime layer
```

Use directory layout, imports, naming, framework conventions, and call relationships as evidence.

### 4. Create Candidate Nodes

Create coarse symbolic components.

Each node must include:

```text
id
label
type
description
artifacts
```

Each artifact reference should use:

```text
path
symbols
```

Allowed node types:

```text
entrypoint
component
service
store
queue
worker
scheduler
external
shared
config
```

Node IDs must be stable and machine-friendly:

```text
entrypoint.http-api
component.auth
service.todo
store.todo-db
queue.email-jobs
worker.email
external.smtp-provider
```

Avoid IDs based only on current labels if a stable architectural name is available.

### 5. Identify Edges

Add relationships between nodes.

Allowed relationship types:

```text
calls
depends_on
reads
writes
publishes
subscribes
serves
uses
configures
```

Each edge must include:

```text
id
source
target
type
description
evidence
```

Evidence should point to real files and, where useful, symbols. Do not add `kind`, `role`, or `snippet_hint` fields unless the user explicitly asks for a richer contract.

### 6. Write `graph.json`

Write the canonical graph to:

```text
.graph/graph.json
```

Include:

```text
metadata
nodes
edges
warnings
```

The graph must be valid JSON. Do not include comments.

### 7. Validate `graph.json`

Before finishing, verify:

```text
JSON parses
node IDs are unique
edge IDs are unique
edge source/target IDs exist
artifact paths exist
symbol hints are plausible by text search where practical
node types are from the allowed set
relationship types are from the allowed set
external nodes are clearly marked
warnings exist for uncertain relationships
```

Fix invalid output before writing derived files.

### 8. Generate `graph_reverse.json`

Generate reverse mappings from `graph.json`.

Write to:

```text
.graph/graph_reverse.json
```

This file maps repository artifacts back to graph nodes and relationships.

It should answer:

```text
Which component owns this file?
Which symbols belong to which node?
Which edges is this artifact evidence for?
```

`graph_reverse.json` must contain only these top-level keys:

```text
metadata
artifacts
```

Do not add root-level `nodes`, `edges`, `components`, `relationships`, summaries, or other indexes. Those duplicate `.graph/graph.json`.

Each `artifacts` entry must use this shape:

```text
path:
  nodes:
    - id
      symbols
  edges
```

Use `nodes` even when there is only one node, because shared files such as `docker-compose.yml`, framework app bootstraps, or config files may map to multiple architecture nodes.

Do not add facts to `graph_reverse.json` that are not derivable from `graph.json`.

Validate `graph_reverse.json` before finishing:

```text
top-level keys are exactly metadata and artifacts
each artifact path appears in graph.json node artifacts or edge evidence
each artifact node id exists in graph.json nodes
each artifact edge id exists in graph.json edges
no root-level nodes or edges dictionaries are present
```

### 9. Generate `architecture.mmd`

Generate:

```text
.graph/architecture.mmd
```

Generate Mermaid from `graph.json`. Do not treat Mermaid as canonical.

Validate `architecture.mmd` before finishing:

```text
file exists at .graph/architecture.mmd
diagram is generated from graph.json nodes and edges
diagram contains no nodes or edges absent from graph.json
```

### 10. Report Warnings

Report unresolved uncertainty clearly.

Examples:

```text
symbol not found
relationship inferred from naming only
external integration likely but not directly configured
file could belong to multiple components
repository too small for 8 nodes
```

## Reference Usage

Use the reference examples as labeled input/output pairs.

Each reference contains:

```text
app/           synthetic input repository
expected_out/  target graph.json, graph_reverse.json, and architecture.mmd
```

When reading references, compare:

```text
source files -> chosen nodes
imports/calls -> chosen edges
artifacts -> reverse mappings
graph nodes/edges -> Mermaid diagram
```

Do not copy reference node names unless they match the target repository. Use references to learn structure and output style.

## Output Quality Bar

A good graph:

- is compact enough to fit into another agent's context
- maps every component to real code
- makes task/component conflict detection possible
- can be rendered directly by a frontend
- can be validated mechanically
- uses stable IDs
- avoids documentation-only prose
