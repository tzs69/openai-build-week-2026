# Merge Marshal API

The FastAPI backend is authoritative for graph validation, projection, planning impact, conflicts, dependencies, and task state. It serves the configured repository's canonical `.graph/graph.json`; proposed architecture remains a run overlay and does not mutate that artifact.

Implemented endpoints:

```text
GET  /api/graph
POST /api/runs
GET  /api/runs/{run_id}
GET  /api/health
```

Planning runs are intentionally stored in memory for the current slice.

From the repository root, create the environment and install both local Python packages:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install --no-use-pep517 -e ./hierarchical-graph -e './backend[test]'
```

Start the API:

```bash
backend/.venv/bin/uvicorn merge_marshal_api.app:app --reload --port 8000
```

Use another target repository if required:

```bash
MERGE_MARSHAL_TARGET_REPO=/absolute/path/to/repo backend/.venv/bin/uvicorn merge_marshal_api.app:app --port 8000
```

Run backend tests:

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests -v
```
