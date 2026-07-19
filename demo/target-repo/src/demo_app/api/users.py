from demo_app.schemas.user import UserResponse
from demo_app.services.users import find_user


def get_user(user_id: str) -> UserResponse:
    """Return the public representation of one user."""

    return find_user(user_id)
