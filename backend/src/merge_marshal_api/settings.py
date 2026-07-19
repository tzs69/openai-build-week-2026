from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TARGET_REPOSITORY = PROJECT_ROOT / "demo" / "target-repo"
TARGET_REPOSITORY_ENV = "MERGE_MARSHAL_TARGET_REPO"


def target_repository() -> Path:
    """Resolve the repository whose canonical graph should be served."""

    configured = os.environ.get(TARGET_REPOSITORY_ENV)
    return Path(configured).expanduser().resolve() if configured else DEFAULT_TARGET_REPOSITORY
