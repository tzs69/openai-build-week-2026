# Hierarchical Graph Reference

## Canonical contract

The `hgraph` package owns and validates the `.graph/graph.json` contract:

```json
{
  "schema_version": "1.0",
  "metadata": {
    "repo_name": "example",
    "repo_root": ".",
    "languages": ["python"],
    "frameworks": ["fastapi"],
    "source_roots": ["backend/"]
  },
  "nodes": [],
  "edges": []
}
```

## Node payload

Pass the parent separately so `hgraph` verifies it before writing:

```bash
hgraph put-node --repo . --parent agent-orchestration --input - <<'JSON'
{
  "id": "conflict-detection",
  "label": "Conflict Detection",
  "type": "component",
  "description": "Detects collisions between agent change contracts.",
  "scope": {
    "artifacts": [
      {
        "path": "backend/conflicts/detector.py",
        "symbols": ["ConflictDetector", "detect_conflicts"],
        "ownership": "primary"
      },
      {
        "path": "backend/contracts/models.py",
        "symbols": ["ChangeContract"],
        "ownership": "shared"
      }
    ]
  }
}
JSON
```

Allowed node types are `entrypoint`, `component`, `service`, `store`, `queue`, `worker`, `scheduler`, `external`, `shared`, and `config`.

Parent nodes may use directories for orientation or have no artifacts. A non-external leaf must reference at least one concrete file. External leaves may have an empty artifact list.

## Edge payload

```bash
hgraph put-edge --repo . --input - <<'JSON'
{
  "id": "orchestrator-calls-conflict-detection",
  "source": "agent-orchestrator",
  "target": "conflict-detection",
  "type": "calls",
  "label": "Checks plans for collisions",
  "evidence": [
    {
      "path": "backend/orchestrator.py",
      "symbols": ["Orchestrator.validate_plans"]
    }
  ]
}
JSON
```

Allowed relationship types are `calls`, `depends_on`, `reads`, `writes`, `publishes`, `subscribes`, `serves`, `uses`, and `configures`.

An edge represents a relationship needed for architecture or change-impact reasoning. A raw import is insufficient unless it establishes that meaningful relationship.

## Projection and updates

`hgraph project` is read-only. The selected root is depth zero. Hidden descendants collapse to their nearest visible ancestor, and equivalent visible relationships retain their canonical IDs in `aggregated_edge_ids`.

`put-node` and `put-edge` upsert by ID. Parent nodes and edge endpoints must already exist. `delete-node` refuses nodes with children or incident edges; `--cascade` removes a verified stale subtree and its incident edges. All mutations replace `graph.json` atomically.

