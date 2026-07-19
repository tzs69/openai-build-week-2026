import unittest

from demo_app.app import dispatch
from demo_app.services.payments import PaymentReceipt


class PaymentEndpointTests(unittest.TestCase):
    def test_accepts_a_positive_payment(self) -> None:
        response = dispatch(
            "POST",
            "/payments",
            user_id="user-1",
            amount_cents=1250,
        )

        self.assertEqual(
            response,
            PaymentReceipt(
                user_id="user-1",
                amount_cents=1250,
                status="accepted",
            ),
        )

    def test_rejects_a_non_positive_payment(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be positive"):
            dispatch(
                "POST",
                "/payments",
                user_id="user-1",
                amount_cents=0,
            )


if __name__ == "__main__":
    unittest.main()
