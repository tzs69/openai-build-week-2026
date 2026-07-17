# Merge Marshal

> **Merge Marshal provides cross-task concurrency control for coding agents.**

## Table of Contents

- [1. Product Overview](#1-product-overview)
  - [Core Thesis](#core-thesis)
  - [The Problem](#the-problem)
  - [What Merge Marshal Adds](#what-merge-marshal-adds)
  - [Product Positioning](#product-positioning)
  - [What Merge Marshal Is Not](#what-merge-marshal-is-not)
- [2. User Workflow](#2-user-workflow)
- [3. Coordination Model](#3-coordination-model)
  - [Coordination Timing](#coordination-timing)
  - [Commit Model](#commit-model)
  - [Real-Time Semantics](#real-time-semantics)
- [4. Runtime Architecture](#4-runtime-architecture)
  - [System Architecture](#system-architecture)
  - [Why GitHub Actions?](#why-github-actions)
  - [Hackathon Hosting Model](#hackathon-hosting-model)
  - [Target Repository Workflow Ownership](#target-repository-workflow-ownership)
  - [Runner Concurrency Model](#runner-concurrency-model)
  - [No Frontend For The MVP](#no-frontend-for-the-mvp)
- [5. Coordinator Internals](#5-coordinator-internals)
  - [Responsibility Boundaries](#responsibility-boundaries)
  - [Coordinator State Store (DB)](#coordinator-state-store)
  - [Change Contracts](#change-contracts)
  - [Conflict Detection](#conflict-detection)
  - [Dependency Graph and Scheduling](#dependency-graph-and-scheduling)
  - [Task Status Labels and Transitions](#task-status-labels-and-transitions)
- [6. Patch and Execution Model](#6-patch-and-execution-model)
  - [Branch and Patch Model](#branch-and-patch-model)
- [7. Demo and MVP Scope](#7-demo-and-mvp-scope)
  - [Demo Scenario](#demo-scenario)
  - [Hackathon MVP Scope](#hackathon-mvp-scope)
  - [Known Limitation: Merge Marshal Must Own Execution](#known-limitation-merge-marshal-must-own-execution)
- [8. Security Model](#8-security-model)
- [9. Repository Layout and Build Order](#9-repository-layout-and-build-order)
  - [Suggested Repository Layout](#suggested-repository-layout)
  - [Recommended Build Order](#recommended-build-order)
- [10. Success Criteria and Final Mental Model](#10-success-criteria-and-final-mental-model)
  - [Success Criteria](#success-criteria)
  - [Final Mental Model](#final-mental-model)
- [11. References](#11-references)

Merge Marshal is a pre-execution coordination layer for teams delegating software work to AI coding agents.

Modern agentic development workflows are beginning to treat a GitHub issue, ticket, or natural-language task as an executable unit of engineering work:

```text
Developer defines an issue
        ↓
Coding agent inspects the repository
        ↓
Agent implements the task on an isolated branch or runner
        ↓
Agent runs tests
        ↓
Agent opens a pull request for human review
```

GitHub's coding-agent workflows already support assigning an issue to an agent that works asynchronously and raises a pull request. Codex can likewise be integrated into GitHub Actions and other automated repository workflows.

These systems are effective at executing **one task at a time**. The coordination problem appears when several tasks are delegated concurrently against the same repository state.

Without a coordination layer, each agent may produce a locally valid change while relying on assumptions another active task is about to invalidate.

Merge Marshal sits between task submission and coding-agent execution:

```text
GitHub issues
      ↓
Merge Marshal planning and coordination
      ↓
Safe tasks run concurrently
Dependent tasks wait and replan
      ↓
Coding agents implement
      ↓
Verified patches are integrated
      ↓
Final pull request
```

Its primary question is not:

> Can an agent implement this issue?

It is:

> Should this agent begin now, and which other active task results must it account for first?

---

## 1. Product Overview

### Core Thesis

Git prevents textual collisions after code is written.

Merge Marshal prevents high-confidence semantic collisions before coding agents begin implementation.

Two branches can:

- Modify different files.
- Produce no Git merge conflict.
- Pass their isolated tests.
- Still become incompatible when combined.

Merge Marshal addresses this by extracting structured plans from all active tasks, identifying cross-task contract dependencies, and controlling execution order.

---

### The Problem

Assume two issues are delegated from the same commit.

#### Task A

Rename:

```text
UserResponse.user_id
```

to:

```text
UserResponse.actor_id
```

#### Task B

Add response caching using the user identity.

Task B may independently generate:

```python
cache_key = f"user:{response.user_id}"
```

Task A may modify:

```text
src/schemas/user.py
```

Task B may modify:

```text
src/services/user_cache.py
```

Git sees no overlapping lines.

Both branches may pass their own narrow tests.

After integration, Task B depends on a field that Task A removed.

```text
Task A removes a contract.
Task B consumes that contract.
```

This is a producer-consumer semantic conflict.

---

### What Merge Marshal Adds

An individual coding agent is responsible for one task:

```text
Understand issue
Inspect repository
Plan implementation
Write code
Run tests
Open PR
```

Merge Marshal operates one level above the agents:

```text
Understand all active tasks
Compare intended changes
Identify dependency edges
Schedule agent execution
Replan stale downstream tasks
Verify combined integration
```

The distinction is:

```text
Coding agent:
How should I implement this task?

Merge Marshal:
Should this task begin now, and what must happen before it does?
```

Merge Marshal does not compete with Codex, GitHub Copilot, Claude Code, or similar coding agents.

It coordinates their execution.

---

### Product Positioning

#### One-line description

> Merge Marshal is an orchestration layer between engineering tasks and coding-agent execution that coordinates concurrent tasks before they become incompatible pull requests.

#### Short analogy

> Air-traffic control for coding agents working on the same codebase.

#### Precise USP

> Merge Marshal provides cross-task concurrency control for coding agents.

It does this by:

1. Planning tasks before implementation.
2. Extracting the contracts each task consumes, changes, or produces.
3. Building a dependency graph across active tasks.
4. Running independent tasks in parallel.
5. Blocking tasks that depend on unfinished upstream changes.
6. Replanning blocked tasks against verified upstream code.
7. Verifying and integrating the resulting patches.

---

### What Merge Marshal Is Not

Merge Marshal is not primarily:

- An AI pull-request reviewer.
- A post-push semantic conflict detector.
- A Git merge-conflict resolver.
- A bot watching developers type.
- A shared vector-memory system for agents.
- A replacement for CI, type checking, tests, or human review.

A post-push analyser asks:

> Are these completed branches compatible?

Merge Marshal asks earlier:

> Should these planned tasks execute concurrently at all?

Actual diffs are still inspected after implementation, but that is verification—not the initial invocation.

---

## 2. User Workflow

### 1. Developer creates a GitHub issue

The issue acts as a delegated engineering task.

```text
Title:
Add Redis caching to user responses

Description:
Cache successful GET /users/{id} responses for five minutes.

Acceptance criteria:
- Cache hits avoid a database query
- User updates invalidate the matching cache entry
- Existing API behaviour remains unchanged
```

### 2. Developer applies `marshal:ready`

The label means:

> Merge Marshal may take ownership of planning and executing this task.

It is the hackathon MVP's main invocation mechanism.

```text
GitHub issue + marshal:ready
        ↓
Task registered with Merge Marshal
```

The developer does **not** manually launch Codex for that task.

Merge Marshal must own agent execution; otherwise it cannot enforce a blocked scheduling decision.

### 3. GitHub Action registers the task

A workflow in the target repository listens for an issue receiving the label.

```yaml
name: Register Merge Marshal Task

on:
  issues:
    types: [labeled]

jobs:
  register:
    if: github.event.label.name == 'marshal:ready'
    runs-on: ubuntu-latest

    steps:
      - name: Register task
        env:
          MERGE_MARSHAL_URL: ${{ secrets.MERGE_MARSHAL_URL }}
          CALLBACK_TOKEN: ${{ secrets.MERGE_MARSHAL_CALLBACK_TOKEN }}
          ISSUE_TITLE: ${{ github.event.issue.title }}
          ISSUE_BODY: ${{ github.event.issue.body }}
        run: |
          jq -n \
            --arg repository "${{ github.repository }}" \
            --argjson issue_number "${{ github.event.issue.number }}" \
            --arg title "$ISSUE_TITLE" \
            --arg body "$ISSUE_BODY" \
            --arg base_branch "main" \
            '{
              repository: $repository,
              issue_number: $issue_number,
              title: $title,
              body: $body,
              base_branch: $base_branch
            }' > task.json

          curl --fail-with-body \
            -X POST "$MERGE_MARSHAL_URL/api/tasks" \
            -H "Authorization: Bearer $CALLBACK_TOKEN" \
            -H "Content-Type: application/json" \
            --data @task.json
```

The registration action sends:

- Repository name.
- Issue number.
- Issue title and body.
- Acceptance criteria. (within issue body)
- Target base branch. (`main` for the MVP)

It does not send a completed code diff because implementation has not started.

### 4. Merge Marshal captures an exact planning commit

GitHub issues are branch-agnostic. They do not inherently point at a feature branch or commit.

For the MVP, Merge Marshal uses a simple base policy:

```text
planning_base_branch = main
planning_base_commit = HEAD(main) when the task is registered
```

```text
main = abc123
```

Task record:

```json
{
  "task_id": "TASK-A",
  "issue_number": 10,
  "planning_base_commit": "abc123",
  "status": "REGISTERED"
}
```

The commit SHA is authoritative; the branch name may move later.

The coordinator resolves the current `main` HEAD through the GitHub API when it receives the task.

### 5. Merge Marshal dispatches read-only planning (per task received)

The coordinator launches a planning workflow for the registered task.

```text
Coordinator
    ↓ workflow_dispatch
GitHub Actions planning worker
    ↓
Checkout planning_base_commit
    ↓
Codex inspects repository read-only
    ↓
Structured change contract
```

No implementation code is written during this stage.

### 6. Merge Marshal compares active task contracts

Assume three tasks are registered:

```text
A: Rename user_id to actor_id
B: Add caching using user identity
C: Add payment logging
```

The change contracts indicate:

```text
Task A removes UserResponse.user_id.
Task B consumes UserResponse.user_id.
Task C is independent.
```

Merge Marshal creates:

```text
Task A ─── invalidates dependency ───▶ Task B

Task C
```

Scheduling result:

```text
Task A: READY
Task B: BLOCKED_BY Task A
Task C: READY
```

This happens before implementation agents begin writing.

### 7. Merge Marshal dispatches only ready tasks

```text
Coordinator
   ├── Run Task A
   ├── Run Task C
   └── Do not run Task B yet
```

Task A and Task C execute concurrently.

Task B remains blocked.

### 8. Completed patches return for verification

An implementation worker:

1. Checks out an exact execution commit.
2. Runs Codex in an isolated environment.
3. Runs task-level tests.
4. Produces a patch artifact.
5. Returns a structured result.

Example:

```json
{
  "task_id": "TASK-A",
  "changed_files": [
    "src/schemas/user.py",
    "src/api/users.py"
  ],
  "resources_removed": [
    "python:symbol:src/schemas/user.py::UserResponse.user_id"
  ],
  "resources_added": [
    "python:symbol:src/schemas/user.py::UserResponse.actor_id"
  ],
  "tests": {
    "passed": 18,
    "failed": 0
  }
}
```

Merge Marshal verifies whether the actual result matches the plan.

### 9. Blocked tasks replan against verified upstream changes

After Task A is applied to the integration branch:

```text
Task B planning base: abc123
Task B execution base: def456 (latest marshal/run-7 commit after Task A is applied)
```

Task B receives:

```text
Relevant upstream changes:

- UserResponse.user_id was removed.
- UserResponse.actor_id is now the canonical identity field.
- Do not introduce any dependency on user_id.
```

Task B replans and then implements:

```python
cache_key = f"user:{response.actor_id}"
```

### 10. Merge Marshal opens one integration PR

For the hackathon MVP, all verified task patches are applied to one coordination-run branch:

```text
main
  │
  └── marshal/run-7
          ├── Task A patch
          ├── Task C patch
          └── Task B patch after replanning
```

The final pull request is:

```text
marshal/run-7 → main
```

This avoids stacked-PR and branch-retargeting complexity.

---

## 3. Coordination Model

### Coordination Timing

Merge Marshal runs whenever a task enters its coordination queue.

For the MVP, that means:

```text
Developer applies marshal:ready
        ↓
marshal-register.yml sends the issue payload
        ↓
Merge Marshal registers the task
        ↓
Planning starts
        ↓
The task is compared against active unfinished tasks
```

Tasks do not need to be submitted at the exact same time. The relevant overlap is whether another task is still active and its result is not yet fully visible to downstream work.

Active tasks include:

```text
REGISTERED
PLANNING
ANALYSING
READY
RUNNING
BLOCKED
VERIFYING
REPLAN_REQUIRED
```

Terminal tasks are normally ignored for active conflict scheduling:

```text
COMPLETED
FAILED
CANCELLED
SUPERSEDED
```

Example rolling case:

```text
10:00  Task A receives marshal:ready.
10:02  Task A begins implementation.
10:05  Task B receives marshal:ready.
10:06  Task B is planned and compared against Task A.
10:07  Task B is blocked until Task A is verified and applied.
```

This is the concurrency window Merge Marshal protects: multiple delegated tasks whose implementation results are not yet visible to each other.

For the hackathon demo, a simple coordination run can still be seeded manually by labeling three issues close together. The production-shaped behavior is continuous: every new task is checked against all active unfinished task contracts before it is allowed to write code.

---

### Commit Model

Merge Marshal tracks three commit SHAs per task:

```json
{
  "planning_base_commit": "abc123",
  "execution_base_commit": "def456",
  "result_commit": "ghi789"
}
```

#### `planning_base_commit`

The repository snapshot inspected during the first read-only planning pass.

It answers:

```text
What code did the original plan assume?
```

For the MVP, all new issues default to the current `main` branch HEAD at registration time.

#### `execution_base_commit`

The repository snapshot the implementation worker actually writes against.

At first, this is usually the same as `planning_base_commit`:

```text
planning_base_commit = abc123
execution_base_commit = abc123
```

If a task is blocked by upstream work, the execution base changes after the required upstream patches are applied:

```text
planning_base_commit = abc123
execution_base_commit = def456
```

This is conceptually similar to a rebase. For blocked tasks, Merge Marshal updates `execution_base_commit` to the latest integration commit after the blocking upstream work is applied, then replans before implementation. This prevents the blocked task from eventually writing code against stale assumptions.

#### `result_commit`

The integration-branch commit created after the verified patch is applied to `marshal/run-X`.

It answers:

```text
What commit contains this accepted task result?
```

#### Example

```text
10:00 main = abc123

10:01 Task A registered:
      Rename UserResponse.user_id to actor_id.

10:01 Task B registered:
      Add caching using the user identity.

Task A planning_base_commit = abc123
Task B planning_base_commit = abc123

Merge Marshal detects:
Task A blocks Task B.

Task A runs first and is applied:
marshal/run-7 = def456

Task B is replanned:
Task B planning_base_commit = abc123
Task B execution_base_commit = def456

Task B now implements against code where actor_id is canonical.

Task B is applied:
marshal/run-7 = ghi789
Task B result_commit = ghi789
```

The important signal is when `planning_base_commit` and `execution_base_commit` differ. That means Merge Marshal prevented a stale implementation by moving the task onto the verified upstream integration state before code was written.

---

### Real-Time Semantics

Merge Marshal does not continuously read an agent's private chain of thought or inject instructions halfway through a run.

For the MVP, "real time" means:

```text
Task enters execution queue
        ↓
Planning starts immediately
        ↓
Plan is compared with active tasks
        ↓
Task is approved, blocked, or escalated
```

A more accurate description is:

> Near-real-time coordination at the task-planning boundary.

Once a worker starts, its execution context is frozen. Merge Marshal waits for completion, verifies the result, and then updates downstream tasks.

Live interruption, rollback, and session resumption are future capabilities.

---

## 4. Runtime Architecture

### System Architecture

The hackathon implementation uses a deliberately lightweight architecture:

- Merge Marshal runs as a long-lived FastAPI coordinator.
- GitHub Actions runners execute target-repository work.
- SQLite stores task state, contracts, dependencies, and worker results.
- GitHub Issues, Actions logs, artifacts, comments, and the final pull request are the MVP product surface.

For the hackathon, Merge Marshal should run locally on a developer laptop and be exposed to GitHub through a public tunnel such as ngrok or Cloudflare Tunnel.

Do not run the coordinator as a GitHub Actions job. A GitHub-hosted runner is temporary: it appears for one workflow job, runs steps, uploads logs or artifacts, and disappears. Merge Marshal needs to remain alive so it can receive registrations, dispatch follow-up workflows, track blocked tasks, and update downstream execution state.

```text
Target GitHub repository
        │
        │ issue labeled marshal:ready
        ▼
Registration GitHub Action
        │
        ▼
Merge Marshal Coordinator
FastAPI + SQLite task store
        │
        ├── task status labels and transitions
        ├── change contracts
        ├── deterministic candidate matching
        ├── dependency graph
        ├── scheduler
        ├── GPT-5.6 classification
        └── GitHub workflow dispatch
        │
        ├───────────────┐
        ▼               ▼
Codex workers         GitHub-native status
GitHub Actions
        │
        ▼
Integration branch
        │
        ▼
Tests + final PR
```

### Why GitHub Actions?

GitHub Actions provides:

- Native access to the target repository.
- Exact commit checkout.
- Isolated worker environments.
- Existing test and build tooling.
- Workflow artifacts for patches and reports.
- Familiar logs for the demo.
- API-triggered planning and implementation jobs.

The coordinator makes scheduling decisions; GitHub Actions executes repository work.

The runner is the execution machine. Merge Marshal is the scheduler.

```text
Merge Marshal:
  decide what should run
  dispatch workflows
  store state
  validate worker results

GitHub runner:
  checkout the target repo
  run Codex
  run tests
  create patch artifacts
  call back to Merge Marshal
```

### Hackathon hosting model

Recommended MVP deployment:

```text
Merge Marshal FastAPI:
  local laptop process
  exposed through ngrok or Cloudflare Tunnel

Task store:
  local SQLite database

Workers:
  GitHub-hosted ubuntu-latest runners

Status surface:
  GitHub issue comments
  GitHub Actions logs
  workflow artifacts
  final integration pull request
```

`localhost` only works from inside the same machine. If `marshal-register.yml` runs on `ubuntu-latest`, then `http://localhost:8000` means the GitHub-hosted runner VM, not the developer laptop. Therefore the target repository should call the public tunnel URL stored in `MERGE_MARSHAL_URL`.

### Target repository workflow ownership

The target repository must contain the GitHub workflow files that Merge Marshal dispatches.

```text
target-repo/.github/workflows/
  marshal-register.yml
  marshal-plan.yml
  marshal-implement.yml
  marshal-apply.yml
```

These workflows cannot live only inside the Merge Marshal repository, because they need native access to the target repository checkout, test commands, branch permissions, Actions logs, and workflow artifacts.

Merge Marshal may ship these files as templates, but each target repository must install them. The onboarding model is:

```text
Install workflow bundle in target repo.
Set MERGE_MARSHAL_URL and callback token secrets.
Create issues.
Apply marshal:ready.
```

This means the MVP is not zero-configuration plug-and-play. It is closer to a CI tool that requires a small repository integration.

### Runner concurrency model

Merge Marshal does not create unlimited machines directly. It dispatches workflow runs, and GitHub schedules jobs onto available runners.

GitHub enforces account and plan-specific concurrency limits for hosted runners. The MVP should not depend on exact limits; it only needs three tasks. The coordinator should still expose an internal setting such as:

```env
MAX_PARALLEL_PLANNING_JOBS=3
MAX_PARALLEL_IMPLEMENTATION_JOBS=2
MAX_PARALLEL_APPLY_JOBS=1
```

For the MVP:

```text
Planning jobs:
  May run in parallel for all registered tasks.

Implementation jobs:
  May run in parallel for tasks with no unfinished dependencies.

Apply jobs:
  Should be serialized per coordination run.
```

Only one apply job should mutate `marshal/run-X` at a time. Otherwise two workers may race while pushing to the same integration branch.

Use a workflow concurrency key for apply jobs:

```yaml
concurrency:
  group: marshal-apply-${{ inputs.run_id }}
  cancel-in-progress: false
```

This is a backup guardrail. The coordinator should still dispatch apply jobs one at a time, because GitHub's concurrency control is not a general-purpose FIFO queue. This preserves parallel planning and implementation while keeping integration history deterministic.

### No frontend for the MVP

The MVP does not require a custom frontend.

The demo can be shown through GitHub-native surfaces:

- Issue comments showing registration, blocked status, replanning, and completion.
- GitHub Actions logs showing planning, implementation, tests, and apply jobs.
- Workflow artifacts containing contracts, patches, and structured reports.
- The final `marshal/run-X -> main` pull request.

A frontend or graph dashboard is useful later, but it is not required to prove the coordination loop.

## 5. Coordinator Internals

### Responsibility Boundaries

#### Codex: repository-grounded task specialist

Codex handles one task in repository context:

- Inspect relevant code.
- Locate files and symbols.
- Generate a structured plan.
- Implement approved tasks.
- Run tests.
- Inspect the resulting diff.

#### GPT-5.6: cross-task reasoning

GPT-5.6 receives compact structured contracts and determines:

- Whether two tasks are semantically related.
- Whether one invalidates another's assumption.
- Dependency direction.
- Scheduling recommendation.
- Replanning guidance.
- Human-readable conflict explanation.

#### Deterministic coordinator: authority and control

Ordinary application code owns:

- Task persistence.
- State transitions.
- Idempotency.
- Dependency graph mutation.
- Topological scheduling.
- Worker dispatch.
- Retry limits.
- Patch application.

Model output is schema-validated and advisory until accepted by deterministic coordinator logic.

```text
Codex understands each task inside the repository.
GPT-5.6 understands relationships between tasks.
Deterministic code controls execution.
```

---

### Coordinator State Store

SQLite is the coordinator's authoritative state store for the MVP.

It is not model memory. It stores task lifecycle, planning contracts, dependency edges, workflow runs, patch artifacts, and commit SHAs so the coordinator can make deterministic scheduling decisions.

When a planning worker returns a new change contract, the coordinator compares it against other active tasks in the same repository and coordination run.

Active statuses include:

```text
REGISTERED
PLANNING
ANALYSING
READY
RUNNING
BLOCKED
VERIFYING
REPLAN_REQUIRED
```

Completed or terminal tasks are normally excluded from active conflict scheduling:

```text
COMPLETED
FAILED
CANCELLED
SUPERSEDED
```

Simplified comparison flow:

```python
new_contract = get_latest_contract(new_task_id)

active_tasks = query_tasks(
    repository=new_task.repository,
    run_id=new_task.run_id,
    statuses=[
        "REGISTERED",
        "PLANNING",
        "ANALYSING",
        "READY",
        "RUNNING",
        "BLOCKED",
        "VERIFYING",
        "REPLAN_REQUIRED",
    ],
    exclude_task_id=new_task_id,
)

for task in active_tasks:
    other_contract = get_latest_contract(task.id)
    if other_contract is None:
        continue

    candidates = deterministic_match(new_contract, other_contract)
    decisions = gpt_classify(candidates)
    update_dependency_edges(decisions)
```

Tasks without a completed contract are still active, but they cannot be compared until their planning worker returns. The coordinator revisits comparisons as each contract arrives.

#### Minimum tables

For the MVP, the task store should contain these core tables.

```text
coordination_runs
tasks
change_contracts
dependency_edges
worker_runs
patch_artifacts
```

#### `coordination_runs`

Stores one active coordination run for the target repository.

```text
id
repository
base_branch
base_commit
integration_branch
status
created_at
updated_at
```

#### `tasks`

Stores issue-backed work items and their lifecycle state.

```text
id
run_id
repository
issue_number
title
body
status
planning_base_branch
planning_base_commit
execution_base_commit
result_commit
created_at
updated_at
```

#### `change_contracts`

Stores planned and verified task contracts.

```text
id
task_id
version
kind
summary
contract_json
created_at
```

`version` is required because blocked tasks may replan:

```text
Task B contract v1: planned against abc123
Task B contract v2: replanned against def456
```

#### `dependency_edges`

Stores why one task blocks or constrains another.

```text
id
run_id
from_task_id
to_task_id
type
decision
severity
confidence
reason
status
created_at
```

For `A blocks B`:

```text
from_task_id = A
to_task_id = B
decision = replan_after
```

#### `worker_runs`

Links task state to GitHub Actions executions.

```text
id
task_id
run_id
kind
github_run_id
status
started_at
completed_at
result_json
```

`kind` may be:

```text
planning
implementation
apply
verify
```

#### `patch_artifacts`

Stores implementation outputs before they are applied.

```text
id
task_id
worker_run_id
artifact_url
patch_sha256
changed_files_json
test_result_json
validation_status
created_at
```

The scheduler uses this data to answer:

```text
Which tasks are active?
What does each task consume, change, or produce?
Who blocks whom?
Which tasks have no unresolved blockers?
Which workflow jobs are already dispatched?
What commit should the next worker use?
```

---

### Change Contracts

A change contract is a structured prediction of what a task will consume, change, remove, or produce.

It is generated before implementation.

```json
{
  "task_id": "TASK-B",
  "contract_version": 1,
  "summary": "Add caching to the user response endpoint",
  "resources": [
    {
      "resource_id": "python:symbol:src/schemas/user.py::UserResponse.user_id",
      "kind": "schema_field",
      "operation": "consume",
      "assumptions": {
        "exists": true,
        "nullable": false,
        "type": "int"
      },
      "evidence": [
        {
          "path": "src/services/user_cache.py",
          "planned_usage": "Construct cache key"
        }
      ],
      "confidence": 0.95
    },
    {
      "resource_id": "cache:key:user:{identity}",
      "kind": "cache_contract",
      "operation": "produce",
      "after": {
        "format": "user:{user_id}"
      },
      "confidence": 0.91
    }
  ],
  "files_expected_to_change": [
    "src/services/user_cache.py",
    "src/api/users.py"
  ],
  "tests_required": [
    "Cache hit avoids database query",
    "Cache miss stores response",
    "User update invalidates cache"
  ]
}
```

#### Canonical resource IDs

Natural-language names are too inconsistent for reliable comparison.

Use identifiers such as:

```text
python:symbol:src/schemas/user.py::UserResponse.user_id
python:symbol:src/api/users.py::get_user
database:column:users.status
http:route:GET:/users/{id}
cache:key:user:{identity}
env:REDIS_URL
```

---

### Conflict Detection

Conflict detection uses two stages.

#### Stage 1: deterministic candidate matching

```python
changed = task_a.changed_resource_ids
required = task_b.required_resource_ids

candidate_conflicts = changed & required
```

Candidate signals include:

- A task removes a resource another consumes.
- Two tasks modify the same symbol.
- A task changes nullability another assumes.
- A task changes an API shape another calls.
- A task changes a cache-key format another invalidates.
- A task renames a database column another queries.

#### Stage 2: GPT-5.6 classification

```json
{
  "left_task": "TASK-A",
  "right_task": "TASK-B",
  "conflict_detected": true,
  "conflict_type": "producer_consumer",
  "severity": "high",
  "decision": "replan_after",
  "run_first": "TASK-A",
  "reason": "TASK-A removes UserResponse.user_id, which TASK-B requires for cache-key construction",
  "confidence": 0.96
}
```

The MVP should hard-block only high-confidence conflicts.

Ambiguous decisions become:

```text
WAITING_FOR_HUMAN
```

---

### Dependency Graph and Scheduling

Merge Marshal builds a directed graph:

```text
Task A ─────────▶ Task B ─────────▶ Task D
   │
   └────────────▶ Task E

Task C
```

Execution occurs in topological batches:

```text
Batch 1: Task A, Task C
Batch 2: Task B, Task E
Batch 3: Task D
```

Simplified scheduler:

```python
while unfinished_tasks:
    ready = find_tasks_with_no_unfinished_dependencies()

    if not ready:
        raise DependencyCycleError()

    results = run_in_parallel(ready)
    verify_and_apply(results)
    reanalyse_blocked_tasks()
```

Cycles require human review rather than model guessing.

---

### Task Status Labels and Transitions

Allowed sequential flow:
```text
REGISTERED
    ↓
PLANNING
    ↓
ANALYSING
    ├── BLOCKED
    ├── WAITING_FOR_HUMAN
    └── READY
          ↓
       RUNNING
          ↓
       VERIFYING
          ├── REPLAN_REQUIRED
          ├── FAILED
          └── COMPLETED
```

Terminal states may include:

```text
FAILED
CANCELLED
SUPERSEDED
```

---

## 6. Patch and Execution Model

### Branch and Patch Model

Each implementation worker produces a patch artifact rather than pushing directly.

```text
Worker checks out exact execution commit
        ↓
Codex modifies isolated workspace
        ↓
Worker runs task-level tests
        ↓
Worker uploads patch + structured report
        ↓
Coordinator receives patch and validates report
        ↓
If validation passes, patch is applied to marshal/run-X
```

This keeps the worker isolated and produces one authoritative integration history.

#### Implement vs apply

Implementation and application are separate steps.

```text
Implement:
  Codex edits code in an isolated runner workspace.
  The worker runs task-level tests.
  The worker produces patch.diff and result.json.
  The change is proposed, but not yet authoritative.

Apply:
  Merge Marshal accepts a verified patch.
  An apply workflow applies it to marshal/run-X.
  The apply workflow commits and pushes the integration branch.
  The change becomes persistent Git history.
```

This separation lets Merge Marshal remain the authority over what enters the shared branch.

For a dependency chain (i.e. `A -> B`):

```text
Implement A
Verify A
Apply A to marshal/run-X
Replan B against latest commit of marshal/run-X
Implement B
Verify B
Apply B
Run final integration tests
Open final pull request
```

Apply can happen after each verified task completes. It is not only a final action after every implementation worker has finished.

Each task stores:

```json
{
  "planning_base_commit": "abc123",
  "execution_base_commit": "def456",
  "result_commit": "ghi789"
}
```

- `planning_base_commit`: inspected during initial planning.
- `execution_base_commit`: used when implementation actually starts.
- `result_commit`: integration-branch commit after applying the verified patch.

---

## 7. Demo and MVP Scope

### Demo Scenario

#### Tasks

##### Task A

```text
Rename UserResponse.user_id to UserResponse.actor_id.
```

##### Task B

```text
Add caching for user responses using the canonical identity field.
```

##### Task C

```text
Add structured logging to payment endpoints.
```

#### Without Merge Marshal

```text
A, B, and C start from the same commit.
A renames user_id.
B implements caching using user_id.
A and B pass isolated tests.
Their patches are combined.
Integration fails or stale behaviour remains.
```

#### With Merge Marshal

```text
A, B, and C are planned first.
A is found to invalidate B's dependency.
A and C run in parallel.
B waits.
A completes and is verified.
B replans against A's result.
B implements using actor_id.
Integration tests pass.
```

#### Final demo metrics

```text
Tasks submitted: 3
Tasks completed: 3
Tasks executed in parallel: 2
Tasks blocked: 1
Tasks replanned: 1
Semantic conflicts prevented: 1
Human interventions: 0
Integration tests passed: 48
```

These are demo outputs, not general production-reliability claims.

---

### Hackathon MVP Scope

#### Must build

- One target demo repository.
- Three curated GitHub issues.
- `marshal:ready` invocation.
- Issue-label registration workflow.
- Read-only Codex planning.
- JSON-schema change contracts.
- Canonical resource IDs.
- Deterministic candidate matching.
- GPT-5.6 conflict classification.
- Dependency graph.
- Parallel execution of independent tasks.
- Blocking and replanning of one dependent task.
- Patch artifacts.
- Coordination-run integration branch.
- Integration tests.
- One final pull request.
- GitHub issue comments, Actions logs, and artifacts as the status surface.
- Side-by-side without/with Merge Marshal demo.

#### Simplify or mock

- One repository.
- One coordination run at a time.
- Maximum three tasks.
- One high-confidence producer-consumer conflict type.
- Curated issue descriptions.
- Single-user operation.
- SQLite or another simple task store.

#### Explicitly defer

- Multi-repository coordination.
- Multi-tenant authentication.
- Local Codex or Claude Code wrapper.
- Arbitrary local-agent interception.
- Live in-flight agent interruption.
- Stacked pull requests.
- Automatic production merging.
- Agent memory as authoritative state.
- Historical conflict learning.
- Telegram notifications.
- Custom frontend or graph dashboard.

---

### Known Limitation: Merge Marshal Must Own Execution

Merge Marshal cannot coordinate an arbitrary coding-agent process launched privately on a developer's laptop.

If a developer directly runs:

```bash
codex "Add Redis caching"
```

Merge Marshal has no knowledge of that task unless a future integration captures it.

For the MVP, the enforced workflow is:

```text
Do not launch the coding agent manually.
Create GitHub issue.
Apply marshal:ready.
Merge Marshal plans and launches the agent.
```

Possible future entry points include:

- A local `marshal codex` CLI wrapper.
- An IDE extension.
- A Codex hook.
- A local daemon.
- A shared engineering-task API.

---

## 8. Security Model

Use a simple rule:

```text
Codex can propose a patch.
Only the apply job can push code.
```

Do not give the same workflow job both an OpenAI credential and GitHub write permission.

### Implementation worker

```text
Repository: exact commit checkout
Local workspace writes: allowed
GitHub write permission: none
OpenAI credential: available
Output: patch and structured report
```

### Apply job

```text
Repository write permission: available
OpenAI credential: unavailable
Input: validated patch artifact
Output: integration-branch commit
```

This limits damage if repository code, issue text, or generated output contains bad instructions. Codex can create a proposed patch, but it cannot directly push to the repository.

Minimum controls:

- Validate model outputs against JSON Schema.
- Use exact commit SHAs.
- Reject unexpected patch paths.
- Restrict workflow permissions.
- Require human approval for sensitive change categories in future versions.

---

## 9. Repository Layout and Build Order

### Suggested Repository Layout

Two repositories make the story clearest.

#### Product repository

```text
merge-marshal/
├── README.md
├── pyproject.toml
├── .env.example
├── docker-compose.yml
│
├── coordinator/
│   ├── main.py
│   ├── api/
│   │   ├── tasks.py
│   │   ├── callbacks.py
│   │   ├── runs.py
│   │   └── health.py
│   ├── models/
│   │   ├── task.py
│   │   ├── run.py
│   │   ├── contract.py
│   │   ├── conflict.py
│   │   ├── patch.py
│   │   └── worker_result.py
│   ├── services/
│   │   ├── task_service.py
│   │   ├── scheduler.py
│   │   ├── conflict_detector.py
│   │   ├── gpt_classifier.py
│   │   ├── github_client.py
│   │   ├── workflow_dispatcher.py
│   │   ├── patch_validator.py
│   │   └── callback_auth.py
│   ├── db/
│   │   ├── session.py
│   │   ├── schema.py
│   │   └── migrations/
│   └── settings.py
│
├── schemas/
│   ├── change_contract.schema.json
│   ├── conflict_decision.schema.json
│   ├── implementation_result.schema.json
│   └── apply_result.schema.json
│
├── prompts/
│   ├── plan_task.md
│   ├── implement_task.md
│   ├── verify_patch.md
│   └── classify_conflict.md
│
├── worker/
│   ├── callback.py
│   ├── make_patch.sh
│   ├── validate_contract.py
│   └── validate_result.py
│
├── templates/
│   └── github-workflows/
│       ├── marshal-register.yml
│       ├── marshal-plan.yml
│       ├── marshal-implement.yml
│       └── marshal-apply.yml
│
├── tests/
│   ├── unit/
│   │   ├── test_scheduler.py
│   │   ├── test_conflict_detector.py
│   │   └── test_state_machine.py
│   └── fixtures/
│       ├── contracts/
│       └── callbacks/
│
└── scripts/
    ├── dev_server.ps1
    ├── seed_demo_run.py
    └── install_workflows.py
```

The core product is `coordinator/`. It owns the FastAPI app, task state, GitHub workflow dispatch, deterministic scheduling, and GPT-5.6 conflict classification.

`templates/github-workflows/` contains workflow templates that are copied into the target repository. They are not active from the Merge Marshal repository by themselves.

`worker/` contains small helper scripts that target-repository workflows can call to validate JSON, make patch artifacts, and post callbacks.

The MVP intentionally omits a frontend. GitHub issue comments, workflow logs, artifacts, and the final pull request are enough for the demo.

#### Target demo repository

```text
merge-marshal-demo/
├── .github/
│   └── workflows/
│       ├── marshal-register.yml
│       ├── marshal-plan.yml
│       ├── marshal-implement.yml
│       └── marshal-apply.yml
├── src/
├── tests/
└── demo-tasks/
```

For maximum implementation speed, these can initially be combined into one monorepo and separated later.

---

### Recommended Build Order

#### Phase 1: prove the scheduler without models

1. Create the demo repository.
2. Create the failing combined-task scenario.
3. Define task and contract data models.
4. Hard-code three contracts.
5. Implement candidate matching.
6. Build the dependency graph.
7. Implement topological scheduling.
8. Simulate blocking, completion, and replanning.

#### Phase 2: add repository-grounded planning

1. Add the read-only Codex workflow.
2. Enforce JSON-schema output.
3. Replace hard-coded contracts.
4. Add canonical resource IDs and evidence.

#### Phase 3: add cross-task reasoning

1. Add GPT-5.6 classification.
2. Keep deterministic filtering before the model call.
3. Add confidence thresholds.
4. Add `WAITING_FOR_HUMAN` handling.

#### Phase 4: execute code changes

1. Add Codex implementation workflow.
2. Generate patch artifacts.
3. Run task-level tests.
4. Validate patches.
5. Apply patches to the integration branch.
6. Replan blocked tasks.
7. Run final integration tests.

#### Phase 5: complete the product surface

1. Add issue-label registration.
2. Add GitHub comments.
3. Add workflow artifact links and concise status comments.
4. Open the final PR.
5. Record the demo through GitHub Issues, Actions, artifacts, and the pull request.

---

## 10. Success Criteria and Final Mental Model

### Success Criteria

The MVP succeeds when it visibly demonstrates:

```text
Three issues are delegated.
        ↓
All are planned before implementation.
        ↓
Task A invalidates Task B's assumption.
        ↓
Task A and independent Task C run concurrently.
        ↓
Task B remains blocked.
        ↓
Task A completes and is verified.
        ↓
Task B replans against the new code.
        ↓
All patches integrate successfully.
        ↓
One tested pull request is opened.
```

---

### Final Mental Model

Modern coding agents are increasingly able to turn a task or issue into an implementation and pull request.

Merge Marshal does not need to reinvent that execution loop.

It inserts the missing coordination layer before multiple issue-driven agents are allowed to run independently.

```text
Developers define engineering intent as issues
                    ↓
Merge Marshal plans incoming tasks
                    ↓
Merge Marshal compares them against active task contracts
                    ↓
Merge Marshal builds a dependency graph
                    ↓
Independent coding agents run concurrently
                    ↓
Dependent coding agents wait
                    ↓
Verified upstream changes update downstream context
                    ↓
Blocked agents replan against current code
                    ↓
Patches are integrated and tested
                    ↓
A final pull request is opened
```

> **Merge Marshal provides cross-task concurrency control for coding agents.**

---

## 11. References

- [GitHub Docs: Using Copilot coding agent on GitHub](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github)
- [GitHub Docs: About third-party coding agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents)
- [GitHub Docs: Events that trigger workflows](https://docs.github.com/actions/using-workflows/events-that-trigger-workflows)
- [OpenAI Developers: Codex GitHub Action](https://developers.openai.com/codex/github-action)
- [OpenAI Cookbook: Automate Jira to GitHub with Codex](https://developers.openai.com/cookbook/examples/codex/jira-github)
