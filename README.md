# Merge Marshal

Merge Marshal is an interactive proof that architecture-grounded coordination can make concurrent coding-agent plans understandable before implementation.

The current product loads a real hierarchical graph from FastAPI and overlays a deterministic three-task coordination plan. It shows architecture impact, proposed nodes and edges, blocking evidence, hierarchy drill-down, and the derived ready/conditional execution batches.

## Repository layout

```text
hierarchical-graph/   Canonical graph toolkit and hgraph CLI
demo/target-repo/    Curated user/payment codebase and .graph/graph.json
backend/             FastAPI graph and coordination API
frontend/            React Flow architecture and plan explorer
```

Product scope is defined in [`MVP_NORTH_STAR.md`](./MVP_NORTH_STAR.md). Delivery status and dependencies are defined in [`MVP_IMPLEMENTATION_PLAN.md`](./MVP_IMPLEMENTATION_PLAN.md).

## Install

From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install --no-use-pep517 -e ./hierarchical-graph -e './backend[test]'
cd frontend
npm ci
```

## Run

Start the backend from the repository root:

```bash
backend/.venv/bin/uvicorn merge_marshal_api.app:app --reload --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`.

## Verify the implemented horizontal slices

From the repository root:

```bash
PYTHONPATH=demo/target-repo/src python3 -m unittest discover -s demo/target-repo/tests -v
backend/.venv/bin/hgraph validate --repo demo/target-repo
backend/.venv/bin/python -m unittest discover -s backend/tests -v
cd frontend
npm run lint
npm run build
npm run test:e2e
```

`npm run test:e2e` starts both local servers and verifies the browser-to-backend path.
