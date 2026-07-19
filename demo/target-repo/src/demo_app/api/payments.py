from demo_app.services.payments import PaymentReceipt, process_payment


def create_payment(user_id: str, amount_cents: int) -> PaymentReceipt:
    """Accept and process a payment request."""

    return process_payment(user_id=user_id, amount_cents=amount_cents)
