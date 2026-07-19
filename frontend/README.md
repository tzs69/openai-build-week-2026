# Merge Marshal Frontend

React frontend for viewing generated codebase architecture graphs.

## Prerequisites

- Node.js `20.19+` or `22.12+`
- npm
- Google Chrome, only when running the browser tests

## Start locally

From the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` in a browser.

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

## Graph fixtures

Static graph fixtures live under `public/fixtures/`. The frontend currently loads `public/fixtures/test-repo-2/` as configured in `src/data/graphData.ts`.

Each active fixture requires one canonical artifact:

```text
graph.json
```

`graph.json` drives the visualization and contains node scope plus edge evidence. The frontend derives its artifact lookup index from this file at load time.
