from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..graph_service import GraphNotFoundError, InvalidGraphError, UnknownGraphRootError
from .models import RunSnapshot
from .service import CoordinationService, RunNotFoundError


router = APIRouter(prefix="/api/runs", tags=["coordination"])


def coordination_service(request: Request) -> CoordinationService:
    return request.app.state.coordination_service


def _raise_graph_error(exc: Exception) -> None:
    if isinstance(exc, (GraphNotFoundError, UnknownGraphRootError)):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, InvalidGraphError):
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    raise exc


@router.post("", response_model=RunSnapshot, status_code=201)
def create_run(
    request: Request,
    root: Optional[str] = None,
    depth: int = Query(default=1, ge=0, le=2),
) -> RunSnapshot:
    try:
        return coordination_service(request).create_run(root=root, depth=depth)
    except (GraphNotFoundError, UnknownGraphRootError, InvalidGraphError) as exc:
        _raise_graph_error(exc)
        raise AssertionError("unreachable")


@router.get("/{run_id}", response_model=RunSnapshot)
def get_run(
    run_id: str,
    request: Request,
    root: Optional[str] = None,
    depth: int = Query(default=1, ge=0, le=2),
) -> RunSnapshot:
    try:
        return coordination_service(request).get_run(
            run_id=run_id,
            root=root,
            depth=depth,
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (GraphNotFoundError, UnknownGraphRootError, InvalidGraphError) as exc:
        _raise_graph_error(exc)
        raise AssertionError("unreachable")
