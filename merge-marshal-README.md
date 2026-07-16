# Merge Marshal

> **Merge Marshal provides cross-task concurrency control for coding agents.**

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

## Core Thesis

Git prevents textual collisions after code is written.

Merge Marshal prevents high-confidence semantic collisions before coding agents begin implementation.

Two branches can:

- Modify different files.
- Produce no Git merge conflict.
- Pass their isolated tests.
- Still become incompatible when combined.

Merge Marshal addresses this by extracting structured plans from all active tasks, identifying cross-task contract dependencies, and controlling execution order.

---

## The Problem

Assume two issues are delegated from the same commit.

### Task A

Rename:

```text
UserResponse.user_id
```

to:

```text
UserResponse.actor_id
```

### Task B

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

## What Merge Marshal Adds

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

## Product Positioning

### One-line description

> Merge Marshal is an orchestration layer between engineering tasks and coding-agent execution that coordinates concurrent tasks before they become incompatible pull requests.

### Short analogy

> Air-traffic control for coding agents working on the same codebase.

### Precise USP

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

## What Merge Marshal Is Not

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

# User Workflow

## 1. Developer creates a GitHub issue

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

## 2. Developer applies `marshal:ready`

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

## 3. GitHub Action registers the task

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
            '{
              repository: $repository,
              issue_number: $issue_number,
              title: $title,
              body: $body
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
- Acceptance criteria.
- Current default-branch commit.
- GitHub workflow metadata.

It does not send a completed code diff because implementation has not started.

## 4. Merge Marshal captures an exact planning commit

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

## 5. Merge Marshal dispatches read-only planning

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

## 6. Merge Marshal compares all active plans

Assume three tasks are registered:

```text
A: Rename user_id to actor_id
B: Add caching using user identity
C: Add payment logging
```

The plans indicate:

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

## 7. Merge Marshal dispatches only ready tasks

```text
Coordinator
   ├── Run Task A
   ├── Run Task C
   └── Do not run Task B yet
```

Task A and Task C execute concurrently.

Task B remains blocked.

## 8. Completed patches return for verification

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

## 9. Blocked tasks replan against verified upstream changes

After Task A is applied to the integration branch:

```text
Task B planning base: abc123
Task B execution base: def456
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

## 10. Merge Marshal opens one integration PR

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

# Real-Time Semantics

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

# System Architecture

The hackathon implementation uses a deliberately lightweight architecture.

```text
Target GitHub repository
        │
        │ issue labeled marshal:ready
        ▼
Registration GitHub Action
        │
        ▼
Merge Marshal Coordinator
FastAPI + task store
        │
        ├── task state machine
        ├── change contracts
        ├── deterministic candidate matching
        ├── dependency graph
        ├── scheduler
        ├── GPT-5.6 classification
        └── GitHub workflow dispatch
        │
        ├───────────────┐
        ▼               ▼
Codex workers         Task graph UI
GitHub Actions
        │
        ▼
Integration branch
        │
        ▼
Tests + final PR
```

## Why GitHub Actions?

GitHub Actions provides:

- Native access to the target repository.
- Exact commit checkout.
- Isolated worker environments.
- Existing test and build tooling.
- Workflow artifacts for patches and reports.
- Familiar logs for the demo.
- API-triggered planning and implementation jobs.

The coordinator makes scheduling decisions; GitHub Actions executes repository work.

## Why not a large AWS architecture?

The product thesis is cross-task agent coordination, not infrastructure provisioning.

For the hackathon, avoid making these mandatory:

- AgentCore.
- SQS.
- DynamoDB.
- CodeBuild.
- ECR.
- Step Functions.
- Kubernetes.

They may be used when already convenient, but they are not necessary to prove the core interaction.

A FastAPI service with SQLite or PostgreSQL is sufficient.

---

# Responsibility Boundaries

## Codex: repository-grounded task specialist

Codex handles one task in repository context:

- Inspect relevant code.
- Locate files and symbols.
- Generate a structured plan.
- Implement approved tasks.
- Run tests.
- Inspect the resulting diff.

## GPT-5.6: cross-task reasoning

GPT-5.6 receives compact structured contracts and determines:

- Whether two tasks are semantically related.
- Whether one invalidates another's assumption.
- Dependency direction.
- Scheduling recommendation.
- Replanning guidance.
- Human-readable conflict explanation.

## Deterministic coordinator: authority and control

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

# Change Contracts

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

## Canonical resource IDs

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

# Conflict Detection

Conflict detection uses two stages.

## Stage 1: deterministic candidate matching

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

## Stage 2: GPT-5.6 classification

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

# Dependency Graph and Scheduling

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

# Task State Machine

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

# Branch and Patch Model

Each worker produces a patch artifact rather than pushing directly.

```text
Worker checks out exact integration commit
        ↓
Codex modifies isolated workspace
        ↓
Worker runs task-level tests
        ↓
Worker uploads patch + report
        ↓
Coordinator validates result
        ↓
Patch is applied to marshal/run-X
```

This keeps the worker isolated and produces one authoritative integration history.

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

# Demo Scenario

## Tasks

### Task A

```text
Rename UserResponse.user_id to UserResponse.actor_id.
```

### Task B

```text
Add caching for user responses using the canonical identity field.
```

### Task C

```text
Add structured logging to payment endpoints.
```

## Without Merge Marshal

```text
A, B, and C start from the same commit.
A renames user_id.
B implements caching using user_id.
A and B pass isolated tests.
Their patches are combined.
Integration fails or stale behaviour remains.
```

## With Merge Marshal

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

## Final demo metrics

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

# Hackathon MVP Scope

## Must build

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
- Minimal graph/status UI.
- Side-by-side without/with Merge Marshal demo.

## Simplify or mock

- One repository.
- One coordination run at a time.
- Maximum three tasks.
- One high-confidence producer-consumer conflict type.
- Curated issue descriptions.
- Single-user operation.
- SQLite or another simple task store.

## Explicitly defer

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
- Kubernetes and large distributed infrastructure.

---

# Known Limitation: Merge Marshal Must Own Execution

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

# Security Model

Repository code, issue content, prompts, and generated commands are untrusted.

Separate the worker that has model credentials from the job that has repository write access.

## Codex worker

```text
Repository: read-only checkout
GitHub write permission: none
OpenAI credential: available
Output: patch and structured report
```

## Patch application job

```text
Repository write permission: available
OpenAI credential: unavailable
Input: validated patch artifact
Output: integration-branch commit
```

Additional controls:

- Validate model outputs against JSON Schema.
- Use exact commit SHAs.
- Reject unexpected patch paths.
- Restrict workflow permissions.
- Do not directly execute arbitrary shell commands returned by a model.
- Require human approval for sensitive change categories in future versions.

---

# Suggested Repository Layout

Two repositories make the story clearest.

## Product repository

```text
merge-marshal/
├── README.md
├── coordinator/
│   ├── app.py
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── repositories/
│   └── database/
├── frontend/
│   ├── app/
│   └── components/
├── prompts/
├── schemas/
└── tests/
```

## Target demo repository

```text
merge-marshal-demo/
├── .github/
│   └── workflows/
│       ├── marshal-register.yml
│       ├── marshal-plan.yml
│       ├── marshal-implement.yml
│       ├── marshal-apply.yml
│       └── marshal-integrate.yml
├── src/
├── tests/
└── demo-tasks/
```

For maximum implementation speed, these can initially be combined into one monorepo and separated later.

---

# Recommended Build Order

## Phase 1: prove the scheduler without models

1. Create the demo repository.
2. Create the failing combined-task scenario.
3. Define task and contract data models.
4. Hard-code three contracts.
5. Implement candidate matching.
6. Build the dependency graph.
7. Implement topological scheduling.
8. Simulate blocking, completion, and replanning.

## Phase 2: add repository-grounded planning

1. Add the read-only Codex workflow.
2. Enforce JSON-schema output.
3. Replace hard-coded contracts.
4. Add canonical resource IDs and evidence.

## Phase 3: add cross-task reasoning

1. Add GPT-5.6 classification.
2. Keep deterministic filtering before the model call.
3. Add confidence thresholds.
4. Add `WAITING_FOR_HUMAN` handling.

## Phase 4: execute code changes

1. Add Codex implementation workflow.
2. Generate patch artifacts.
3. Run task-level tests.
4. Validate patches.
5. Apply patches to the integration branch.
6. Replan blocked tasks.
7. Run final integration tests.

## Phase 5: complete the product surface

1. Add issue-label registration.
2. Add GitHub comments.
3. Add minimal task graph UI.
4. Open the final PR.
5. Record the demo.

---

# Success Criteria

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

# Final Mental Model

Modern coding agents are increasingly able to turn a task or issue into an implementation and pull request.

Merge Marshal does not need to reinvent that execution loop.

It inserts the missing coordination layer before multiple issue-driven agents are allowed to run independently.

```text
Developers define engineering intent as issues
                    ↓
Merge Marshal plans all active tasks
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

# References

- [GitHub Docs: Using Copilot coding agent on GitHub](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github)
- [GitHub Docs: About third-party coding agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents)
- [GitHub Docs: Events that trigger workflows](https://docs.github.com/actions/using-workflows/events-that-trigger-workflows)
- [OpenAI Developers: Codex GitHub Action](https://developers.openai.com/codex/github-action)
- [OpenAI Cookbook: Automate Jira to GitHub with Codex](https://developers.openai.com/cookbook/examples/codex/jira-github)
