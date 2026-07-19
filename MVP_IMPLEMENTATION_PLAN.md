# Merge Marshal MVP Implementation Plan

## Purpose

This document turns [`MVP_NORTH_STAR.md`](./MVP_NORTH_STAR.md) into an ordered implementation plan. It should be updated as slices are completed, but the north-star behavior remains the authority for what the MVP must prove.

The implementation rule is simple:

> Build the smallest complete path through the system, then add coordination behavior to that path. Do not build model workers or real code execution before the deterministic product story works end to end.

## First horizontal slice checklist

- [x] Create the curated demo repository and starting behavior tests.
- [x] Generate and validate its canonical hierarchical graph.
- [x] Serve root/depth graph projections through FastAPI.
- [x] Migrate the frontend to the canonical API schema.
- [x] Add hierarchy drill-down, breadcrumbs, scope, ownership, and evidence inspection.
- [x] Replace old runtime fixture and reverse-map dependencies.
- [x] Add backend and browser integration coverage.
- [x] Document clean installation, run, and verification commands.

**Status:** Complete.

## Second horizontal slice checklist

- [x] Add extensible `ChangeContract` and polymorphic `ChangeEffect` models.
- [x] Support proposed architecture nodes and edges without mutating `graph.json`.
- [x] Validate contracts against canonical nodes, paths, and proposed IDs.
- [x] Resolve direct, downstream, and uncertain impact for each graph projection.
- [x] Derive conflicts and task dependencies from normalized resource interactions.
- [x] Derive A and C as ready while stale B is blocked pending replan.
- [x] Add in-memory `POST /api/runs` and `GET /api/runs/{run_id}` endpoints.
- [x] Add task cards, schedule, overlays, proposed graph elements, and evidence UI.
- [x] Add backend and browser coverage for the complete planning workflow.

**Status:** Complete. The next horizontal slice is Phase 3: approval and coordination playback.

## Current repository state

The first two horizontal slices are implemented. The repository now has a live architecture path and a deterministic planning path:

- `hierarchical-graph/` is a deterministic Python toolkit for creating, validating, reading, and projecting the canonical `.graph/graph.json`. Its eight tests pass when run with `PYTHONPATH=src`.
- `demo/target-repo/` is the curated user/payment codebase for Tasks A, B, and C. Its three starting tests pass and its canonical graph validates with nine nodes and five evidence-backed edges.
- `backend/` validates and serves graph projections, validates varied change effects, resolves projection-aware impact, derives conflicts/dependencies/schedules, and stores planning runs in memory. Its graph and coordination tests pass.
- `frontend/` loads graph projections and run snapshots from the backend, renders task state and evidence, remaps impact during hierarchy drill-down, and renders proposed architecture as non-canonical overlays. Its lint, build, and API-backed Playwright suite pass.

The obsolete runtime graph fixtures, reverse maps, and Mermaid projections have been removed from the frontend. The remaining MVP gaps begin at coordination playback:

- There is no approval command, execution state machine, event stream, contract version-two replan, implementation result, or plan-versus-actual comparison yet.

The next implementation target is Phase 3: approve the derived plan, play back A and C together, preserve stale Task B as blocked, introduce its compatible version-two contract, and only then allow B to proceed.

## Dependency chain

```text
Curated demo code
  → stable canonical graph and node IDs
  → graph API and frontend graph contract
  → change-contract fixtures and validation
  → impact calculation
  → conflict detection and dependency scheduling
  → plan overlays and coordination explanation
  → approval, state transitions, events, and replanning
  → implementation-result comparison
  → final graph diff and repeatable demo
```

The important constraint is that a `ChangeContract` uses typed, extensible effects rather than one flat list of key/value edits. Effects may describe artifact, symbol, behavior, test, configuration, architecture-node, or architecture-edge changes. Existing targets refer to stable graph node IDs, artifact paths, symbols, or resource IDs; proposed architecture elements use task-scoped proposed IDs. The contract may claim diagram impact, but the backend validates and expands those claims against the canonical graph. The UI only renders the resolved impact returned by the backend.

## Implementation phases

### Phase 1: Establish the live architecture path

Create the curated demo repository and its canonical hierarchical graph. Add a small FastAPI backend that validates and projects that graph using `hierarchical-graph/`. Migrate the existing frontend from the old fixture schema to `GET /api/graph` and make hierarchy navigable at depth one or two.

Outcome: a viewer opens Merge Marshal, sees the actual demo architecture supplied by the backend, drills into a component, and inspects its artifacts and edge evidence. No static reverse map is involved.

This phase is the direct next implementation chunk and is specified in detail below.

### Phase 2: Show a coordinated plan before execution

Freeze the minimum domain schemas for `Task`, `ChangeContract`, polymorphic `ChangeEffect`, `DiagramImpact`, `Conflict`, `Dependency`, and `RunSnapshot`. A change effect has a common machine-readable resource interaction (`produce`, `consume`, `mutate`, or `retire`) plus a kind-specific payload and human-readable intent. Architecture effects can propose creating, updating, moving, or removing graph nodes and edges. Proposed elements render as overlays only; they do not mutate `.graph/graph.json` before implementation is verified.

Create the three curated tasks and version-one contract fixtures against the stable demo graph. Implement schema and domain validation, backend-resolved diagram impact, deterministic resource-based conflict detection, dependency construction, cycle detection, and ready-batch calculation. Submission order must not determine correctness; it is only a stable display tie-breaker for otherwise independent tasks. A future model may propose contracts or classify ambiguous relationships, but deterministic backend code remains authoritative for blocking and scheduling.

Store the run in memory with only planning-time states such as `PLANNED`, `READY`, and `BLOCKED`. Do not manufacture `RUNNING` or `COMPLETED` states in this phase. Expose run creation and retrieval endpoints that return the complete coordination snapshot.

Extend the one-screen frontend with three task cards, task-colored graph overlays, proposed-node/edge styling, impact styles, the currently ready batch, and an inspector explaining each effect, impact, and conflict. At the end of this phase the user must see that Task A blocks Task B's stale contract, Task C can run with Task A, and Task B requires replanning before it becomes executable.

Outcome: the core hackathon claim is visible and is derived by deterministic logic rather than hard-coded task statuses.

### Phase 3: Add approval and coordination playback

Implement the backend task-state machine and ordered `RunEvent` records. Add the approval command. Simulate Task A and Task C running together, keep Task B blocked, then load Task B contract version two after Task A completes. Preserve both Task B contract versions. Only the compatible version-two contract allows Task B into a later execution batch. Deliver state changes through SSE, using polling only as a time-boxed fallback.

The backend remains authoritative for task status. Begin with in-memory state; add SQLite here only if process-restart persistence is needed for the demo. Actual worker completion and verified repository changes remain later concerns, so `COMPLETED` is produced only by the explicit playback/state-transition mechanism, never inferred from the planning contract.

Add the approval control, live task statuses, conflict-to-replan explanation, and event timeline to the frontend.

Outcome: the viewer watches the safe order occur and can see exactly how Task B changed from `user_id` to `actor_id` before it was allowed to run.

### Phase 4: Close the loop with planned versus actual

Create prepared `ImplementationResult` fixtures and a post-change graph for the demo. Implement deterministic plan-versus-actual classification and graph diffing. Add verification and completion events.

Render planned-and-changed, planned-but-unchanged, out-of-plan, added, removed, uncertain, and test-result categories in the final frontend state. Keep plan overlays in run history, never in the canonical graph.

Outcome: the product proves not only that it coordinated plans, but that it checked whether the completed work respected those plans.

### Phase 5: Make the demo repeatable and defensible

Add backend unit tests for schemas, graph delivery, impact rules, conflicts, scheduling, state transitions, comparison, and error cases. Replace old frontend fixture tests with API-shaped tests and add one Playwright test covering the full story. Document exact install, start, test, and reset commands. Add a single demo reset mechanism so every presentation starts from the same state.

Outcome: a clean checkout can reproduce the full story without editing JSON or source files during the presentation.

### Phase 6: Add intelligence only after the MVP works

If time remains, replace one prepared planner contract with a real model call that receives the task, graph projection, and relevant repository context, then returns schema-constrained output for the same validator. Keep deterministic coordination authoritative. Live implementation workers and graph regeneration come after this, not before it.

Outcome: the demo gains one credible live AI boundary without making the core visual coordination story unreliable.

## Completed horizontal slice 1: live hierarchical architecture

### User-visible result

Starting the backend and frontend should produce this complete behavior:

```text
Open Merge Marshal
  → frontend calls GET /api/graph?depth=1
  → backend validates the demo repository's .graph/graph.json
  → backend returns a derived projection
  → frontend renders its nodes and aggregated edges
  → user selects or drills into a component
  → frontend requests GET /api/graph?root=<node-id>&depth=1
  → inspector shows node scope or edge evidence
```

This is a useful horizontal slice because it crosses the target repository, canonical data, deterministic toolkit, backend, frontend, and tests while remaining small. It establishes the contracts and IDs needed by every later feature.

This slice originally excluded tasks, contracts, overlays, coordination, chat, SSE, and model calls. Phase 2 has since added the planning portions while chat, SSE, and model calls remain excluded.

## Vertical slices completed in horizontal slice 1

### Vertical slice 1: Create the demo substrate

Add one small target repository under `demo/target-repo/` with enough real code and tests to support the later story:

- A user response schema containing `UserResponse.user_id`.
- A user endpoint or service that produces that response.
- A natural place for Task B to add response caching while consuming the canonical identity field.
- A payment endpoint or service that Task C can modify independently for structured logging.
- Tests proving the starting behavior.

Generate `demo/target-repo/.graph/graph.json` with stable nodes for the user API/schema area and the independent payment area. Validate it with `hgraph`. Keep ordinary classes and functions as artifact symbols unless they are architecturally significant.

Done when the demo tests pass, `hgraph validate --repo demo/target-repo` passes, the graph contains no temporary plan data, and its node IDs are suitable for all three future contracts.

### Vertical slice 2: Serve the canonical graph through FastAPI

Create the application backend with a configurable target-repository path. Implement a graph service that calls the existing toolkit's load, validation, and `build_projection` behavior rather than duplicating it.

Implement:

```http
GET /api/graph?root={optional_node_id}&depth={0_to_2}
```

Return the canonical schema fields plus projection metadata and any `aggregated_edge_ids`. Reject an unknown root, unsupported depth, missing graph, or invalid graph with a clear HTTP error. Do not create or return `graph_reverse.json`.

Add backend tests that compare the HTTP response with the toolkit's projection for the same graph.

Done when changing the configured target graph changes the API response without changing backend or frontend code.

### Vertical slice 3: Migrate the frontend data boundary

Replace the old TypeScript graph shapes with the canonical projection shape:

- `schema_version` is top-level.
- A node includes `parent_id` and `scope.artifacts`.
- An artifact includes `ownership`.
- An edge uses `label`, `evidence`, and optional `aggregated_edge_ids`.
- The response contains `projection` metadata.
- There is no reverse-map or persisted-warning dependency.

Create a small API client and make `GraphPage` load `/api/graph?depth=1`. Adapt the existing React Flow conversion, node card, edge label, header, and details inspector rather than rewriting them.

Done when the graph screen is backed only by the API, loading and errors remain clear, and node scope plus edge evidence are visible in the inspector.

### Vertical slice 4: Make hierarchy explorable

Add a minimal hierarchy interaction: drill into a selected component by requesting it as `root`, show the active root and depth as a breadcrumb, and provide a way back to the top-level projection. Keep layout, zoom, selection, and breadcrumbs in frontend memory.

Do not attempt a fully expandable compound-node layout in this slice. Backend projection plus drill-down proves hierarchy with much lower layout risk; nested rendering can be evaluated later if it improves the demo.

Done when a user can move between a top-level view and a one-level child view without loading another page or reading raw JSON.

### Vertical slice 5: Lock the integration with tests and commands

Configure the development connection through a Vite proxy or one explicit frontend API base URL. Add documented commands for installing and starting both applications. Update browser tests to intercept `/api/graph`, assert the new schema, exercise drill-down, and verify missing/invalid graph errors. Delete old fixture dependencies only after replacement coverage passes.

Done when backend tests, frontend lint/build, and the focused Playwright graph tests pass from documented commands.

## Files established by horizontal slice 1

The precise Python module names may vary, but the responsibility boundaries should resemble:

```text
backend/
  pyproject.toml
  src/merge_marshal_api/
    app.py                 FastAPI construction and route wiring
    settings.py            configured target-repository path
    graph_routes.py        HTTP parsing and errors
    graph_service.py       toolkit validation and projection adapter
  tests/
    test_graph_api.py

demo/
  target-repo/
    .graph/graph.json      canonical current architecture
    src/                   curated user and payment code
    tests/                 starting-behavior tests

frontend/src/
  api/graphClient.ts       GET /api/graph
  types/graphTypes.ts      canonical projection types
  data/graphAdapter.ts     projection-to-React-Flow adapter
  components/GraphPage.tsx
  components/ArchitectureGraph.tsx
  components/DetailsPanel.tsx
```

Phase 2 added pure coordination logic under `backend/src/merge_marshal_api/coordination/`. It can be extracted into a standalone `coordination-core/` package later if a second consumer appears; extraction is not required for the MVP.

## Phase 2 entry gate — passed

Do not begin contract or overlay work until all of these statements are true:

- The demo repository exists and its starting tests pass.
- Its canonical graph validates and contains stable IDs for Tasks A, B, and C.
- FastAPI serves toolkit-derived root/depth projections.
- The frontend no longer imports graph fixtures or a reverse map.
- A user can inspect artifacts, symbols, ownership, hierarchy, and edge evidence.
- Backend and frontend tests protect that path.

This gate passed. Phase 2 now creates one run whose three validated contracts produce visible overlays and derive A-blocks-stale-B while C remains independent. The active next target is Phase 3 approval and coordination playback.
