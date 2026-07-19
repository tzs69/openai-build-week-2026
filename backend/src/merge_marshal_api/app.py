from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from .coordination import CoordinationService
from .coordination.routes import router as coordination_router
from .graph_routes import router as graph_router
from .graph_service import GraphService
from .settings import target_repository


def create_app(repository: Optional[Path] = None) -> FastAPI:
    app = FastAPI(title="Merge Marshal API", version="0.1.0")
    app.state.graph_service = GraphService(repository or target_repository())
    app.state.coordination_service = CoordinationService(app.state.graph_service)
    app.include_router(graph_router)
    app.include_router(coordination_router)
    return app


app = create_app()
