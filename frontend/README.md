# Merge Marshal Frontend

React frontend for exploring backend-projected hierarchical codebase graphs.

## Prerequisites

- Node.js `20.19+` or `22.12+`
- npm
- The backend environment described in [`../backend/README.md`](../backend/README.md)
- Google Chrome when running the browser tests

## Start locally

Start the FastAPI backend from the repository root:

```bash
backend/.venv/bin/uvicorn merge_marshal_api.app:app --reload --port 8000
```

Then start the frontend in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` requests to `http://127.0.0.1:8000`.

The frontend does not read graph files directly. It requests root/depth projections from `GET /api/graph`, renders them with React Flow, and keeps layout, selection, and breadcrumbs in browser memory.

## Verification

```bash
cd frontend
npm run lint
npm run build
npm run test:e2e
```

The Playwright configuration starts both FastAPI and Vite. The suite covers desktop and mobile graph loading, executor-scope and edge-evidence inspection, hierarchy drill-down, backend failures, malformed responses, and layout collisions.
