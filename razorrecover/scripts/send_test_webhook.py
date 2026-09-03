"""
Sends realistic, correctly-signed Razorpay-shaped `payment.failed` webhooks
to your locally running RazorRecover backend.

WHY THIS EXISTS: Razorpay's dashboard gates webhook configuration behind
KYC completion, even for Test Mode. This script is the documented fallback
from the project spec's Data Strategy section — constructed fixtures that
match Razorpay's real, published payload structure (field names, error
codes, error reasons — all taken from Razorpay's own docs), signed with
the exact same HMAC-SHA256 scheme Razorpay uses. Your backend cannot tell
the difference between this and a real webhook call — which is the point:
everything downstream (classification, policy, execution, audit trail) is
exercised identically either way.

These are explicitly SIMULATED, not LIVE_TEST_MODE — be upfront about that
in your demo, exactly as the spec requires.

USAGE:
    python scripts/send_test_webhook.py                  # sends one random scenario
    python scripts/send_test_webhook.py --all             # sends every scenario once
    python scripts/send_test_webhook.py --scenario insufficient_balance
    python scripts/send_test_webhook.py --count 10         # sends 10 random scenarios
    python scripts/send_test_webhook.py --duplicate         # resends the last event (tests idempotency)
    python scripts/send_test_webhook.py --url http://localhost:8000/webhooks/razorpay
"""
import argparse
import hashlib
import hmac
import json
import os
import random
import time
import uuid
from pathlib import Path

import requests

# --- load RAZORPAY_WEBHOOK_SECRET from .env without needing python-dotenv here ---
def load_webhook_secret() -> str:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("RAZORPAY_WEBHOOK_SECRET="):
                return line.split("=", 1)[1].strip()
    return os.getenv("RAZORPAY_WEBHOOK_SECRET", "")


WEBHOOK_SECRET = load_webhook_secret()
DEFAULT_URL = "http://localhost:8000/webhooks/razorpay"

# --- scenario library — field values match Razorpay's documented error taxonomy ---
SCENARIOS = {
    "insufficient_balance": dict(
        amount=random.choice([50000, 120000, 300000]),
        error_code="GATEWAY_ERROR",
        error_description="Your payment could not be completed due to insufficient account balance.",
        error_source="business",
        error_step="payment_authorization",
        error_reason="insufficient_funds",
    ),
    "expired_card": dict(
        amount=random.choice([200000, 850000]),
        error_code="GATEWAY_ERROR",
        error_description="The card used for this payment has expired.",
        error_source="customer",
        error_step="payment_authorization",
        error_reason="card_expired",
    ),
    "blocked_card": dict(
        amount=180000,
        error_code="GATEWAY_ERROR",
        error_description="The card used for this payment is blocked.",
        error_source="customer",
        error_step="payment_authorization",
        error_reason="card_blocked",
    ),
    "authentication_required": dict(
        amount=random.choice([1800000, 2500000, 1650000]),  # above the ₹15,000 AFA threshold
        error_code="BAD_REQUEST_ERROR",
        error_description="Payment failed due to authentication failure.",
        error_source="customer",
        error_step="payment_authentication",
        error_reason="authentication_failed",
    ),
    "mandate_cancelled": dict(
        amount=90000,
        error_code="GATEWAY_ERROR",
        error_description="The mandate for this subscription was cancelled by the customer.",
        error_source="customer",
        error_step="payment_authorization",
        error_reason="mandate_cancelled",
    ),
    "generic_bank_decline": dict(
        # Deliberately vague — matches Razorpay's own documented behavior that
        # customer banks often don't share a specific reason. This is the case
        # that should fall through to Claude / manual review, not a rule match.
        amount=random.choice([70000, 95000, 150000]),
        error_code="GATEWAY_ERROR",
        error_description="Payment was declined by the customer's bank.",
        error_source="customer",
        error_step="payment_authorization",
        error_reason=None,
    ),
    "payment_timed_out": dict(
        amount=110000,
        error_code="GATEWAY_ERROR",
        error_description="Your payment could not be completed due to a temporary issue. Try again later.",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="payment_timed_out",
    ),
}

LAST_EVENT_FILE = Path(__file__).resolve().parent / ".last_event.json"


def build_payload(scenario_name: str, fixed_amount=None) -> dict:
    scenario = SCENARIOS[scenario_name]
    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    subscription_id = f"sub_{uuid.uuid4().hex[:14]}"

    return {
        "id": f"evt_{uuid.uuid4().hex[:14]}",
        "entity": "event",
        "event": "payment.failed",
        "contains": ["payment"],
        "created_at": int(time.time()),
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": fixed_amount or scenario["amount"],
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "captured": False,
                    "description": f"Simulated failure — {scenario_name}",
                    "email": "test.customer@example.com",
                    "contact": "+919876543210",
                    "subscription_id": subscription_id,
                    "error_code": scenario["error_code"],
                    "error_description": scenario["error_description"],
                    "error_source": scenario["error_source"],
                    "error_step": scenario["error_step"],
                    "error_reason": scenario["error_reason"],
                }
            }
        },
    }


def sign(body: bytes) -> str:
    if not WEBHOOK_SECRET:
        raise RuntimeError(
            "RAZORPAY_WEBHOOK_SECRET not found in .env — set it before running this script."
        )
    return hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()


def send(payload: dict, url: str) -> None:
    body = json.dumps(payload).encode("utf-8")
    signature = sign(body)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-RazorRecover-Test-Source": "send_test_webhook.py",
    }

    response = requests.post(url, data=body, headers=headers)
    payment_id = payload["payload"]["payment"]["entity"]["id"]
    print(f"[{payload['payload']['payment']['entity'].get('error_reason') or 'ambiguous':<22}] "
          f"{payment_id}  ->  {response.status_code}  {response.json()}")

    LAST_EVENT_FILE.write_text(json.dumps(payload))


def main():
    parser = argparse.ArgumentParser(description="Send simulated Razorpay webhooks to RazorRecover.")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), help="Send a specific scenario")
    parser.add_argument("--all", action="store_true", help="Send every scenario once")
    parser.add_argument("--count", type=int, default=1, help="Number of random scenarios to send")
    parser.add_argument("--duplicate", action="store_true", help="Resend the last event (tests idempotency)")
    parser.add_argument("--url", default=DEFAULT_URL, help="Webhook endpoint URL")
    args = parser.parse_args()

    if not WEBHOOK_SECRET:
        print("ERROR: RAZORPAY_WEBHOOK_SECRET is empty or .env not found. Set it first.")
        return

    if args.duplicate:
        if not LAST_EVENT_FILE.exists():
            print("No previous event found — send one first, then use --duplicate.")
            return
        payload = json.loads(LAST_EVENT_FILE.read_text())
        print("Resending the exact same event (should be ignored as a duplicate)...")
        send(payload, args.url)
        return

    if args.all:
        for name in SCENARIOS:
            send(build_payload(name), args.url)
        return

    if args.scenario:
        for _ in range(args.count):
            send(build_payload(args.scenario), args.url)
        return

    for _ in range(args.count):
        name = random.choice(list(SCENARIOS.keys()))
        send(build_payload(name), args.url)


if __name__ == "__main__":
    main()
