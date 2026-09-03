"""
Defensively pulls the fields we care about out of a Razorpay
`payment.failed` (or subscription.*) webhook payload.

We parse leniently (lots of .get() with defaults) rather than a strict
schema, because Razorpay's payload has many optional/nested fields and
we'd rather store what we can than 500 on an unexpected shape.
"""
from __future__ import annotations

from typing import Any


def extract_failure_fields(payload: dict) -> dict[str, Any]:
    event_payload = payload.get("payload", {})
    payment_entity = event_payload.get("payment", {}).get("entity", {})
    subscription_entity = event_payload.get("subscription", {}).get("entity", {})

    razorpay_payment_id = payment_entity.get("id")
    subscription_id = subscription_entity.get("id") or payment_entity.get("subscription_id")

    # Razorpay amounts are in paise (smallest unit) — convert to rupees for readability
    raw_amount = payment_entity.get("amount")
    amount = (raw_amount / 100) if isinstance(raw_amount, (int, float)) else None

    return {
        "razorpay_payment_id": razorpay_payment_id,
        "subscription_id": subscription_id,
        "amount": amount,
        "error_code": payment_entity.get("error_code"),
        "error_description": payment_entity.get("error_description"),
        "error_source": payment_entity.get("error_source"),
        "error_step": payment_entity.get("error_step"),
        "error_reason": payment_entity.get("error_reason"),
        # mask contact info — keep only last 4 chars for reference, never store raw
        "customer_ref_masked": _mask(payment_entity.get("contact") or payment_entity.get("email")),
    }


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    return f"***{value[-4:]}" if len(value) > 4 else "****"
