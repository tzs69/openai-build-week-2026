from __future__ import annotations

from collections.abc import Callable
from typing import Any

from demo_app.api.payments import create_payment
from demo_app.api.users import get_user


ROUTES: dict[tuple[str, str], Callable[..., Any]] = {
    ("GET", "/users/{user_id}"): get_user,
    ("POST", "/payments"): create_payment,
}


def dispatch(method: str, path_template: str, **parameters: Any) -> Any:
    """Dispatch a request to one of the deliberately tiny demo endpoints."""

    handler = ROUTES[(method, path_template)]
    return handler(**parameters)
