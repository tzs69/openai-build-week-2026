from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentReceipt:
    user_id: str
    amount_cents: int
    status: str


def process_payment(user_id: str, amount_cents: int) -> PaymentReceipt:
    """Process a payment without touching the user-response contract."""

    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    return PaymentReceipt(
        user_id=user_id,
        amount_cents=amount_cents,
        status="accepted",
    )
