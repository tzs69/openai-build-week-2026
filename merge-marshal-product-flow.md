# Merge Marshal Product Flow

## Goal

Merge Marshal helps multiple coding agents plan and implement changes against the same repository without silently colliding. It uses a codebase architecture graph as shared context, then visualizes each agent's planned blast radius before code is written.

## Core Artifacts

```text
.graph/
  graph.json          canonical architecture source of truth
  graph_reverse.json  artifact -> node/edge lookup index
  architecture.mmd    generated Mermaid view
```

`graph.json` represents the current verified codebase. It is only updated after code changes are implemented, validated, and persisted.

## End-To-End Flow

1. **Initial Graph Generation**

   The `generate_graph` skill inspects the repository and writes `.graph/graph.json`, `.graph/graph_reverse.json`, and `.graph/architecture.mmd`.

2. **Frontend Loads Architecture**

   The frontend renders the architecture graph from `.graph/graph.json`. `architecture.mmd` can be used as a generated human-readable view, but `graph.json` remains canonical.

3. **User Submits Request**

   The user enters an implementation request through the chat UI, such as adding a feature, changing behavior, or restructuring part of the codebase.

4. **Orchestrator Receives Request**

   A backend FastAPI app sends the request to the orchestrator agent. The orchestrator owns task decomposition and agent coordination.

5. **Task Decomposition**

   If the request is complex, the orchestrator splits it into subtasks.

6. **Planner Workers Produce Change Contracts**

   Each Codex planner worker receives:

   ```text
   assigned subtask
   current graph.json
   graph_reverse.json
   relevant repository context
   ```

   Each worker returns a structured change contract describing:

   ```text
   affected nodes
   affected edges
   affected artifacts/files
   proposed graph changes, if any
   risk notes
   ```

7. **Frontend Shows Planned Blast Radius**

   Each agent is assigned a color. The frontend highlights the nodes and edges from each agent's change contract using that color.

   These highlights are overlays only. They do not mutate `graph.json`.

8. **Conflict Detection**

   The backend compares change contracts.

   Basic conflict levels:

   ```text
   hard conflict    same file/artifact
   medium conflict  same graph node
   soft conflict    adjacent or connected graph nodes
   graph conflict   one plan changes/removes a node or edge another plan depends on
   ```

9. **Deconflicting / Replanning**

   If conflicts exist, the orchestrator keeps one plan and asks the conflicting worker to replan with constraints.

   Example:

   ```text
   Agent A owns component.auth and src/auth/service.py.
   Agent B must replan to avoid those files/nodes if possible.
   ```

   The frontend updates overlays as revised change contracts arrive.

10. **Implementation Begins**

   After all plans are sufficiently deconflicted, implementation workers start writing code.

   Each worker operates in an isolated git worktree or branch. Workers do not write directly into the same checkout.

11. **Validation And Persistence**

   The orchestrator validates each worker's changes, then applies or merges accepted changes in a controlled sequence.

   Persistence to git happens only after validation succeeds.

12. **Graph Refresh**

   After code is persisted, the backend runs graph generation again.

   The old graph is compared with the new graph to detect:

   ```text
   added nodes
   removed nodes
   updated nodes
   added edges
   removed edges
   updated edges
   artifact remaps
   ```

13. **Frontend Updates Final State**

   Temporary agent overlays are removed after their changes are applied.

   The frontend renders the refreshed architecture graph from the new `graph.json`.

## Important Design Rule

Planned work is represented as colored overlays from change contracts.

Committed architecture is represented by `graph.json`.

Do not update `graph.json` for plans. Update it only after implementation, validation, and persistence.
