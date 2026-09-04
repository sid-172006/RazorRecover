"""
Simulation helper module for RazorRecover.
Builds authentic Razorpay payment.failed payloads with valid HMAC-SHA256 signatures
and provides enriched story metadata for interactive demos.
"""
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path

# Load webhook secret
def get_webhook_secret() -> str:
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    if not secret:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("RAZORPAY_WEBHOOK_SECRET="):
                    return line.split("=", 1)[1].strip()
    return secret or "test_secret_key_razorrecover"


SIMULATION_SCENARIOS = {
    "insufficient_balance": {
        "title": "Month-End Low Balance",
        "story": "Rahul's debit card has insufficient funds near month-end. AI recognizes salary cycle and offers instant UPI fallback.",
        "customer_name": "Rahul Verma",
        "customer_email": "rahul.verma@example.com",
        "customer_phone": "+91 98765 43210",
        "default_amount": 1499.0,
        "plan_name": "Apex Cloud Pro (Monthly)",
        "error_code": "GATEWAY_ERROR",
        "error_description": "Your payment could not be completed due to insufficient account balance.",
        "error_source": "business",
        "error_step": "payment_authorization",
        "error_reason": "insufficient_funds",
        "recovery_method": "UPI QuickPay",
        "action_cta": "Pay ₹1,499 via UPI QuickPay",
    },
    "expired_card": {
        "title": "Expired Credit Card",
        "story": "Priya's HDFC corporate card expired last month. AI halts aggressive retries and sends a 1-click self-serve card update form.",
        "customer_name": "Priya Sharma",
        "customer_email": "priya.s@techcorp.in",
        "customer_phone": "+91 98201 88321",
        "default_amount": 2999.0,
        "plan_name": "Team Workspace Plan",
        "error_code": "GATEWAY_ERROR",
        "error_description": "The card used for this payment has expired.",
        "error_source": "customer",
        "error_step": "payment_authorization",
        "error_reason": "card_expired",
        "recovery_method": "Card Update Link",
        "action_cta": "Update Card & Pay ₹2,999",
    },
    "authentication_required": {
        "title": "RBI 2FA Threshold Timeout",
        "story": "High-value invoice above the ₹15,000 auto-debit cap required OTP, but customer stepped away. AI sends instant 3D Secure approval link.",
        "customer_name": "Ankit Desai",
        "customer_email": "ankit@desaimedia.com",
        "customer_phone": "+91 99302 11984",
        "default_amount": 18500.0,
        "plan_name": "Enterprise Annual Tier",
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": "Payment failed due to authentication failure (RBI AFA mandate).",
        "error_source": "customer",
        "error_step": "payment_authentication",
        "error_reason": "authentication_failed",
        "recovery_method": "3D-Secure Re-approval",
        "action_cta": "Authorize Mandate (OTP)",
    },
    "payment_timed_out": {
        "title": "Midnight Gateway Downtime",
        "story": "SBI/HDFC core banking outage at midnight. AI identifies transient gateway failure and queues smart retry when banks recover.",
        "customer_name": "Vikram Malhotra",
        "customer_email": "vikram.m@startup.co",
        "customer_phone": "+91 97110 54329",
        "default_amount": 999.0,
        "plan_name": "Developer Starter Plan",
        "error_code": "GATEWAY_ERROR",
        "error_description": "Your payment could not be completed due to a temporary gateway issue.",
        "error_source": "bank",
        "error_step": "payment_authorization",
        "error_reason": "payment_timed_out",
        "recovery_method": "Smart Delayed Retry",
        "action_cta": "Retry with Alternate Bank",
    },
    "generic_bank_decline": {
        "title": "Ambiguous Decline (Gemini AI Fallback)",
        "story": "Customer's bank declined with zero error code. Deterministic rules cannot classify this, so it escalates live to Google Gemini to reason over the failure and prescribe a smart recovery.",
        "customer_name": "Sameer Kapoor",
        "customer_email": "sameer.k@fintechhub.in",
        "customer_phone": "+91 98450 77123",
        "default_amount": 4500.0,
        "plan_name": "Pro Business Suite",
        "error_code": "GATEWAY_ERROR",
        "error_description": "Payment was declined by the customer's bank.",
        "error_source": "customer",
        "error_step": "payment_authorization",
        "error_reason": None,
        "recovery_method": "Gemini Smart Retry",
        "action_cta": "Retry with UPI / Backup Card",
    },
}


def build_simulated_webhook(
    scenario_key: str,
    custom_amount: float = None,
    custom_error_description: str = None,
) -> tuple[dict, bytes, str]:
    """
    Constructs a valid Razorpay payment.failed payload and its HMAC-SHA256 signature.
    Supports custom amounts and custom error descriptions for dynamic LLM testing.
    Returns: (payload_dict, raw_body_bytes, signature_hex)
    """
    scenario = SIMULATION_SCENARIOS.get(scenario_key)
    if not scenario:
        scenario = SIMULATION_SCENARIOS["insufficient_balance"]

    amount_rupees = custom_amount if custom_amount is not None else scenario["default_amount"]
    # Razorpay amounts in webhooks are typically in paise (x100).
    # The webhook parser handles / 100 correctly.
    amount_paise = int(amount_rupees * 100)

    payment_id = f"pay_sim_{uuid.uuid4().hex[:10]}"
    subscription_id = f"sub_sim_{uuid.uuid4().hex[:10]}"
    event_id = f"evt_sim_{uuid.uuid4().hex[:10]}"

    error_description = custom_error_description.strip() if custom_error_description else scenario["error_description"]

    payload = {
        "id": event_id,
        "entity": "event",
        "event": "payment.failed",
        "contains": ["payment"],
        "created_at": int(time.time()),
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": "failed",
                    "method": "card",
                    "captured": False,
                    "description": f"Interactive Demo - {scenario['title']}",
                    "email": scenario["customer_email"],
                    "contact": scenario["customer_phone"],
                    "subscription_id": subscription_id,
                    "error_code": scenario["error_code"],
                    "error_description": error_description,
                    "error_source": scenario["error_source"],
                    "error_step": scenario["error_step"],
                    "error_reason": scenario["error_reason"],
                }
            }
        },
    }

    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    secret = get_webhook_secret()
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    return payload, raw_body, signature
