"""
Razorpay webhook signature verification.

Razorpay signs every webhook body with HMAC-SHA256 using the webhook secret
you set in the Dashboard, and sends it in the `X-Razorpay-Signature` header.
We must verify this BEFORE trusting or storing anything in the payload —
otherwise anyone could POST fake "payment failed" events to our endpoint.
"""
import hmac
import hashlib


class InvalidWebhookSignature(Exception):
    pass


def verify_signature(raw_body: bytes, received_signature: str, webhook_secret: str) -> bool:
    """
    raw_body must be the EXACT, unparsed request body bytes — signing breaks
    if you verify against a re-serialized JSON object instead of the raw bytes.
    """
    if not received_signature or not webhook_secret:
        return False

    expected_signature = hmac.new(
        key=webhook_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # constant-time comparison — avoids timing-attack leakage
    return hmac.compare_digest(expected_signature, received_signature)
