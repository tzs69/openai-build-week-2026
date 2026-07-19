import unittest

from demo_app.app import dispatch
from demo_app.schemas.user import UserResponse


class UserEndpointTests(unittest.TestCase):
    def test_returns_the_canonical_user_identity(self) -> None:
        response = dispatch("GET", "/users/{user_id}", user_id="user-1")

        self.assertEqual(
            response,
            UserResponse(user_id="user-1", display_name="Ada Lovelace"),
        )


if __name__ == "__main__":
    unittest.main()
