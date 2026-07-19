# ChatGPT project context

This directory is a local mirror of the ChatGPT project “openai_build_week”.

- Treat every file under `sources/` as read-only reference material.
- Do not edit, rename, move, or delete synced project files.
- These files may be replaced the next time a task is created from this ChatGPT project.

## Project instructions

Keep responses direct and concise.

Offer alternative viewpoints and methods when building; do not get tunnel vision.

Treat the user as someone who may not know what they do not know and would value relevant introductions to both established and newer ideas.

## Hackathon context

This project explores an interactive visual model of a codebase and the work performed by coding agents. The aim is to help a person understand both the current system and how an agent's plan is expected to change it.

The experience should make planned additions, removals, modifications, dependencies, and the wider range of possible impact understandable before and during execution. It should also distinguish direct changes from downstream or uncertain effects and preserve the reasoning or evidence behind them.

The diagram should support richer, dynamic interaction than a static architecture document. Rendering, visual language, impact calculation, and application technology remain intentionally undecided; do not lock them in without discussing trade-offs.

## Hierarchical graph direction

- `.graph/graph.json` is the single canonical architecture artifact.
- Nodes use globally unique IDs and `parent_id` to preserve meaningful component nesting; edges remain global.
- Nodes contain visual identity plus executor scope (`artifacts`, symbols, and `primary`/`shared` ownership). Edges contain visual relationships plus code evidence.
- Cohesive modules are the default lowest level. Promote classes only when architecturally significant; keep ordinary classes and functions as symbol metadata.
- Preserve the full hierarchy in the artifact. UI/backend consumers should derive depth-limited projections, initially one or two levels, and aggregate hidden edges.
- Do not persist `graph_reverse.json`, Mermaid, warnings, layout state, or other derivable views.

## Implemented graph toolkit

- `hierarchical-graph/` owns the installable `hgraph` CLI, storage, validation, projection, JSON Schema, fixtures, and tests.
- `.agents/skills/generate_hierarchical_graph/` contains only the LLM analysis workflow and CLI usage guidance, following the OMM separation between deterministic tooling and agent instructions.
- `hgraph` supports initialization, node/edge upserts and deletion, hierarchy inspection, validation, and read-only depth projection.
- The original `.agents/skills/generate_graph/` remains unchanged; use the hierarchical skill for this direction.
