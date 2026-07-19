# Merge Marshal Frontend

React frontend for viewing generated codebase architecture graphs.

## Prerequisites

- Node.js `20.19+` or `22.12+`
- npm
- Google Chrome, only when running the browser tests

## Start locally

Start the backend first by following [`../backend/README.md`](../backend/README.md).
It serves the configured repository graph at `http://127.0.0.1:8000/api/graph`.

Then start the frontend from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` in a browser.

During development, Vite proxies `/api/*` requests to `http://127.0.0.1:8000`.
Set `VITE_API_TARGET` before starting Vite to use a different backend origin.

Use `npm ci` after pulling the repository. It installs the exact dependency versions recorded in `package-lock.json`. Do not run `npm init`; the project and its dependencies are already defined by `package.json` and `package-lock.json`.

## Production build

```bash
cd frontend
npm ci
npm run build
npm run preview
```

`npm run build` generates `frontend/dist/`. Both `dist/` and `node_modules/` are intentionally ignored because they can be reproduced from the tracked source files and lockfile.

## Verification

```bash
npm run lint
npm run build
npm run test:e2e
```

The Playwright suite uses a locally installed Chrome browser and covers desktop and mobile graph rendering, selection, warning states, fixture failures, and edge-label collisions.

## Graph API and fixtures

The application loads the canonical artifact through `GET /api/graph`. The
fetch and normalization logic remains isolated in `src/data/graphData.ts`.

Static graphs under `public/fixtures/` are retained only as deterministic
frontend test data; they are not the runtime graph source.

Each active fixture requires one canonical artifact:

```text
graph.json
```

`graph.json` drives the visualization and contains node scope plus edge evidence. The frontend derives its artifact lookup index from this file at load time.
