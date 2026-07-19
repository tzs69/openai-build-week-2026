from backend.orchestration.planner import plan_change


def decompose_request(request: str) -> list[str]:
    return plan_change(request)

