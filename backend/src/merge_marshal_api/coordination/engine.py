from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

from .models import (
    ChangeContract,
    Conflict,
    ConflictSeverity,
    Dependency,
    DiagramImpact,
    ExecutionBatch,
    ImpactClassification,
    ImpactEvidence,
    ResourceInteraction,
    Task,
    TaskStatus,
)


class InvalidContractError(ValueError):
    """A contract is structurally valid but invalid for this repository graph."""


class DependencyCycleError(ValueError):
    """The derived task dependency graph contains a cycle."""


def _nodes_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in graph["nodes"]}


def validate_contracts(
    contracts: Iterable[ChangeContract], graph: dict[str, Any], repository: Path
) -> None:
    nodes_by_id = _nodes_by_id(graph)
    canonical_ids = set(nodes_by_id)
    effect_ids: set[str] = set()
    proposed_ids: set[str] = set()
    task_versions: set[tuple[str, int]] = set()

    for contract in contracts:
        version_key = (contract.task_id, contract.version)
        if version_key in task_versions:
            raise InvalidContractError(
                f"duplicate contract version {contract.version} for {contract.task_id}"
            )
        task_versions.add(version_key)

        for claim in contract.diagram_impact_claims:
            if claim.node_id not in canonical_ids:
                raise InvalidContractError(
                    f"contract {contract.task_id} claims unknown node {claim.node_id}"
                )

        for effect in contract.effects:
            if effect.effect_id in effect_ids:
                raise InvalidContractError(f"duplicate effect ID {effect.effect_id}")
            effect_ids.add(effect.effect_id)

            target_node = effect.target.node_id
            if target_node is not None and target_node not in canonical_ids:
                raise InvalidContractError(
                    f"effect {effect.effect_id} targets unknown node {target_node}"
                )

            if effect.target.path and effect.interaction != ResourceInteraction.PRODUCE:
                target_path = repository / effect.target.path
                if not target_path.exists():
                    raise InvalidContractError(
                        f"effect {effect.effect_id} targets missing path {effect.target.path}"
                    )

            change = effect.architecture_change
            if change is None:
                continue
            proposal = change.node or change.edge
            if proposal is None:
                continue
            if proposal.id in canonical_ids or proposal.id in proposed_ids:
                raise InvalidContractError(
                    f"proposed graph ID {proposal.id} is not unique"
                )
            proposed_ids.add(proposal.id)
            if change.node and change.node.parent_id not in canonical_ids:
                raise InvalidContractError(
                    f"proposed node {change.node.id} has unknown parent "
                    f"{change.node.parent_id}"
                )

    known_endpoints = canonical_ids | proposed_ids
    for contract in contracts:
        for effect in contract.effects:
            change = effect.architecture_change
            if change is None or change.edge is None:
                continue
            edge = change.edge
            if edge.source not in known_endpoints or edge.target not in known_endpoints:
                raise InvalidContractError(
                    f"proposed edge {edge.id} references an unknown endpoint"
                )


def _effects_by_resource(
    contracts: Iterable[ChangeContract],
) -> dict[str, list[tuple[str, Any]]]:
    grouped: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for contract in contracts:
        for effect in contract.effects:
            grouped[effect.resource_id].append((contract.task_id, effect))
    return grouped


def _task_pair(first: str, second: str) -> tuple[str, str]:
    return tuple(sorted((first, second)))  # type: ignore[return-value]


def detect_conflicts(
    contracts: list[ChangeContract], graph: dict[str, Any]
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    blocking_pairs: set[tuple[str, str]] = set()

    for resource_id, uses in sorted(_effects_by_resource(contracts).items()):
        for index, (first_task, first_effect) in enumerate(uses):
            for second_task, second_effect in uses[index + 1 :]:
                if first_task == second_task:
                    continue
                pair = _task_pair(first_task, second_task)
                interactions = {first_effect.interaction, second_effect.interaction}
                if interactions == {
                    ResourceInteraction.RETIRE,
                    ResourceInteraction.CONSUME,
                }:
                    retiring_task = (
                        first_task
                        if first_effect.interaction == ResourceInteraction.RETIRE
                        else second_task
                    )
                    consuming_task = (
                        second_task if retiring_task == first_task else first_task
                    )
                    conflicts.append(
                        Conflict(
                            id=f"conflict-retired-{retiring_task}-{consuming_task}",
                            task_ids=list(pair),
                            type="retired_resource_consumed",
                            severity=ConflictSeverity.HARD,
                            blocking=True,
                            resource_id=resource_id,
                            blocker_task_id=retiring_task,
                            blocked_task_id=consuming_task,
                            reason=(
                                f"{retiring_task} retires a resource that "
                                f"{consuming_task} still consumes; the consumer must replan."
                            ),
                        )
                    )
                    blocking_pairs.add(pair)
                elif interactions <= {
                    ResourceInteraction.MUTATE,
                    ResourceInteraction.RETIRE,
                }:
                    conflicts.append(
                        Conflict(
                            id=f"conflict-collision-{pair[0]}-{pair[1]}",
                            task_ids=list(pair),
                            type="resource_collision",
                            severity=ConflictSeverity.HARD,
                            blocking=True,
                            resource_id=resource_id,
                            reason=(
                                f"Both tasks change the same resource: {resource_id}. "
                                "No safe order is inferred automatically."
                            ),
                        )
                    )
                    blocking_pairs.add(pair)

    nodes_by_task: dict[str, set[str]] = defaultdict(set)
    for contract in contracts:
        for effect in contract.effects:
            if effect.target.node_id:
                nodes_by_task[contract.task_id].add(effect.target.node_id)

    task_ids = [contract.task_id for contract in contracts]
    edge_pairs = {
        frozenset((edge["source"], edge["target"])) for edge in graph["edges"]
    }
    for index, first_task in enumerate(task_ids):
        for second_task in task_ids[index + 1 :]:
            pair = _task_pair(first_task, second_task)
            if pair in blocking_pairs:
                continue
            first_nodes = nodes_by_task[first_task]
            second_nodes = nodes_by_task[second_task]
            shared = first_nodes & second_nodes
            if shared:
                node_id = sorted(shared)[0]
                conflicts.append(
                    Conflict(
                        id=f"warning-shared-{pair[0]}-{pair[1]}",
                        task_ids=list(pair),
                        type="shared_component",
                        severity=ConflictSeverity.MEDIUM,
                        blocking=False,
                        reason=f"Both plans touch architecture component {node_id}.",
                    )
                )
                continue
            connected = any(
                frozenset((first_node, second_node)) in edge_pairs
                for first_node in first_nodes
                for second_node in second_nodes
            )
            if connected:
                conflicts.append(
                    Conflict(
                        id=f"warning-connected-{pair[0]}-{pair[1]}",
                        task_ids=list(pair),
                        type="connected_components",
                        severity=ConflictSeverity.UNCERTAIN,
                        blocking=False,
                        reason="The plans touch connected components and should be reviewed.",
                    )
                )

    return conflicts


def build_dependencies(
    contracts: list[ChangeContract], conflicts: list[Conflict]
) -> list[Dependency]:
    dependencies: dict[tuple[str, str, str], Dependency] = {}

    for conflict in conflicts:
        if conflict.type != "retired_resource_consumed":
            continue
        assert conflict.blocker_task_id and conflict.blocked_task_id
        dependency = Dependency(
            predecessor_task_id=conflict.blocker_task_id,
            successor_task_id=conflict.blocked_task_id,
            type="replan_after",
            reason=conflict.reason,
            replan_required=True,
        )
        dependencies[(
            dependency.predecessor_task_id,
            dependency.successor_task_id,
            dependency.type,
        )] = dependency

    by_resource = _effects_by_resource(contracts)
    for resource_id, uses in by_resource.items():
        producers = [item for item in uses if item[1].interaction == ResourceInteraction.PRODUCE]
        consumers = [item for item in uses if item[1].interaction == ResourceInteraction.CONSUME]
        for producer_task, _ in producers:
            for consumer_task, _ in consumers:
                if producer_task == consumer_task:
                    continue
                dependency = Dependency(
                    predecessor_task_id=producer_task,
                    successor_task_id=consumer_task,
                    type="produces_for",
                    reason=(
                        f"{producer_task} produces {resource_id}, which "
                        f"{consumer_task} consumes."
                    ),
                )
                dependencies[(producer_task, consumer_task, dependency.type)] = dependency

    return sorted(
        dependencies.values(),
        key=lambda item: (
            item.predecessor_task_id,
            item.successor_task_id,
            item.type,
        ),
    )


def topological_batches(
    tasks: list[Task], dependencies: list[Dependency]
) -> list[ExecutionBatch]:
    task_order = {task.id: index for index, task in enumerate(tasks)}
    successors: dict[str, set[str]] = defaultdict(set)
    indegree = {task.id: 0 for task in tasks}
    incoming: dict[str, list[Dependency]] = defaultdict(list)
    for dependency in dependencies:
        if dependency.successor_task_id not in successors[dependency.predecessor_task_id]:
            successors[dependency.predecessor_task_id].add(dependency.successor_task_id)
            indegree[dependency.successor_task_id] += 1
        incoming[dependency.successor_task_id].append(dependency)

    remaining = set(indegree)
    batches: list[ExecutionBatch] = []
    batch_index = 1
    while remaining:
        ready = sorted(
            (task_id for task_id in remaining if indegree[task_id] == 0),
            key=task_order.__getitem__,
        )
        if not ready:
            raise DependencyCycleError("derived task dependencies contain a cycle")
        conditional = any(
            dependency.replan_required
            for task_id in ready
            for dependency in incoming.get(task_id, [])
        )
        batches.append(
            ExecutionBatch(
                index=batch_index,
                task_ids=ready,
                conditional=conditional,
                condition=(
                    "A compatible replanned contract is required"
                    if conditional
                    else None
                ),
            )
        )
        batch_index += 1
        for task_id in ready:
            remaining.remove(task_id)
            for successor in successors.get(task_id, set()):
                indegree[successor] -= 1
    return batches


def assign_task_states(
    tasks: list[Task], conflicts: list[Conflict], dependencies: list[Dependency]
) -> list[Task]:
    blocked_by: dict[str, set[str]] = defaultdict(set)
    requires_replan: set[str] = set()
    unresolved_collision_tasks: set[str] = set()
    for dependency in dependencies:
        blocked_by[dependency.successor_task_id].add(dependency.predecessor_task_id)
        if dependency.replan_required:
            requires_replan.add(dependency.successor_task_id)
    for conflict in conflicts:
        if conflict.blocking and not conflict.blocker_task_id:
            unresolved_collision_tasks.update(conflict.task_ids)

    return [
        task.model_copy(
            update={
                "status": (
                    TaskStatus.BLOCKED
                    if task.id in blocked_by or task.id in unresolved_collision_tasks
                    else TaskStatus.READY
                ),
                "blocked_by": sorted(blocked_by.get(task.id, set())),
                "requires_replan": task.id in requires_replan,
            }
        )
        for task in tasks
    ]


def _visible_nodes(
    graph: dict[str, Any], root: str | None, depth: int
) -> tuple[set[str], set[str], dict[str, dict[str, Any]]]:
    nodes_by_id = _nodes_by_id(graph)
    children: dict[str, list[str]] = defaultdict(list)
    for node in graph["nodes"]:
        if node["parent_id"]:
            children[node["parent_id"]].append(node["id"])

    universe: set[str] = set()
    pending = [root] if root else list(nodes_by_id)
    while pending:
        node_id = pending.pop()
        if node_id in universe:
            continue
        universe.add(node_id)
        pending.extend(children.get(node_id, []))

    seeds = [root] if root else [
        node["id"] for node in graph["nodes"] if node["parent_id"] is None
    ]
    visible: set[str] = set()
    queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds if seed)
    while queue:
        node_id, node_depth = queue.popleft()
        if node_id in visible or node_depth > depth:
            continue
        visible.add(node_id)
        if node_depth < depth:
            queue.extend((child, node_depth + 1) for child in children.get(node_id, []))
    return visible, universe, nodes_by_id


def _visible_ancestor(
    node_id: str,
    visible: set[str],
    universe: set[str],
    nodes_by_id: dict[str, dict[str, Any]],
) -> str | None:
    if node_id not in universe:
        return None
    current: str | None = node_id
    while current is not None:
        if current in visible:
            return current
        parent = nodes_by_id[current].get("parent_id")
        current = parent if isinstance(parent, str) else None
    return None


def resolve_impacts(
    contracts: list[ChangeContract],
    graph: dict[str, Any],
    root: str | None,
    depth: int,
) -> list[DiagramImpact]:
    visible, universe, nodes_by_id = _visible_nodes(graph, root, depth)
    proposed_parents = {
        effect.architecture_change.node.id: effect.architecture_change.node.parent_id
        for contract in contracts
        for effect in contract.effects
        if effect.architecture_change is not None
        and effect.architecture_change.node is not None
    }

    def projected_endpoint(node_id: str) -> str | None:
        if node_id in proposed_parents:
            parent = proposed_parents[node_id]
            return (
                node_id
                if _visible_ancestor(parent, visible, universe, nodes_by_id) is not None
                else None
            )
        return _visible_ancestor(node_id, visible, universe, nodes_by_id)

    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for edge in graph["edges"]:
        adjacency[edge["source"]].append((edge["target"], edge))
        adjacency[edge["target"]].append((edge["source"], edge))

    impacts: list[DiagramImpact] = []
    for contract in contracts:
        claims = {claim.node_id: claim for claim in contract.diagram_impact_claims}
        for effect in contract.effects:
            change = effect.architecture_change
            proposed_node = change.node if change else None
            proposed_edge = change.edge if change else None
            if proposed_edge:
                projected_source = projected_endpoint(proposed_edge.source)
                projected_target = projected_endpoint(proposed_edge.target)
                proposed_edge = (
                    proposed_edge.model_copy(
                        update={"source": projected_source, "target": projected_target}
                    )
                    if projected_source and projected_target
                    else None
                )
            canonical_node = proposed_node.id if proposed_node else effect.target.node_id
            anchor_node = proposed_node.parent_id if proposed_node else effect.target.node_id
            if canonical_node is None or anchor_node is None:
                continue

            claim = claims.get(anchor_node)
            direct_reason = claim.reason if claim else effect.intent
            evidence = [
                ImpactEvidence(
                    kind="planner_claim" if claim else "declared_target",
                    description=direct_reason,
                    path=effect.target.path,
                    symbols=[effect.target.symbol] if effect.target.symbol else [],
                )
            ]
            impacts.append(
                DiagramImpact(
                    task_id=contract.task_id,
                    effect_id=effect.effect_id,
                    interaction=effect.interaction,
                    canonical_node_id=canonical_node,
                    visible_node_id=_visible_ancestor(
                        anchor_node, visible, universe, nodes_by_id
                    ),
                    classification=ImpactClassification.DIRECT,
                    reason=direct_reason,
                    confidence=effect.confidence,
                    evidence=evidence,
                    proposed_node=proposed_node,
                    proposed_edge=proposed_edge,
                )
            )

            if proposed_node or proposed_edge:
                continue
            seen = {anchor_node}
            frontier = [(anchor_node, 0)]
            while frontier:
                current, hops = frontier.pop(0)
                if hops >= 2:
                    continue
                for neighbor, edge in adjacency.get(current, []):
                    if neighbor in seen:
                        continue
                    seen.add(neighbor)
                    next_hops = hops + 1
                    classification = (
                        ImpactClassification.DOWNSTREAM
                        if next_hops == 1
                        else ImpactClassification.UNCERTAIN
                    )
                    impacts.append(
                        DiagramImpact(
                            task_id=contract.task_id,
                            effect_id=effect.effect_id,
                            interaction=effect.interaction,
                            canonical_node_id=neighbor,
                            visible_node_id=_visible_ancestor(
                                neighbor, visible, universe, nodes_by_id
                            ),
                            classification=classification,
                            reason=(
                                f"{nodes_by_id[neighbor]['label']} is {next_hops} evidence-backed "
                                f"relationship hop{'s' if next_hops > 1 else ''} from the change."
                            ),
                            confidence=max(0.2, effect.confidence - (0.25 * next_hops)),
                            evidence=[
                                ImpactEvidence(
                                    kind="graph_edge",
                                    description=edge["label"],
                                    edge_id=edge["id"],
                                    path=(edge["evidence"][0]["path"] if edge["evidence"] else None),
                                    symbols=(edge["evidence"][0]["symbols"] if edge["evidence"] else []),
                                )
                            ],
                        )
                    )
                    frontier.append((neighbor, next_hops))

    rank = {
        ImpactClassification.DIRECT: 0,
        ImpactClassification.DOWNSTREAM: 1,
        ImpactClassification.UNCERTAIN: 2,
    }
    return sorted(
        impacts,
        key=lambda item: (
            item.task_id,
            item.effect_id,
            rank[item.classification],
            item.canonical_node_id,
        ),
    )
