from __future__ import annotations

from .models import (
    ArchitectureAction,
    ArchitectureChange,
    ChangeContract,
    ChangeEffect,
    DiagramImpactClaim,
    EffectKind,
    EffectTarget,
    ImpactClassification,
    ProposedEdge,
    ProposedNode,
    ResourceInteraction,
    Task,
)


TASK_A = "task-a"
TASK_B = "task-b"
TASK_C = "task-c"


def demo_tasks() -> list[Task]:
    return [
        Task(
            id=TASK_A,
            title="Rename the canonical user identity",
            instructions="Rename UserResponse.user_id to UserResponse.actor_id.",
            color="#d45d3f",
        ),
        Task(
            id=TASK_B,
            title="Add user caching",
            instructions="Cache user responses using the canonical user identity.",
            color="#6854c7",
        ),
        Task(
            id=TASK_C,
            title="Add structured payment logging",
            instructions="Record a structured event when a payment is processed.",
            color="#168477",
        ),
    ]


def demo_contracts() -> list[ChangeContract]:
    old_identity = "python:symbol:src/demo_app/schemas/user.py::UserResponse.user_id"
    new_identity = "python:symbol:src/demo_app/schemas/user.py::UserResponse.actor_id"
    return [
        ChangeContract(
            task_id=TASK_A,
            version=1,
            summary="Replace the public user identity field.",
            effects=[
                ChangeEffect(
                    effect_id="task-a-retire-user-id",
                    kind=EffectKind.SYMBOL,
                    interaction=ResourceInteraction.RETIRE,
                    resource_id=old_identity,
                    target=EffectTarget(
                        node_id="user-response-schema",
                        path="src/demo_app/schemas/user.py",
                        symbol="UserResponse.user_id",
                    ),
                    details={
                        "change": "rename",
                        "replacement_symbol": "UserResponse.actor_id",
                    },
                    intent="Retire the old canonical identity name.",
                    confidence=0.99,
                ),
                ChangeEffect(
                    effect_id="task-a-produce-actor-id",
                    kind=EffectKind.SYMBOL,
                    interaction=ResourceInteraction.PRODUCE,
                    resource_id=new_identity,
                    target=EffectTarget(
                        node_id="user-response-schema",
                        path="src/demo_app/schemas/user.py",
                        symbol="UserResponse.actor_id",
                    ),
                    details={"change": "rename_target"},
                    intent="Introduce the replacement canonical identity name.",
                    confidence=0.99,
                ),
            ],
            diagram_impact_claims=[
                DiagramImpactClaim(
                    node_id="user-response-schema",
                    classification=ImpactClassification.DIRECT,
                    reason="The renamed symbol belongs to the response schema.",
                )
            ],
            tests_required=["User responses expose actor_id instead of user_id"],
        ),
        ChangeContract(
            task_id=TASK_B,
            version=1,
            summary="Add a cache keyed by the current canonical identity field.",
            effects=[
                ChangeEffect(
                    effect_id="task-b-consume-user-id",
                    kind=EffectKind.BEHAVIOR,
                    interaction=ResourceInteraction.CONSUME,
                    resource_id=old_identity,
                    target=EffectTarget(
                        node_id="user-service",
                        path="src/demo_app/services/users.py",
                        symbol="find_user",
                    ),
                    details={"usage": "cache_key"},
                    intent="Use the response identity as the cache key.",
                    confidence=0.96,
                ),
                ChangeEffect(
                    effect_id="task-b-create-cache-node",
                    kind=EffectKind.ARCHITECTURE_NODE,
                    interaction=ResourceInteraction.PRODUCE,
                    resource_id="architecture:node:user-cache",
                    target=EffectTarget(node_id="user-domain"),
                    details={"change": "create", "technology": "in-memory"},
                    intent="Add a cache component inside the user domain.",
                    confidence=0.9,
                    architecture_change=ArchitectureChange(
                        action=ArchitectureAction.CREATE,
                        node=ProposedNode(
                            id="proposed-task-b-user-cache",
                            parent_id="user-domain",
                            label="User Cache",
                            type="store",
                            description="Proposed cache for canonical user responses.",
                        ),
                    ),
                ),
                ChangeEffect(
                    effect_id="task-b-create-cache-edge",
                    kind=EffectKind.ARCHITECTURE_EDGE,
                    interaction=ResourceInteraction.PRODUCE,
                    resource_id="architecture:edge:user-service-uses-cache",
                    target=EffectTarget(node_id="user-service"),
                    details={"change": "create"},
                    intent="Connect the user service to the proposed cache.",
                    confidence=0.9,
                    architecture_change=ArchitectureChange(
                        action=ArchitectureAction.CREATE,
                        edge=ProposedEdge(
                            id="proposed-task-b-user-service-uses-cache",
                            source="user-service",
                            target="proposed-task-b-user-cache",
                            type="uses",
                            label="Reads and writes cached users",
                        ),
                    ),
                ),
            ],
            diagram_impact_claims=[
                DiagramImpactClaim(
                    node_id="user-service",
                    classification=ImpactClassification.DIRECT,
                    reason="Caching changes user retrieval behavior.",
                )
            ],
            tests_required=["Repeated user retrieval uses the cache"],
        ),
        ChangeContract(
            task_id=TASK_C,
            version=1,
            summary="Emit a structured event after payment processing.",
            effects=[
                ChangeEffect(
                    effect_id="task-c-log-payment",
                    kind=EffectKind.BEHAVIOR,
                    interaction=ResourceInteraction.MUTATE,
                    resource_id="python:symbol:src/demo_app/services/payments.py::process_payment",
                    target=EffectTarget(
                        node_id="payment-service",
                        path="src/demo_app/services/payments.py",
                        symbol="process_payment",
                    ),
                    details={
                        "change": "emit_structured_log",
                        "fields": ["payment_id", "amount", "status"],
                    },
                    intent="Make successful payment processing observable.",
                    confidence=0.98,
                )
            ],
            diagram_impact_claims=[
                DiagramImpactClaim(
                    node_id="payment-service",
                    classification=ImpactClassification.DIRECT,
                    reason="The payment service emits the new event.",
                )
            ],
            tests_required=["A successful payment emits a structured event"],
        ),
    ]
