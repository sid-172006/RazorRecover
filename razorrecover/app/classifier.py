"""
Phase 2 — deterministic rule classifier.

Handles the 3 "clear" MVP categories. Anything that doesn't confidently
match one of these rules is left as `None` (ambiguous) — that's the signal
to route it to Claude in Phase 3, not to force a guess here.

Each rule returns (category, recommended_action) — actions match the
Action Policy Table in the spec doc. Confidence is always 1.0 for a rule
match since these are exact, explainable matches (that's the whole point
of using rules for the clear cases — no guessing involved).
"""
from __future__ import annotations

from dataclasses import dataclass

# AFA (additional factor authentication) threshold per RBI's recurring-payment
# framework. Some categories (insurance, mutual funds, card bills) have higher
# limits — flagged as a known simplification, verify against the specific
# payment type before presenting this rule as fact in the demo.
AFA_THRESHOLD_RUPEES = 15000


@dataclass
class RuleClassification:
    category: str
    recommended_action: str
    confidence: float
    decided_by: str = "rule"
    decision_reason: str = ""


def classify_by_rules(fields: dict) -> RuleClassification | None:
    """
    fields: dict with keys amount, error_code, error_description,
    error_source, error_step, error_reason (as produced by webhook_parser).

    Returns None if no rule confidently matches — caller should treat this
    as "ambiguous, needs Claude" rather than force a category here.
    """
    error_reason = (fields.get("error_reason") or "").lower()
    error_description = (fields.get("error_description") or "").lower()
    error_step = (fields.get("error_step") or "").lower()
    amount = fields.get("amount")

    combined_text = f"{error_reason} {error_description}"

    # --- Rule 1: Insufficient balance ---
    if "insufficient" in combined_text or "low balance" in combined_text:
        return RuleClassification(
            category="insufficient_balance",
            recommended_action="wait_and_notify",
            confidence=1.0,
            decision_reason="Error text explicitly indicates insufficient funds.",
        )

    # --- Rule 2: Expired or blocked card ---
    if "expired" in combined_text and "card" in combined_text:
        return RuleClassification(
            category="expired_or_blocked_card",
            recommended_action="request_payment_method_update",
            confidence=1.0,
            decision_reason="Error text explicitly indicates an expired card.",
        )
    if "card" in combined_text and ("blocked" in combined_text or "restricted" in combined_text):
        return RuleClassification(
            category="expired_or_blocked_card",
            recommended_action="request_payment_method_update",
            confidence=1.0,
            decision_reason="Error text explicitly indicates a blocked or restricted card.",
        )

    # --- Rule 3: Authentication / AFA required ---
    # Two ways this shows up: an explicit auth-failure reason, OR a recurring
    # charge above the AFA threshold combined with an authentication-stage failure.
    auth_keywords = ["authentication_failed", "authentication failed", "otp", "3ds", "afa"]
    is_auth_error = any(kw in combined_text for kw in auth_keywords) or "authentication" in error_step

    if is_auth_error:
        return RuleClassification(
            category="authentication_required",
            recommended_action="customer_reapproval",
            confidence=1.0,
            decision_reason=(
                f"Authentication-stage failure detected"
                + (f" on a payment above the AFA threshold (₹{AFA_THRESHOLD_RUPEES:,})." if amount and amount > AFA_THRESHOLD_RUPEES else ".")
            ),
        )

    # --- Rule 4: Mandate cancelled ---
    if "mandate" in combined_text and ("cancel" in combined_text or "revoke" in combined_text):
        return RuleClassification(
            category="mandate_cancelled",
            recommended_action="request_reauthorisation",
            confidence=1.0,
            decision_reason="Error text explicitly indicates the mandate was cancelled or revoked.",
        )

    # --- No confident rule match — this is the genuinely ambiguous case ---
    # (e.g. Razorpay's own docs note that generic "declined by bank" errors
    # often carry no further detail because the bank itself doesn't share one)
    return None
