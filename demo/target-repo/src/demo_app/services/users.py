from demo_app.schemas.user import UserResponse


USERS = {
    "user-1": "Ada Lovelace",
    "user-2": "Grace Hopper",
}


def find_user(user_id: str) -> UserResponse:
    """Load a user and construct the canonical public response."""

    return UserResponse(user_id=user_id, display_name=USERS[user_id])
