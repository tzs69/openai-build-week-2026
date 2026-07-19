"""FastAPI entrypoint and HTTP translation for the graph service."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response, status

from merge_marshal_api.graph_service import (
    GraphNotFoundError,
    GraphService,
    GraphUnreadableError,
    InvalidGraphError,
)
from merge_marshal_api.models import (
    ApiErrorDetail,
    ApiErrorResponse,
    GraphArtifact,
    HealthResponse,
)
from merge_marshal_api.settings import Settings


def api_error(
    status_code: int,
    code: str,
    message: str,
    errors: list[str] | None = None,
) -> HTTPException:
    """Build the consistent error envelope declared by the API contract."""
    detail = ApiErrorDetail(
        code=code,
        message=message,
        errors=errors or [],
    )
    return HTTPException(status_code=status_code, detail=detail.model_dump())


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an app, allowing explicit settings injection in tests."""
    active_settings = settings or Settings()
    graph_service = GraphService(active_settings.repository_path)
    application = FastAPI(
        title="Merge Marshal API",
        version="0.1.0",
        description="Read-only API for canonical codebase architecture graphs.",
    )

    @application.get("/api/health", response_model=HealthResponse, tags=["system"])
    def get_health() -> HealthResponse:
        return HealthResponse()

    @application.get(
        "/api/graph",
        response_model=GraphArtifact,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ApiErrorResponse},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiErrorResponse},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ApiErrorResponse},
        },
        tags=["graph"],
    )
    def get_graph(response: Response) -> GraphArtifact:
        # Keep filesystem and validation errors independent from HTTP concerns.
        try:
            graph = graph_service.load_graph()
        except GraphNotFoundError as error:
            raise api_error(404, "graph_not_found", str(error)) from error
        except InvalidGraphError as error:
            raise api_error(
                422,
                "graph_invalid",
                "The configured graph artifact is invalid",
                error.errors,
            ) from error
        except GraphUnreadableError as error:
            raise api_error(500, "graph_unreadable", str(error)) from error

        response.headers["Cache-Control"] = "no-store"
        return graph

    # Expose resolved configuration for diagnostics without using module globals.
    application.state.settings = active_settings
    return application


app = create_app()
