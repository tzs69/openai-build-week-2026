from dataclasses import dataclass


@dataclass(frozen=True)
class UserResponse:
    """Public user data returned by the user endpoint."""

    user_id: str
    display_name: str
