from backend.contracts.models import ChangeContract


class ConflictDetector:
    def detect_conflicts(self, contracts: list[ChangeContract]) -> list[str]:
        return [contract.request for contract in contracts if contract.request]

