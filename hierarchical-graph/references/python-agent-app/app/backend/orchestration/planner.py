from backend.conflicts.detector import ConflictDetector
from backend.contracts.models import ChangeContract


def plan_change(request: str) -> list[str]:
    detector = ConflictDetector()
    contract = ChangeContract(request=request)
    return detector.detect_conflicts([contract])

