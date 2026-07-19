from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskStatus(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    BLOCKED = "BLOCKED"


class EffectKind(str, Enum):
    ARTIFACT = "artifact_change"
    SYMBOL = "symbol_change"
    BEHAVIOR = "behavior_change"
    TEST = "test_change"
    CONFIGURATION = "configuration_change"
    ARCHITECTURE_NODE = "architecture_node_change"
    ARCHITECTURE_EDGE = "architecture_edge_change"


class ResourceInteraction(str, Enum):
    PRODUCE = "produce"
    CONSUME = "consume"
    MUTATE = "mutate"
    RETIRE = "retire"


class ArchitectureAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    MOVE = "move"
    REMOVE = "remove"


class ImpactClassification(str, Enum):
    DIRECT = "direct"
    DOWNSTREAM = "downstream"
    UNCERTAIN = "uncertain"


class ConflictSeverity(str, Enum):
    HARD = "hard"
    MEDIUM = "medium"
    UNCERTAIN = "uncertain"


class EffectTarget(StrictModel):
    node_id: Optional[str] = None
    path: Optional[str] = None
    symbol: Optional[str] = None

    @model_validator(mode="after")
    def requires_a_coordinate(self) -> "EffectTarget":
        if not any((self.node_id, self.path, self.symbol)):
            raise ValueError("an effect target needs a node, path, or symbol")
        return self


class ProposedNode(StrictModel):
    id: str
    parent_id: str
    label: str
    type: str
    description: str


class ProposedEdge(StrictModel):
    id: str
    source: str
    target: str
    type: str
    label: str


class ArchitectureChange(StrictModel):
    action: ArchitectureAction
    node: Optional[ProposedNode] = None
    edge: Optional[ProposedEdge] = None

    @model_validator(mode="after")
    def contains_one_graph_element(self) -> "ArchitectureChange":
        if (self.node is None) == (self.edge is None):
            raise ValueError("an architecture change needs exactly one node or edge")
        return self


class ChangeEffect(StrictModel):
    effect_id: str
    kind: EffectKind
    interaction: ResourceInteraction
    resource_id: str
    target: EffectTarget
    details: dict[str, Any] = Field(default_factory=dict)
    intent: str
    confidence: float = Field(ge=0, le=1)
    architecture_change: Optional[ArchitectureChange] = None

    @model_validator(mode="after")
    def architecture_kind_matches_payload(self) -> "ChangeEffect":
        architecture_kind = self.kind in {
            EffectKind.ARCHITECTURE_NODE,
            EffectKind.ARCHITECTURE_EDGE,
        }
        if architecture_kind != (self.architecture_change is not None):
            raise ValueError(
                "architecture effect kinds require an architecture_change payload"
            )
        if self.kind == EffectKind.ARCHITECTURE_NODE:
            if self.architecture_change is None or self.architecture_change.node is None:
                raise ValueError("architecture_node_change requires a node payload")
        if self.kind == EffectKind.ARCHITECTURE_EDGE:
            if self.architecture_change is None or self.architecture_change.edge is None:
                raise ValueError("architecture_edge_change requires an edge payload")
        return self


class DiagramImpactClaim(StrictModel):
    node_id: str
    classification: ImpactClassification
    reason: str


class ChangeContract(StrictModel):
    task_id: str
    version: int = Field(ge=1)
    summary: str
    effects: list[ChangeEffect] = Field(min_length=1)
    diagram_impact_claims: list[DiagramImpactClaim] = Field(default_factory=list)
    tests_required: list[str] = Field(default_factory=list)


class Task(StrictModel):
    id: str
    title: str
    instructions: str
    color: str
    status: TaskStatus = TaskStatus.PLANNED
    blocked_by: list[str] = Field(default_factory=list)
    requires_replan: bool = False


class ImpactEvidence(StrictModel):
    kind: Literal["declared_target", "graph_edge", "planner_claim"]
    description: str
    edge_id: Optional[str] = None
    path: Optional[str] = None
    symbols: list[str] = Field(default_factory=list)


class DiagramImpact(StrictModel):
    task_id: str
    effect_id: str
    interaction: ResourceInteraction
    canonical_node_id: str
    visible_node_id: Optional[str]
    classification: ImpactClassification
    reason: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[ImpactEvidence]
    proposed_node: Optional[ProposedNode] = None
    proposed_edge: Optional[ProposedEdge] = None


class Conflict(StrictModel):
    id: str
    task_ids: list[str] = Field(min_length=2, max_length=2)
    type: Literal[
        "resource_collision",
        "retired_resource_consumed",
        "shared_component",
        "connected_components",
    ]
    severity: ConflictSeverity
    blocking: bool
    resource_id: Optional[str] = None
    blocker_task_id: Optional[str] = None
    blocked_task_id: Optional[str] = None
    reason: str


class Dependency(StrictModel):
    predecessor_task_id: str
    successor_task_id: str
    type: Literal["produces_for", "replan_after"]
    reason: str
    replan_required: bool = False


class ExecutionBatch(StrictModel):
    index: int = Field(ge=1)
    task_ids: list[str]
    conditional: bool = False
    condition: Optional[str] = None


class ProjectionRef(StrictModel):
    root: Optional[str]
    depth: int


class RunSnapshot(StrictModel):
    run_id: str
    status: Literal["PLANNED"] = "PLANNED"
    projection: ProjectionRef
    tasks: list[Task]
    contracts: list[ChangeContract]
    impacts: list[DiagramImpact]
    conflicts: list[Conflict]
    dependencies: list[Dependency]
    execution_batches: list[ExecutionBatch]
