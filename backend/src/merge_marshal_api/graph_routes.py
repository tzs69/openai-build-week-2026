from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from .graph_service import (
    GraphNotFoundError,
    GraphService,
    InvalidGraphError,
    UnknownGraphRootError,
)


router = APIRouter(prefix="/api")


def graph_service(request: Request) -> GraphService:
    return request.app.state.graph_service


@router.get("/graph")
def get_graph(
    request: Request,
    root: Optional[str] = None,
    depth: int = Query(default=1, ge=0, le=2),
) -> dict:
    try:
        return graph_service(request).project(root=root, depth=depth)
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnknownGraphRootError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidGraphError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
