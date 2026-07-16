# Graph-Native Change Planning for Coding Agents

## Working Concept

A visual change-planning and supervision layer for coding agents.

Developers select the parts of a backend related to a feature, the system identifies the likely blast radius, the developer approves a bounded change plan, and the resulting implementation is checked against that plan.

## Problem

When developers work in unfamiliar or poorly documented backends, it is difficult to determine:

- which components are involved in a feature;
- what dependencies may also need to change;
- whether a coding agent has understood the intended scope;
- whether the final implementation changed more or less than expected.

Existing coding agents mainly operate through text prompts, file context, and diffs. Their assumptions about change scope are often difficult to inspect before implementation begins.

Architecture diagrams can help, but they are usually created manually, become outdated, and are disconnected from the actual development workflow.

## Target User

A backend developer making a feature change in an unfamiliar or poorly documented codebase.

## Core Job

Help the developer understand, approve, execute, and review the scope of a backend feature change.

## Product Thesis

Code changes affect interconnected system components, but coding agents are usually instructed through unstructured text.

A persistent, editable system map can act as a shared change contract between the developer and the coding agent.

## Proposed Workflow

1. Import a backend repository.
2. Generate a focused map of its main components and relationships.
3. Select the components related to a feature.
4. Describe the intended change.
5. Let the planning agent identify additional affected components.
6. Review and approve the proposed scope, constraints, and acceptance criteria.
7. Send the approved plan to a coding agent for implementation.
8. Compare the planned scope against the actual code changes.
9. Highlight completed, missing, and unexplained out-of-scope changes.

## Core Product Object

The central object is a structured **change manifest**, containing:

- feature intent;
- user-selected components;
- suggested additional components;
- reasons for scope expansion;
- approved scope;
- constraints;
- acceptance criteria;
- planned work;
- actual implementation changes.

The graph is the interface used to create, inspect, and review this manifest.

## Main Differentiator

The product does not stop at visualizing a codebase.

The same system map is used across the full change lifecycle:

> Understand → Scope → Approve → Execute → Verify

This makes the agent's interpretation of the feature visible and editable before code is changed, then provides a clear way to check whether the implementation followed the approved plan.

## Build Week MVP

The MVP should demonstrate one complete backend feature-change workflow:

- one repository;
- one supported backend stack;
- one focused system map;
- visual component selection;
- agent-assisted scope expansion;
- human approval of the change plan;
- implementation by a coding agent;
- planned-versus-actual change visualization.

## Example Demo

A developer wants to add cumulative partial refunds to an unfamiliar payments backend.

The developer selects the refund endpoint and payment service.

The system suggests additional affected components, such as:

- request and response schemas;
- refund persistence model;
- payment provider integration;
- event payloads;
- tests.

The developer reviews and approves the final scope.

A coding agent implements the feature.

The final graph shows:

- components that were planned and changed;
- components that were planned but not changed;
- components changed outside the approved scope;
- newly introduced components or relationships;
- relevant test results.

## Explicit Non-Goals for the MVP

The MVP will not attempt to provide:

- universal programming-language support;
- perfect reconstruction of software architecture;
- cross-repository microservice mapping;
- production runtime tracing;
- autonomous deployment;
- automatic merging;
- guaranteed prevention of semantic conflicts;
- a full multi-agent project-management platform.

## Product Risks to Validate

The project must validate whether:

1. the generated system map is accurate enough to support planning;
2. the visualization remains understandable rather than becoming graph clutter;
3. proposed and actual code changes can be mapped back to meaningful components;
4. the structured visual workflow provides more value than a normal text-based coding-agent conversation.

## Current Product Positioning

> Select a feature's scope visually, let the planning agent identify the missing blast radius, approve the plan, and verify that the coding agent changed what was intended.

## Open Questions

The following areas still need to be firmed up:

- the exact component types shown in the graph;
- the abstraction level of the default view;
- how the system distinguishes verified relationships from inferred ones;
- how much scope expansion the planning agent may propose;
- how developers edit and approve the change manifest;
- how deviations are presented after implementation;
- whether multi-agent coordination belongs in the MVP or a later version.
