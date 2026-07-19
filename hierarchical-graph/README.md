# Hierarchical Codebase Graph

`hgraph` deterministically creates, updates, validates, and projects the canonical `.graph/graph.json` used for codebase visualization and task-executor scoping.

Install locally:

```bash
python3 -m pip install -e ./hierarchical-graph
```

For older pip in an offline environment, use the included setuptools compatibility path:

```bash
python3 -m pip install --no-use-pep517 -e ./hierarchical-graph
```

Then run:

```bash
hgraph --help
```

The CLI owns the graph contract and persistence behavior. Agent-specific analysis guidance lives separately in `.agents/skills/generate_hierarchical_graph/`.
